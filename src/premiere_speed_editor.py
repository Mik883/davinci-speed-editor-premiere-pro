"""Use a DaVinci Resolve Speed Editor as a Premiere Pro controller on Windows."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

from speed_editor_hid import JogLed, JogMode, Key, Led, SpeedEditor


ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "premiere_mapping.json"
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120
PIPE_NAME = r"\\.\pipe\SpeedEditorPremiere"
PIPE_ACCESS_OUTBOUND = 0x00000002
PIPE_TYPE_MESSAGE = 0x00000004
PIPE_READMODE_MESSAGE = 0x00000002
PIPE_WAIT = 0x00000000
PIPE_UNLIMITED_INSTANCES = 255
ERROR_PIPE_CONNECTED = 535
ERROR_ALREADY_EXISTS = 183


ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


VK = {
    "backspace": 0x08, "tab": 0x09, "enter": 0x0D, "shift": 0x10,
    "ctrl": 0x11, "alt": 0x12, "esc": 0x1B, "space": 0x20,
    "page_up": 0x21, "page_down": 0x22, "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "delete": 0x2E, "win": 0x5B, "f1": 0x70, "f2": 0x71,
    "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79,
    "f11": 0x7A, "f12": 0x7B, "grave": 0xC0,
    "comma": 0xBC, "period": 0xBE, "minus": 0xBD, "equals": 0xBB,
}

user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
)
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.WriteFile.argtypes = (
    wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
)
kernel32.WriteFile.restype = wintypes.BOOL
kernel32.DisconnectNamedPipe.argtypes = (wintypes.HANDLE,)
kernel32.DisconnectNamedPipe.restype = wintypes.BOOL


class NativePipeServer:
    """One-way event channel from the HID companion to the Adobe plugin."""

    def __init__(self) -> None:
        self.handle: int | None = None
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _serve(self) -> None:
        create_pipe = kernel32.CreateNamedPipeW
        create_pipe.argtypes = (
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
            wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        )
        create_pipe.restype = wintypes.HANDLE
        connect_pipe = kernel32.ConnectNamedPipe
        connect_pipe.argtypes = (wintypes.HANDLE, wintypes.LPVOID)
        connect_pipe.restype = wintypes.BOOL
        while True:
            handle = create_pipe(
                PIPE_NAME,
                PIPE_ACCESS_OUTBOUND,
                PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                1,
                4096,
                4096,
                0,
                None,
            )
            if handle == wintypes.HANDLE(-1).value:
                print(f"[PIPE] CreateNamedPipe fallita: {ctypes.get_last_error()}")
                time.sleep(2)
                continue
            connected = bool(connect_pipe(handle, None))
            if not connected and ctypes.get_last_error() != ERROR_PIPE_CONNECTED:
                kernel32.CloseHandle(handle)
                time.sleep(1)
                continue
            with self.lock:
                self.handle = handle
            print("[PIPE] Plug-in Control Surface collegato")
            while True:
                with self.lock:
                    if self.handle != handle:
                        break
                time.sleep(0.25)

    def send(self, line: str) -> None:
        payload = (line.rstrip("\n") + "\n").encode("ascii", errors="replace")
        with self.lock:
            handle = self.handle
            if handle is None:
                return
            written = wintypes.DWORD()
            ok = kernel32.WriteFile(handle, payload, len(payload), ctypes.byref(written), None)
            if not ok:
                kernel32.DisconnectNamedPipe(handle)
                kernel32.CloseHandle(handle)
                self.handle = None
                print("[PIPE] Plug-in disconnesso; attendo la riconnessione")


def _virtual_key(name: str) -> int:
    name = name.lower().strip()
    if name in VK:
        return VK[name]
    if len(name) == 1:
        code = user32.VkKeyScanW(ord(name))
        if code == -1:
            raise ValueError(f"Tasto non supportato: {name}")
        return code & 0xFF
    raise ValueError(f"Nome tasto non supportato: {name}")


def _key_event(vk: int, up: bool = False) -> None:
    item = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUTUNION(ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP if up else 0, 0, 0)),
    )
    if user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT)) != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def send_hotkey(spec: str) -> None:
    keys = [_virtual_key(part) for part in spec.split("+") if part.strip()]
    for key in keys:
        _key_event(key)
    for key in reversed(keys):
        _key_event(key, up=True)


def send_action(action: str | list[str] | None) -> None:
    if not action:
        return
    sequence = action if isinstance(action, list) else [action]
    for hotkey in sequence:
        send_hotkey(hotkey)
        if len(sequence) > 1:
            time.sleep(0.035)


def foreground_executable() -> str:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return os.path.basename(buffer.value).lower()
        return ""
    finally:
        kernel32.CloseHandle(handle)


def premiere_is_active() -> bool:
    return foreground_executable() == "adobe premiere pro.exe"


class PremiereBridge:
    def __init__(self, config: dict, test_mode: bool = False, pipe: NativePipeServer | None = None) -> None:
        self.config = config
        self.test_mode = test_mode
        self.editor: SpeedEditor | None = None
        self.held: set[Key] = set()
        self.dial_mode = "jog"
        self.last_shuttle_level: int | None = None
        self.pipe = pipe
        self.config_mtime = 0.0
        self.jog_last_value: int | None = None
        self.press_lock = threading.Lock()
        self.pending_single: dict[Key, threading.Timer] = {}

    def refresh_config(self) -> None:
        """Reload panel changes without interrupting the HID connection."""
        try:
            mtime = CONFIG_PATH.stat().st_mtime
            if mtime != self.config_mtime:
                self.config = load_config()
                self.config_mtime = mtime
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[CONFIG] Mantengo l'ultima configurazione valida: {exc}")

    def allowed(self) -> bool:
        if self.pipe:
            return True
        return self.test_mode or not self.config.get("premiere_only", True) or premiere_is_active()

    def emit(
        self,
        action: str | list[str] | None,
        label: str,
        native_target: str | None = None,
        mapping_key: str | None = None,
        mode_group: str = "mapping_modes",
    ) -> None:
        key_name = mapping_key or label
        mode = self.config.get(mode_group, {}).get(key_name, "native" if self.pipe else "shortcut")
        if mode == "off":
            return
        if self.pipe and mode == "native":
            targets = self.config.get("native_button_targets", {})
            target = native_target if native_target is not None else targets.get(key_name, key_name)
            if target:
                self.pipe.send(f"K {target}")
            return
        if not action:
            print(f"[MAPPA] {label}: nessuna azione configurata")
            return
        # Custom shortcuts are injected by Windows, so never send them to an
        # unrelated foreground application while the native pipe is active.
        if self.pipe and not self.test_mode and not premiere_is_active():
            return
        if not self.allowed():
            return
        print(f"[PREMIERE] {label} -> {action}")
        send_action(action)

    def _emit_pending_single(self, key: Key, timer: threading.Timer) -> None:
        with self.press_lock:
            if self.pending_single.get(key) is not timer:
                return
            self.pending_single.pop(key, None)
        self.refresh_config()
        self.emit(self.config.get("buttons", {}).get(key.name), key.name)

    def _handle_standard_key_press(self, key: Key) -> None:
        double_target = self.config.get("double_press_targets", {}).get(key.name)
        double_shortcut = self.config.get("double_press_buttons", {}).get(key.name)
        double_mode = self.config.get("double_press_modes", {}).get(key.name)
        if double_mode == "off":
            double_target = None
            double_shortcut = None
            double_mode = None
        if not double_target and not double_shortcut and not double_mode:
            self.emit(self.config.get("buttons", {}).get(key.name), key.name, mapping_key=key.name)
            return

        is_double = False
        with self.press_lock:
            previous = self.pending_single.pop(key, None)
            if previous is not None and previous.is_alive():
                previous.cancel()
                is_double = True
            else:
                delay = max(0.18, min(0.7, float(self.config.get("double_press_window_ms", 350)) / 1000.0))
                timer: threading.Timer
                timer = threading.Timer(delay, lambda: self._emit_pending_single(key, timer))
                timer.daemon = True
                self.pending_single[key] = timer
                timer.start()

        if is_double:
            fallback = self.config.get("double_press_buttons", {}).get(key.name)
            self.emit(
                fallback,
                f"{key.name} doppio",
                native_target=double_target,
                mapping_key=key.name,
                mode_group="double_press_modes",
            )

    def on_keys(self, keys: list[Key]) -> None:
        self.refresh_config()
        current = set(keys)
        for key in current - self.held:
            if key == Key.JOG:
                self.dial_mode = "jog"
                self.last_shuttle_level = None
                self.jog_last_value = None
                assert self.editor
                # JOG must remain relative so the freely spinning wheel never
                # reaches the +/-4096 endpoint of the absolute HID mode.
                self.editor.set_jog_mode(JogMode.RELATIVE, JogLed.JOG)
                if self.pipe:
                    self.pipe.send("K JOG")
            elif key == Key.SHTL:
                self.dial_mode = "shuttle"
                self.last_shuttle_level = None
                assert self.editor
                self.editor.set_jog_mode(JogMode.ABSOLUTE_DEADZERO, JogLed.SHTL)
                if self.pipe:
                    self.pipe.send("K SHTL")
            elif key == Key.SCRL:
                self.dial_mode = "scroll"
                self.last_shuttle_level = None
                assert self.editor
                self.editor.set_jog_mode(JogMode.RELATIVE_2, JogLed.SCRL)
                if self.pipe:
                    self.pipe.send("K SCRL")
            else:
                self._handle_standard_key_press(key)
        self.held = current

    def on_jog(self, mode: JogMode, value: int) -> None:
        self.refresh_config()
        if not self.allowed():
            return
        transport = self.config.get("transport", {})
        if self.dial_mode == "jog":
            if mode == JogMode.ABSOLUTE:
                if self.jog_last_value is None:
                    self.jog_last_value = int(value)
                    return
                delta = int(value) - self.jog_last_value
                self.jog_last_value = int(value)
                # The documented half-turn range is -4096..4096. Correct wraparound.
                if delta > 4096:
                    delta -= 8192
                elif delta < -4096:
                    delta += 8192
            else:
                # In RELATIVE mode the Speed Editor reports velocity in units
                # of about 360 per encoder click (360, 720, 1080, ...), not a
                # Loupedeck-style click count. Normalize it before forwarding
                # it to Premiere and apply Loupedeck's observed +/-55 cap.
                delta = int(round(float(value) / 360.0))
                delta = max(-55, min(55, delta))
            if transport.get("invert_jog", False):
                delta = -delta
            if not delta:
                return
            scale = max(0.1, float(transport.get("jog_scale", 1.0)))
            # Logi/Loupedeck sends Premiere relative clicks with a transport
            # resolution of 10. Using a very large value makes Premiere round
            # ordinary Speed Editor movements down to no visible movement.
            ticks_per_revolution = max(1.0, float(transport.get("jog_ticks_per_revolution", 10.0)))
            if self.pipe:
                self.pipe.send(f"J {delta * scale:.4f} {ticks_per_revolution:.1f}")
            else:
                steps = max(1, int(round(abs(delta * scale) / 64.0)))
                hotkey = "right" if delta > 0 else "left"
                for _ in range(min(steps, 12)):
                    send_hotkey(hotkey)
            return
        if self.pipe:
            if self.dial_mode == "shuttle":
                half_range = max(256.0, float(transport.get("shuttle_half_range", 4096.0)))
                self.pipe.send(f"H {int(value)} {half_range:.1f}")
            else:
                gear = max(1.0, float(transport.get("scroll_gear", 8.0)))
                self.pipe.send(f"R {int(value)} {16384.0 / gear:.1f}")
            return
        if self.dial_mode == "shuttle":
            level = max(-6, min(6, int(value)))
            if level == self.last_shuttle_level:
                return
            self.last_shuttle_level = level
            send_hotkey("k")
            if level:
                direction = "l" if level > 0 else "j"
                for _ in range(abs(level)):
                    send_hotkey(direction)
            return
        steps = max(1, min(abs(int(value)), int(self.config.get("max_jog_steps", 12))))
        if self.dial_mode == "scroll":
            # Premiere scrolls the panel underneath the pointer horizontally with Shift+wheel.
            _key_event(VK["shift"])
            try:
                amount = -WHEEL_DELTA * steps if value > 0 else WHEEL_DELTA * steps
                user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
            finally:
                _key_event(VK["shift"], up=True)

    @staticmethod
    def on_battery(charging: bool, level: int) -> None:
        print(f"[BATTERIA] {level}%{' (in carica)' if charging else ''}")

    def run_once(self) -> None:
        self.editor = SpeedEditor()
        self.editor.on_keys = self.on_keys
        self.editor.on_jog = self.on_jog
        self.editor.on_battery = self.on_battery
        timeout = self.editor.authenticate()
        self.editor.set_leds(Led.SNAP)
        self.editor.set_jog_mode(JogMode.RELATIVE, JogLed.JOG)
        print(f"[HID] Speed Editor collegata; autenticazione valida per {timeout}s")
        try:
            self.editor.run()
        finally:
            self.editor.close()


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge Speed Editor -> Adobe Premiere Pro")
    parser.add_argument("--test", action="store_true", help="Invia i comandi anche se Premiere non e attivo")
    parser.add_argument("--list-device", action="store_true", help="Mostra le interfacce HID rilevate ed esce")
    parser.add_argument("--native-pipe", action="store_true", help="Invia gli eventi al plug-in Control Surface nativo")
    args = parser.parse_args()
    if args.list_device:
        devices = SpeedEditor.enumerate()
        print(json.dumps(devices, indent=2, default=lambda value: value.decode(errors="replace") if isinstance(value, bytes) else str(value)))
        return 0 if devices else 1
    singleton = None
    if args.native_pipe:
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        ctypes.set_last_error(0)
        singleton = kernel32.CreateMutexW(None, False, "Local\\SpeedEditorPremiereBridge")
        if not singleton or ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            return 0
    pipe = NativePipeServer() if args.native_pipe else None
    if pipe:
        pipe.start()
    bridge = PremiereBridge(load_config(), test_mode=args.test, pipe=pipe)
    print("Speed Editor Bridge per Premiere. Ctrl+C per uscire.")
    while True:
        try:
            bridge.run_once()
        except KeyboardInterrupt:
            print("\nBridge arrestato.")
            return 0
        except OSError as exc:
            print(f"[HID] Dispositivo non disponibile: {exc}. Nuovo tentativo tra 3s...")
            time.sleep(3)
        except Exception as exc:
            print(f"[ERRORE] {type(exc).__name__}: {exc}. Nuovo tentativo tra 3s...")
            time.sleep(3)


if __name__ == "__main__":
    sys.exit(main())
