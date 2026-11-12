"""Only the diagnostic SMR check becomes a recorded warning; hard gates stay closed."""
import io
import zlib
import numpy as np
import usb_emg as u

t=np.arange(u.EMG_COUNT)/u.EMG_HZ
x=np.round(1850+80*np.sin(2*np.pi*4*t)+5*np.sin(2*np.pi*83*t)).astype('<i2')
def header(payload,worn=1000,gap=1005):
    return f'EMG 1000 2000 {zlib.crc32(payload):x} {worn} {gap} 0'
payload=x.tobytes(); h=header(payload)
try: u.validate(h,payload)
except ValueError: pass
else: raise AssertionError('normal capture stopped rejecting low SMR')
w=[]; assert u.validate(h,payload,quality_warnings=w)[0]==1000 and len(w)==1
for badh,badp in [(h,payload[:-2]),(header(payload,0),payload),(header(payload,gap=3000),payload),(header(bytes(4000)),bytes(4000))]:
    try: u.validate(badh,badp,quality_warnings=[])
    except ValueError: pass
    else: raise AssertionError('diagnostic bypassed a hard gate')
class Serial:
    def __init__(self): self.data=io.BytesIO(('RECORDING 2\n'+h+'\n').encode()+payload)
    @property
    def in_waiting(self): return len(self.data.getbuffer())-self.data.tell()
    def write(self,b): pass
    def read(self,n): return self.data.read(n)
_,_,_,timing=u.read_take(Serial(),preview=lambda line:None,review_smr=True)
assert timing['quality_status']=='review_required' and timing['quality_warnings'] and timing['training_eligible'] is False
print('PASS: diagnostic stores SMR warning; normal SMR gate, CRC, contact, clipping and sampling gates preserved')
