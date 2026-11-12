"""Set MAKO Daily's clock over an explicitly selected USB port (pyserial 3.5)."""
import argparse
import datetime
import time


def wait_line(port, prefix, timeout=5):
    deadline = time.monotonic() + timeout
    pending=bytearray()
    while time.monotonic() < deadline:
        # Read only buffered bytes: macOS CDC can signal readiness with no byte,
        # which pyserial readline treats as a disconnect between characters.
        available=port.in_waiting
        if not available:
            time.sleep(.01)
            continue
        pending.extend(port.read(min(available,4096)))
        while b'\n' in pending:
            raw,_,remaining=pending.partition(b'\n');pending=bytearray(remaining)
            line=raw.decode('ascii',errors='replace').strip()
            if line.startswith(prefix):return line
            if line.startswith('ERR invalid'):raise RuntimeError(line)
        if len(pending)>4096:raise RuntimeError('Oversized USB response')
    raise RuntimeError(f'No {prefix!r} response; check port and MAKO firmware')


def sync(port_name):
    import serial
    with serial.Serial(port_name, 115200, timeout=0.2, write_timeout=2, exclusive=True) as port:
        # Opening USB CDC can reset some board configurations; allow startup.
        time.sleep(2)
        port.reset_input_buffer()
        port.write(b'?\n')
        wait_line(port, 'MAKO DAILY 1.')
        offset = int(datetime.datetime.now().astimezone().utcoffset().total_seconds() / 60)
        seconds = int(time.time())
        port.write(f't {seconds} {offset}\n'.encode('ascii'))
        reply = wait_line(port, 'OK TIME ')
        fields = reply.split()
        if len(fields) != 4 or int(fields[2]) != seconds or int(fields[3]) != offset:
            raise RuntimeError(f'Time acknowledgement mismatch: {reply}')
        print(f'Clock accepted: {datetime.datetime.fromtimestamp(seconds).astimezone().isoformat()}')
        return seconds, offset


def interactive(port_name):
    import serial
    with serial.Serial(port_name, 115200, timeout=0.2, write_timeout=2, exclusive=True) as port:
        port.write(b'?\n')
        wait_line(port, 'MAKO DAILY 1.2')
        print('页面 0=表盘 1=活动 2=倒计时 3=秒表 4=番茄钟')
        print('s=下一页 l=开始/暂停 r=重置；d 600=设置600秒倒计时；q=退出')
        while True:
            try:
                command = input('MAKO> ').strip()
            except (EOFError, KeyboardInterrupt):
                return
            if command == 'q':
                return
            if not valid_command(command):
                print('请输入 0–4、s、l、r，或 d 加 1–10800 秒。')
                continue
            port.reset_input_buffer()
            port.write((command + '\n').encode('ascii'))
            try:
                print(wait_line(port, 'OK '))
            except RuntimeError as exc:
                print(exc)


def valid_command(command):
    if command in ('0', '1', '2', '3', '4', 's', 'l', 'r'):
        return True
    parts = command.split(' ')
    return (len(parts) == 2 and parts[0] == 'd' and parts[1].isascii()
            and parts[1].isdigit() and len(parts[1]) <= 5 and 1 <= int(parts[1]) <= 10800)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True, help='Exact /dev/cu.usbmodem… port (Windows: COMn)')
    parser.add_argument("--interactive", action="store_true", help="校时后打开计时工具控制台")
    args = parser.parse_args()
    try:
        sync(args.port)
        if args.interactive:
            interactive(args.port)
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        parser.exit(1, f'{exc}\n')
