"""USB adapter for the existing raw_capture pipeline; only explicit diagnostic firmware."""
import asyncio
import contextlib
from gesture_trial import Reader


def packet(line):
    if not line.startswith(b'I ') or len(line)!=41 or not line.endswith(b'\n'):
        raise ValueError('Invalid USB IMU frame')
    raw=bytes.fromhex(line[2:-1].decode('ascii'))
    if len(raw)!=19 or raw[0]!=3:raise ValueError('USB IMU requires six-axis packet v3')
    return raw


class UsbImu:
    async def __aenter__(self):
        import serial
        from serial.tools import list_ports
        from upgrade import select_port
        device=select_port(list_ports.comports(),0x8045)
        if not device:raise OSError('Verified MAKO USB application not connected')
        self.address=device.serial_number
        self.port=serial.Serial(device.device,115200,timeout=.1,write_timeout=2,exclusive=True)
        self.reader = Reader(self.port)
        try:
            self.port.write(b'?\n')
            deadline = asyncio.get_running_loop().time()+3
            banner = ''
            while asyncio.get_running_loop().time() < deadline:
                for line in self.reader.take():
                    if line.startswith('MAKO DAILY '): banner = line
                if banner: break
                await asyncio.sleep(.02)
            if 'USB-IMU-3' not in banner:raise ValueError('Flash imu_usb diagnostic firmware first')
            self.port.write(b'x\n')
        except BaseException:
            self.reader.stop = True
            await asyncio.sleep(.03)
            self.port.close();raise
        return self

    async def __aexit__(self,*args):
        try:
            if hasattr(self,'task'):await self.stop_notify(None)
        finally:
            self.reader.stop = True
            await asyncio.sleep(.03)
            self.port.close()

    async def start_notify(self,_,callback):
        self.reader.take()  # read-and-discard; never tcflush on macOS CDC
        async def pump():
            while True:
                for line in self.reader.take():
                    if line.startswith('E '): raise ValueError(line)
                    if line.startswith('I '): callback(None,packet((line+'\n').encode('ascii')))
                await asyncio.sleep(.002)
        self.task=asyncio.create_task(pump())
        self.port.write(b'g\n')

    async def stop_notify(self,_):
        self.port.write(b'x\n')
        self.task.cancel()
        try:
            with contextlib.suppress(asyncio.CancelledError):await self.task
        finally:del self.task
