"""Minimal HID driver for the Blackmagic DaVinci Resolve Speed Editor.

The authentication routine is derived from Sylvain Munaut's Apache-2.0
implementation: https://github.com/smunaut/blackmagic-misc/blob/master/bmd.py
"""

from __future__ import annotations

import enum
import struct
import time
from collections.abc import Callable

import hid


class Key(enum.IntEnum):
    NONE = 0x00
    SMART_INSRT = 0x01
    APPND = 0x02
    RIPL_OWR = 0x03
    CLOSE_UP = 0x04
    PLACE_ON_TOP = 0x05
    SRC_OWR = 0x06
    IN = 0x07
    OUT = 0x08
    TRIM_IN = 0x09
    TRIM_OUT = 0x0A
    ROLL = 0x0B
    SLIP_SRC = 0x0C
    SLIP_DEST = 0x0D
    TRANS_DUR = 0x0E
    CUT = 0x0F
    DIS = 0x10
    SMTH_CUT = 0x11
    SOURCE = 0x1A
    TIMELINE = 0x1B
    SHTL = 0x1C
    JOG = 0x1D
    SCRL = 0x1E
    SYNC_BIN = 0x1F
    TRANS = 0x22
    VIDEO_ONLY = 0x25
    AUDIO_ONLY = 0x26
    RIPL_DEL = 0x2B
    AUDIO_LEVEL = 0x2C
    FULL_VIEW = 0x2D
    SNAP = 0x2E
    SPLIT = 0x2F
    LIVE_OWR = 0x30
    ESC = 0x31
    CAM1 = 0x33
    CAM2 = 0x34
    CAM3 = 0x35
    CAM4 = 0x36
    CAM5 = 0x37
    CAM6 = 0x38
    CAM7 = 0x39
    CAM8 = 0x3A
    CAM9 = 0x3B
    STOP_PLAY = 0x3C


class Led(enum.IntFlag):
    CLOSE_UP = 1 << 0
    CUT = 1 << 1
    DIS = 1 << 2
    SMTH_CUT = 1 << 3
    TRANS = 1 << 4
    SNAP = 1 << 5
    CAM7 = 1 << 6
    CAM8 = 1 << 7
    CAM9 = 1 << 8
    LIVE_OWR = 1 << 9
    CAM4 = 1 << 10
    CAM5 = 1 << 11
    CAM6 = 1 << 12
    VIDEO_ONLY = 1 << 13
    CAM1 = 1 << 14
    CAM2 = 1 << 15
    CAM3 = 1 << 16
    AUDIO_ONLY = 1 << 17


class JogLed(enum.IntFlag):
    JOG = 1 << 0
    SHTL = 1 << 1
    SCRL = 1 << 2


class JogMode(enum.IntEnum):
    RELATIVE = 0
    ABSOLUTE = 1
    RELATIVE_2 = 2
    ABSOLUTE_DEADZERO = 3


def _rol8(value: int) -> int:
    return ((value << 56) | (value >> 8)) & 0xFFFFFFFFFFFFFFFF


def _auth_response(challenge: int) -> int:
    even = [
        0x3AE1206F97C10BC8, 0x2A9AB32BEBF244C6,
        0x20A6F8B8DF9ADF0A, 0xAF80ECE52CFC1719,
        0xEC2EE2F7414FD151, 0xB055ADFD73344A15,
        0xA63D2E3059001187, 0x751BF623F42E0DDE,
    ]
    odd = [
        0x3E22B34F502E7FDE, 0x24656B981875AB1C,
        0xA17F3456DF7BF8C3, 0x6DF72E1941AEF698,
        0x72226F011E66AB94, 0x3831A3C606296B42,
        0xFD7FF81881332C89, 0x61A3F6474FF236C6,
    ]
    mask = 0xA79A63F585D37BF0
    n = challenge & 7
    value = challenge
    for _ in range(n):
        value = _rol8(value)
    if (value & 1) == ((0x78 >> n) & 1):
        key = even[n]
    else:
        value ^= _rol8(value)
        key = odd[n]
    return value ^ (_rol8(value) & mask) ^ key


class SpeedEditor:
    VID = 0x1EDB
    PID = 0xDA0E

    def __init__(self) -> None:
        self.device = hid.device()
        self.device.open(self.VID, self.PID)
        self.on_keys: Callable[[list[Key]], None] | None = None
        self.on_jog: Callable[[JogMode, int], None] | None = None
        self.on_battery: Callable[[bool, int], None] | None = None
        self.reauth_at = 0.0

    @staticmethod
    def enumerate() -> list[dict]:
        return hid.enumerate(SpeedEditor.VID, SpeedEditor.PID)

    def authenticate(self) -> int:
        self.device.send_feature_report(b"\x06\x00" + bytes(8))
        data = bytes(self.device.get_feature_report(6, 10))
        if data[:2] != b"\x06\x00":
            raise RuntimeError(f"Challenge HID inattesa: {data.hex()}")
        challenge = int.from_bytes(data[2:10], "little")
        self.device.send_feature_report(b"\x06\x01" + bytes(8))
        data = bytes(self.device.get_feature_report(6, 10))
        if data[:2] != b"\x06\x02":
            raise RuntimeError(f"Risposta HID inattesa: {data.hex()}")
        response = _auth_response(challenge)
        self.device.send_feature_report(b"\x06\x03" + response.to_bytes(8, "little"))
        data = bytes(self.device.get_feature_report(6, 10))
        if data[:2] != b"\x06\x04":
            raise RuntimeError(f"Stato autenticazione inatteso: {data.hex()}")
        timeout = int.from_bytes(data[2:4], "little")
        self.reauth_at = time.monotonic() + max(1, timeout - 10)
        return timeout

    def set_leds(self, leds: Led) -> None:
        self.device.write(struct.pack("<BI", 2, int(leds)))

    def set_jog_mode(self, mode: JogMode, led: JogLed) -> None:
        self.device.write(struct.pack("<BBIB", 3, int(mode), 0, 255))
        self.device.write(struct.pack("<BB", 4, int(led)))

    def close(self) -> None:
        self.device.close()

    def run(self) -> None:
        while True:
            if time.monotonic() >= self.reauth_at:
                self.authenticate()
            report = self.device.read(64, 100)
            if not report:
                continue
            raw = bytes(report)
            if raw[0] == 0x03 and len(raw) >= 7:
                _, mode, value, _ = struct.unpack_from("<BBiB", raw)
                if self.on_jog:
                    self.on_jog(JogMode(mode), value)
            elif raw[0] == 0x04 and len(raw) >= 13:
                values = struct.unpack_from("<6H", raw, 1)
                keys = []
                for value in values:
                    if not value:
                        continue
                    try:
                        keys.append(Key(value))
                    except ValueError:
                        print(f"[HID] Codice tasto sconosciuto: 0x{value:02x}")
                if self.on_keys:
                    self.on_keys(keys)
            elif raw[0] == 0x07 and len(raw) >= 3 and self.on_battery:
                self.on_battery(bool(raw[1]), raw[2])
