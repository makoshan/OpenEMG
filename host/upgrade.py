"""Build and upgrade Mako over USB without pressing Reset (existing CDC firmware)."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parent
BOARD_SERIAL = '9B648DB7317019E2'


def select_port(ports, pid=None):
    matches = [p for p in ports if p.vid == 0x2886
               and p.serial_number == BOARD_SERIAL and p.pid in (0x8045, 0x0045)]
    if len(matches) > 1:
        raise RuntimeError('Multiple matching USB ports; refusing to choose')
    return matches[0] if matches and (pid is None or matches[0].pid == pid) else None


def wait_port(pid, timeout=20):
    from serial.tools import list_ports
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        port = select_port(list_ports.comports(), pid)
        if port:
            return port
        time.sleep(.2)
    raise RuntimeError(f'USB mode 0x{pid:04x} did not appear; upgrade is not verified')


def validate_package(path):
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read('manifest.json'))['manifest']
        if set(manifest) != {'application', 'dfu_version'}:
            raise ValueError('Only application DFU packages are allowed')
        app = manifest['application']
        names = [app['bin_file'], app['dat_file'], 'manifest.json']
        if (any(Path(n).name != n or '\\' in n for n in names)
                or len(set(names)) != 3 or sorted(archive.namelist()) != sorted(names)):
            raise ValueError('Unexpected package paths or entries')
        init = app['init_packet_data']
        if init['device_type'] != 0x52 or init['softdevice_req'] != [0x123]:
            raise ValueError('Package must target nRF52 / S140 7.3.0')
        if not 0 < len(archive.read(app['bin_file'])) <= 0xED000 - 0x27000:
            raise ValueError('Application exceeds board application region')
        if not archive.read(app['dat_file']):
            raise ValueError('Empty DFU initialization packet')


def verify_application(port_name, app):
    import serial
    from usb_client import sync, wait_line
    if app == 'daily':
        sync(port_name)
        print('Upload completed; MAKO application responded and clock was synchronized.')
    elif app == 'punch_hid':
        with serial.Serial(port_name, 115200, timeout=.2, exclusive=True) as connection:
            print(wait_line(connection, 'raw ax=', timeout=10))
        print('Upload completed; Punch IMU stream responded. BLE HID pairing remains unverified.')
    elif app in ('imu_usb', 'audio_usb', 'ei_trial'):
        signature = {'imu_usb': 'MAKO DAILY 1.usb-imu; USB-IMU-3',
                     'audio_usb': 'MAKO DAILY 1.usb-audio; USB-AUDIO-2',
                     'ei_trial': 'MAKO EI-TRIAL 1; project=1111996'}[app]
        with serial.Serial(port_name, 115200, timeout=.2, exclusive=True) as connection:
            time.sleep(2)
            connection.reset_input_buffer()
            connection.write(b'?\n')
            print(wait_line(connection, signature, timeout=5))
        print('Upload completed; diagnostic protocol responded. Sensor capture remains unverified.')
    else:
        raise ValueError(f'Unknown application: {app}')


def upgrade(package=None, app='daily'):
    import serial
    from serial.tools import list_ports
    from usb_client import wait_line
    if app != 'daily' and package is None:
        raise ValueError('Non-daily firmware requires an explicit --package')
    port = select_port(list_ports.comports())
    if not port:
        raise RuntimeError('MAKO USB is not connected; connect its USB data cable')
    if package is None:
        subprocess.run(['pio', 'run', '-d', str(ROOT), '-e', 'oled_sh1106'], check=True)
        package = ROOT / '.pio/build/oled_sh1106/firmware.zip'
    package = Path(package).resolve()
    validate_package(package)
    # Reuse the pinned uploader. Import before resetting so missing tools are harmless.
    sys.path.insert(0, str(Path.home() / '.platformio/packages/tool-adafruit-nrfutil/site-packages'))
    from nordicsemi.dfu.dfu import Dfu
    from nordicsemi.dfu.dfu_transport_serial import DfuTransportSerial
    port = select_port(list_ports.comports())
    if not port:
        raise RuntimeError('MAKO disconnected before upgrade')
    if port.pid == 0x8045:
        with serial.Serial(port.device, 115200, timeout=.2, write_timeout=2) as connection:
            # Opening USB CDC can reset the board; the banner is lost if we ask too early.
            time.sleep(2)
            connection.reset_input_buffer()
            connection.write(b'?\n')
            try:
                print(wait_line(connection, 'MAKO DAILY 1.'), flush=True)
            except RuntimeError as exc:
                # Identity is already proven by the USB serial number; a silent or wedged
                # application is exactly when flashing matters most. Do not refuse to recover.
                print(f'No banner from the running application ({exc}); recovering anyway.', flush=True)
        print('Entering serial DFU automatically (no UF2 disk expected)...', flush=True)
        with serial.Serial(port.device, 1200, timeout=.2) as connection:
            connection.dtr = True
            time.sleep(.1)
            connection.dtr = False
        port = wait_port(0x0045)
    # A mode switch may change the port name; always use the re-identified device.
    DfuTransportSerial.ACK_PACKET_TIMEOUT = 5.0
    transport = DfuTransportSerial(port.device, 115200, False, True, 0, timeout=.1)
    print(f'Uploading {package.name} to verified MAKO...', flush=True)
    try:
        Dfu(str(package), dfu_transport=transport).dfu_send_images()
    finally:
        if transport.is_open():
            transport.close()
    port = wait_port(0x8045, 30)
    verify_application(port.device, app)


def check_running():
    """mstack: verify what is on the watch before verifying anything else. Exit 0 only when
    the running banner version equals the VERSION constant in device/main.cpp."""
    import re, subprocess
    src = re.search(r'VERSION = "([^"]+)";', (ROOT / 'device/main.cpp').read_text()).group(1)
    out = subprocess.run([sys.executable, str(ROOT / 'usb_probe.py'), '?', '--seconds', '3', '--timeout', '14'],
                         capture_output=True, text=True).stdout
    m = re.search(r'MAKO DAILY ([^;]+);', out)
    running = m.group(1) if m else None
    print(f'source={src} running={running} match={running == src}')
    return 0 if running == src else 1


def upgrade_uf2(env='oled_sh1106', app='daily'):
    """Double-tap route: build, convert to UF2, copy to the bootloader volume, verify, sync.

    The 1200-baud serial route has entered a bootloader that then answered nothing three
    times (2026-09-12/13); this path never touches the CDC line coding at all.
    """
    import shutil
    from usb_client import sync
    subprocess.run(['pio', 'run', '-d', str(ROOT), '-e', env], check=True)
    hexfile = ROOT / f'.pio/build/{env}/firmware.hex'
    uf2 = ROOT / f'.pio/build/{env}/firmware.uf2'
    conv = Path.home() / '.platformio/packages/framework-arduinoadafruitnrf52-seeed/tools/uf2conv/uf2conv.py'
    subprocess.run([sys.executable, str(conv), '-f', '0xADA52840', '-c', '-o', str(uf2), str(hexfile)], check=True)
    volume = Path('/Volumes/XIAO-SENSE')
    if not volume.is_dir():
        # A live application reboots itself into the UF2 bootloader on 'u' (1.6.18+).
        from serial.tools import list_ports
        port = select_port(list_ports.comports(), 0x8045)
        if port:
            import serial
            with serial.Serial(port.device, 115200, timeout=.2, write_timeout=2) as connection:
                time.sleep(2); connection.write(b'u\n'); time.sleep(.5)
            print('Asked the application to enter the UF2 bootloader...', flush=True)
        else:
            print('Double-tap the XIAO reset button now (UF2 volume XIAO-SENSE must appear)...', flush=True)
        deadline = time.monotonic() + 120
        while not volume.is_dir():
            if time.monotonic() > deadline:
                raise RuntimeError('XIAO-SENSE did not appear; double-tap reset and retry')
            time.sleep(.5)
    # is_dir() goes true before the FAT volume accepts writes; the copy then fails with
    # EACCES/ENOENT and the whole 120 s wait is wasted. Observed twice on 2026-09-16.
    for attempt in range(20):
        try:
            shutil.copyfile(uf2, volume / uf2.name)  # FAT volume: no chmod
            break
        except OSError as exc:
            if attempt == 19 or not volume.is_dir():
                raise RuntimeError(f'Could not write the UF2 to {volume}: {exc}')
            time.sleep(.5)
    port = wait_port(0x8045, 30)
    if app == 'daily':
        sync(port.device)
        print('UF2 upload completed; MAKO application responded and clock was synchronized.')
    else:
        import serial
        from usb_client import wait_line
        signature = {'imu_usb': 'USB-IMU-3', 'audio_usb': 'USB-AUDIO-2', 'ei_trial': 'EI-TRIAL', 'punch_hid': 'PUNCH-HID'}[app]
        with serial.Serial(port.device, 115200, timeout=.2, write_timeout=2) as connection:
            time.sleep(2); connection.read(connection.in_waiting); connection.write(b'?\n')
            banner = wait_line(connection, 'MAKO DAILY ')
        if signature not in banner:
            raise RuntimeError(f'{app} did not identify itself: {banner}')
        print(f'UF2 upload completed; {app} responded: {banner}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, help='Use an existing application DFU zip instead of building')
    parser.add_argument('--app', choices=('daily', 'punch_hid', 'imu_usb', 'audio_usb', 'ei_trial'), default='daily',
                        help='Post-upload application protocol to verify')
    parser.add_argument('--uf2', action='store_true', help='Flash by copying a UF2 to the double-tap bootloader volume')
    parser.add_argument('--check', action='store_true', help='Report the version running on the watch versus the source; no writes')
    parser.add_argument('--env', default='oled_sh1106', help='PlatformIO environment for --uf2 (e.g. imu_usb for the web recorder)')
    args = parser.parse_args()
    try:
        if args.check:
            sys.exit(check_running())
        upgrade_uf2(args.env, args.app) if args.uf2 else upgrade(args.package, args.app)
    except Exception as exc:
        parser.exit(1, f'Upgrade failed: {exc}\n')
