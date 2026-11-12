"""Pair, sync the real host clock, and read MAKO Daily state. Requires bleak 3.0.2."""
import argparse
import asyncio
import datetime
import json
import struct
import time

TIME_UUID = "ae500002-38c1-4b5f-bfe0-59e2d438ef7a"
STATE_UUID = "ae500003-38c1-4b5f-bfe0-59e2d438ef7a"


def decode_state(data):
    if len(data) != 20 or data[0] != 1:
        raise ValueError("Unsupported MAKO status packet")
    _, flags, battery, motion, steps, active, utc, timer = struct.unpack("<BBBBIIII", data)
    if motion > 3 or (battery != 255 and battery > 100) or flags & ~31:
        raise ValueError("Invalid MAKO status fields")
    return {"synced": bool(flags & 1), "connected": bool(flags & 2),
            "timer_running": bool(flags & 4), "timer_finished": bool(flags & 8),
            "screen_on": bool(flags & 16),
            "battery_percent_estimate": None if battery == 255 else battery,
            "motion": ["unknown", "still", "moving", "walking"][motion],
            "steps": steps, "active_seconds": active, "utc_seconds": utc or None,
            "timer_remaining_ms": timer}


async def find_device(address=None):
    from bleak import BleakScanner
    if address:
        return address
    matches = await BleakScanner.discover(timeout=8, return_adv=True)
    devices = [device for device, adv in matches.values() if adv.local_name == "MAKO Daily"]
    if len(devices) != 1:
        raise RuntimeError(f"Found {len(devices)} MAKO Daily devices; use --address to select exactly one")
    return devices[0]


async def run(args):
    from bleak import BleakClient
    device = await find_device(args.address)
    # macOS prompts for pairing when the encrypted characteristic is accessed.
    async with BleakClient(device, timeout=30) as client:
        if not args.read_only:
            offset = datetime.datetime.now().astimezone().utcoffset()
            minutes = int(offset.total_seconds() / 60)
            await client.write_gatt_char(TIME_UUID, struct.pack("<Qh", int(time.time()), minutes), response=True)
            await asyncio.sleep(1.2)  # allow firmware loop and 1Hz status publication
        state = decode_state(await client.read_gatt_char(STATE_UUID))
        if not args.read_only and (not state["synced"] or abs(state["utc_seconds"] - time.time()) > 10):
            raise RuntimeError("Time write was not confirmed by the device status")
        print(json.dumps(state, ensure_ascii=False, indent=2))
        if args.watch:
            def notify(_, data):
                try:
                    print(json.dumps(decode_state(data), ensure_ascii=False))
                except ValueError as exc:
                    print(f"Invalid notification: {exc}")
            await client.start_notify(STATE_UUID, notify)
            await asyncio.sleep(args.watch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", help="Exact device address or macOS peripheral UUID")
    parser.add_argument("--read-only", action="store_true", help="Do not change the watch clock")
    parser.add_argument("--watch", type=int, default=0, help="Observe state notifications for this many seconds")
    parser.add_argument("--check", action="store_true", help="Offline protocol check; does not use Bluetooth")
    args = parser.parse_args()
    if not 0 <= args.watch <= 3600:
        parser.error("--watch must be between 0 and 3600")
    if args.check:
        assert decode_state(struct.pack("<BBBBIIII", 1, 3, 255, 0, 0, 0, 1788825600, 300000))["battery_percent_estimate"] is None
        for invalid in (b"", bytes(20), struct.pack("<BBBBIIII", 1, 0, 255, 9, 0, 0, 0, 0)):
            try:
                decode_state(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid packet accepted")
        print("PASS: BLE status decoder (offline)")
    else:
        try:
            asyncio.run(run(args))
        except (RuntimeError, ValueError, OSError) as exc:
            parser.exit(1, f"{exc}\n")
