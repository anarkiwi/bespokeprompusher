import struct
import time

import serial

PORT_DEFAULT = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Cable_FT8YXF6L-if03-port0"
SPEED_DEFAULT = 9600
TANK_ID_DEFAULT = 0x1
R_LEN = 9
METRICS = ("level", "rssi", "temperature_c", "battery_status")


def poll(config, _creds):
    port = config.get("port", PORT_DEFAULT)
    speed = config.get("speed", SPEED_DEFAULT)
    tank_id = config.get("tank_id", TANK_ID_DEFAULT)
    request = bytes([0x2, 0x1, tank_id, 0xd])

    for _ in range(3):
        with serial.Serial(port, speed, timeout=5) as s:
            s.reset_input_buffer()
            for b in request:
                s.write(bytes([b]))
                time.sleep(0.01)
                s.flush()
            r = s.read(R_LEN)

        if len(r) == R_LEN and r[-1] == 0xd:
            vals = struct.unpack_from("<" + "b" * R_LEN, r)
            if vals[1] != tank_id:
                raise ValueError(f"unexpected tank_id {vals[1]}, expected {tank_id}")
            return list(zip(METRICS, (vals[3], vals[4], vals[5], vals[6])))
        time.sleep(1)

    raise RuntimeError("aquapoll: no valid response after 3 attempts")
