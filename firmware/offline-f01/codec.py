"""Experimental V12 transport v1. No device control or hardware safety acceptance."""
from dataclasses import dataclass
import struct
HEADER=struct.Struct('<BBBBIQ')
FRAME_BYTES=27
SYNTHETIC=1
SESSION_START=2
RECONFIGURE=4
MAX_FRAMES=8

@dataclass(frozen=True)
class Packet:
    sequence:int
    timestamp_us:int
    flags:int
    frames:tuple[bytes,...]

def signed24(raw):
    if len(raw)!=3:raise ValueError('24-bit value requires exactly 3 bytes')
    return int.from_bytes(raw,'big',signed=True)

def decode_frame(frame):
    if len(frame)!=FRAME_BYTES:raise ValueError('ADS frame must be 27 bytes')
    return int.from_bytes(frame[:3],'big'),tuple(signed24(frame[i:i+3]) for i in range(3,27,3))

def capacity(mtu):
    if not isinstance(mtu,int) or isinstance(mtu,bool) or not 23<=mtu<=517:raise ValueError('invalid ATT MTU')
    return min(MAX_FRAMES,max(0,(mtu-3-HEADER.size)//FRAME_BYTES))

def encode(packet,mtu=247):
    if not isinstance(packet.sequence,int) or not 0<=packet.sequence<=0xffffffff:raise ValueError('invalid sequence')
    if not isinstance(packet.timestamp_us,int) or not 0<=packet.timestamp_us<=0xffffffffffffffff:raise ValueError('invalid timestamp')
    if not isinstance(packet.flags,int) or packet.flags<0 or packet.flags&~7:raise ValueError('unknown flags')
    if not 1<=len(packet.frames)<=capacity(mtu):raise ValueError('frame count exceeds negotiated MTU')
    if any(len(f)!=FRAME_BYTES for f in packet.frames):raise ValueError('invalid frame length')
    if packet.flags&SESSION_START and packet.sequence!=0:raise ValueError('session must start at sequence 0')
    if packet.flags&RECONFIGURE and not packet.flags&SESSION_START:raise ValueError('configuration boundary needs session start')
    return HEADER.pack(1,1,len(packet.frames),packet.flags,packet.sequence,packet.timestamp_us)+b''.join(packet.frames)

def decode(data,mtu=247):
    if len(data)<HEADER.size or len(data)>mtu-3:raise ValueError('truncated or oversized packet')
    version,kind,count,flags,seq,ts=HEADER.unpack_from(data)
    if version!=1 or kind!=1:raise ValueError('unsupported version or type (IMU not defined)')
    if flags&~7 or not 1<=count<=capacity(mtu):raise ValueError('invalid flags or count')
    if len(data)!=HEADER.size+count*FRAME_BYTES:raise ValueError('payload length does not match count')
    if flags&SESSION_START and seq!=0:raise ValueError('session must start at sequence 0')
    if flags&RECONFIGURE and not flags&SESSION_START:raise ValueError('configuration boundary needs session start')
    return Packet(seq,ts,flags,tuple(bytes(data[i:i+FRAME_BYTES]) for i in range(HEADER.size,len(data),FRAME_BYTES)))

def decode_pack16(data,mtu=247,version=None):
    """协议 2/3（R01 pack16）：首帧 27 字节，后续帧 8 个 int16 LE 差值；3 = 每份数据发两份（C07 负载仿真）。还原成 27 字节帧。"""
    if len(data)<HEADER.size or len(data)>mtu-3:raise ValueError('truncated or oversized packet')
    expected=version;version,kind,count,flags,seq,ts=HEADER.unpack_from(data)
    if version not in (2,3) or kind!=1 or expected not in (None,version):raise ValueError('unsupported version or type')
    copies=version-1;anchor=HEADER.size+FRAME_BYTES+24*(copies-1);step=16*copies
    if flags&~7 or count<1 or len(data)!=anchor+(count-1)*step:raise ValueError('invalid flags or count')
    if flags&SESSION_START and seq!=0:raise ValueError('session must start at sequence 0')
    if flags&RECONFIGURE and not flags&SESSION_START:raise ValueError('configuration boundary needs session start')
    first=bytes(data[HEADER.size:HEADER.size+FRAME_BYTES])
    if any(data[HEADER.size+FRAME_BYTES+24*i:HEADER.size+FRAME_BYTES+24*(i+1)]!=first[3:] for i in range(copies-1)):raise ValueError('pack16 copies differ')
    frames=[first];values=list(decode_frame(first)[1])
    for i in range(count-1):
        block=data[anchor+i*step:anchor+(i+1)*step]
        if any(block[16*c:16*(c+1)]!=block[:16] for c in range(1,copies)):raise ValueError('pack16 copies differ')
        values=[v+d for v,d in zip(values,struct.unpack('<8h',block[:16]))]
        if any(not -0x800000<=v<=0x7fffff for v in values):raise ValueError('pack16 value out of 24-bit range')
        frames.append(first[:3]+b''.join(v.to_bytes(3,'big',signed=True) for v in values))
    return Packet(seq,ts,flags,tuple(frames))

class Receiver:
    """Explicit reconnect boundary. Counts missing samples; never fills them."""
    def __init__(self,allow_real=False,decoder=decode):
        self.decoder=decoder
        self.allow_real=allow_real;self.expected=None;self.last_timestamp=None;self.synthetic=None
        self.accepted_samples=0;self.missing_samples=0;self.reordered=0;self.malformed=0;self.sessions=0;self.boundaries=[]
    def disconnect(self):
        self.expected=None;self.last_timestamp=None;self.synthetic=None
    def receive(self,data,mtu=247):
        try:p=self.decoder(data,mtu)
        except ValueError:self.malformed+=1;raise
        synthetic=bool(p.flags&SYNTHETIC)
        if not synthetic and not self.allow_real:raise ValueError('real source not enabled; no hardware validated')
        boundary=bool(p.flags&RECONFIGURE)
        if boundary:
            if self.expected is None:raise ValueError('configuration boundary requires an existing session')
            if self.synthetic!=synthetic:raise ValueError('cannot change source kind at configuration boundary')
            if p.timestamp_us<=self.last_timestamp:raise ValueError('nonmonotonic configuration boundary')
            # 只记录可观测时差；ADC停采期间丢了多少样本未知，不伪造精确丢样数。
            self.boundaries.append(dict(previous_session=self.sessions, previous_timestamp_us=self.last_timestamp,
                                        next_timestamp_us=p.timestamp_us, missing_samples=None, reason='configuration'))
            self.expected=None
        if self.expected is None:
            if not p.flags&SESSION_START:raise ValueError('session-start packet required after connect')
            delta=0
        else:
            if p.flags&SESSION_START:raise ValueError('disconnect must be recorded before a new session')
            if self.synthetic!=synthetic:raise ValueError('cannot mix synthetic and real data in a session')
            delta=(p.sequence-self.expected)&0xffffffff
            if delta>=0x80000000:self.reordered+=1;raise ValueError('duplicate or reordered packet')
            if p.timestamp_us<=self.last_timestamp:raise ValueError('nonmonotonic timestamp')
        if self.expected is None:self.sessions+=1
        self.missing_samples+=delta;self.accepted_samples+=len(p.frames)
        self.expected=(p.sequence+len(p.frames))&0xffffffff
        self.last_timestamp=p.timestamp_us;self.synthetic=synthetic
        return p
