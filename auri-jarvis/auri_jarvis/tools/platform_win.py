"""Windows implementation of tools.platform.Platform (AI-2): ctypes (user32 / kernel32 /
powrprof) + pycaw for the master volume. Written from scratch from the Win32 docs; the
hectorg2211 repo was only an idea source (no licence → nothing copied).

Every method is blocking and is called from a worker thread (the registry runs sync tools
via asyncio.to_thread), so COM is initialised per call.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from ctypes import wintypes

import psutil

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SW_RESTORE, SW_MAXIMIZE = 9, 3
SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
GW_OWNER = 4
WM_CLOSE = 0x0010
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x0001, 0x0002
VK = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "stop": 0xB2}
VK_F11 = 0x7A
CF_UNICODETEXT = 13
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


_MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
)
_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, _MonitorEnumProc, wintypes.LPARAM]
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MONITORINFO)]
user32.EnumWindows.argtypes = [_EnumWindowsProc, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetClipboardData.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]


def work_areas() -> list[tuple[int, int, int, int]]:
    """Work areas (left, top, right, bottom) of all monitors, sorted left → right."""
    rects: list[tuple[int, int, int, int]] = []

    def cb(hmon, _hdc, _rect, _data):  # type: ignore[no-untyped-def]
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            w = info.rcWork
            rects.append((w.left, w.top, w.right, w.bottom))
        return True

    user32.EnumDisplayMonitors(None, None, _MonitorEnumProc(cb), 0)
    return sorted(rects, key=lambda r: (r[0], r[1]))


def top_windows(exe_name: str) -> list[int]:
    """Visible, titled, unowned top-level windows of a process (z-order, topmost first)."""
    want = exe_name.lower()
    pids = {p.pid for p in psutil.process_iter(["name"]) if (p.info.get("name") or "").lower() == want}
    found: list[int] = []
    if not pids:
        return found

    def cb(hwnd, _data):  # type: ignore[no-untyped-def]
        if not user32.IsWindowVisible(hwnd) or user32.GetWindow(hwnd, GW_OWNER):
            return True
        if user32.GetWindowTextLengthW(hwnd) == 0:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            found.append(int(hwnd))
        return True

    user32.EnumWindows(_EnumWindowsProc(cb), 0)
    return found


def _key(vk: int, extended: bool = False) -> None:
    flags = KEYEVENTF_EXTENDEDKEY if extended else 0
    user32.keybd_event(vk, 0, flags, 0)
    user32.keybd_event(vk, 0, flags | KEYEVENTF_KEYUP, 0)


def _endpoint_volume():  # type: ignore[no-untyped-def]
    from pycaw.pycaw import AudioUtilities

    speakers = AudioUtilities.GetSpeakers()
    vol = getattr(speakers, "EndpointVolume", None)
    if vol is not None:
        return vol
    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume

    iface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(iface, POINTER(IAudioEndpointVolume))


class _Com:
    def __enter__(self) -> None:
        import comtypes

        comtypes.CoInitialize()

    def __exit__(self, *exc: object) -> None:
        import comtypes

        comtypes.CoUninitialize()


class WindowsPlatform:
    def start_app(self, path: str, args: list[str]) -> None:
        if path.lower().endswith(".exe"):
            subprocess.Popen([path, *args], creationflags=DETACHED, close_fds=True)
        else:
            os.startfile(path)  # type: ignore[attr-defined]

    def open_url(self, url: str, *, browser_path: str | None, app_window: bool) -> None:
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError("only http(s) URLs")
        if browser_path and os.path.exists(browser_path):
            flag = f"--app={url}" if app_window else "--new-window"
            argv = [browser_path, flag] if app_window else [browser_path, flag, url]
            subprocess.Popen(argv, creationflags=DETACHED, close_fds=True)
        else:
            os.startfile(url)  # type: ignore[attr-defined]

    def place_window(self, exe_name: str, monitor: int, mode: str, *, wait_s: float) -> bool:
        deadline = time.monotonic() + wait_s
        hwnds = top_windows(exe_name)
        while not hwnds and time.monotonic() < deadline:
            time.sleep(0.25)
            hwnds = top_windows(exe_name)
        areas = work_areas()
        if not hwnds or not areas:
            return False
        left, top, right, bottom = areas[min(max(monitor, 1), len(areas)) - 1]
        hwnd = hwnds[0]
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetWindowPos(hwnd, None, left, top, right - left, bottom - top, SWP_NOZORDER | SWP_NOACTIVATE)
        if mode in ("maximized", "fullscreen"):
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
        if mode == "fullscreen":
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.15)
            _key(VK_F11)
        return True

    def close_app(self, exe_name: str) -> int:
        hwnds = top_windows(exe_name)
        for h in hwnds:
            user32.PostMessageW(h, WM_CLOSE, 0, 0)  # graceful: the app may ask to save
        return len(hwnds)

    def is_running(self, exe_name: str) -> bool:
        want = exe_name.lower()
        return any((p.info.get("name") or "").lower() == want for p in psutil.process_iter(["name"]))

    def media_key(self, action: str) -> None:
        _key(VK[action], extended=True)

    def get_volume(self) -> tuple[int, bool]:
        with _Com():
            v = _endpoint_volume()
            return round(v.GetMasterVolumeLevelScalar() * 100), bool(v.GetMute())

    def set_volume(self, level: int | None = None, mute: bool | None = None) -> tuple[int, bool]:
        with _Com():
            v = _endpoint_volume()
            if level is not None:
                v.SetMasterVolumeLevelScalar(max(0, min(100, level)) / 100.0, None)
            if mute is not None:
                v.SetMute(1 if mute else 0, None)
            return round(v.GetMasterVolumeLevelScalar() * 100), bool(v.GetMute())

    def lock(self) -> None:
        user32.LockWorkStation()

    def sleep(self) -> None:
        ctypes.WinDLL("powrprof").SetSuspendState(0, 1, 0)

    def clipboard_text(self) -> str | None:
        if not user32.OpenClipboard(None):
            return None
        try:
            h = user32.GetClipboardData(CF_UNICODETEXT)
            if not h:
                return None
            p = kernel32.GlobalLock(h)
            if not p:
                return None
            try:
                return ctypes.wstring_at(p)
            finally:
                kernel32.GlobalUnlock(h)
        finally:
            user32.CloseClipboard()

    def monitor_count(self) -> int:
        return len(work_areas())

    def screenshot_png(self, monitor: int, max_width: int) -> bytes | None:
        """One monitor (1 = left … like the tools) as PNG bytes in memory, downscaled for the
        vision model. Nothing is written to disk."""
        import io

        import mss
        from PIL import Image

        with mss.mss() as sct:
            mons = sorted(sct.monitors[1:], key=lambda m: (m["left"], m["top"]))  # [0] = all screens
            if not mons:
                return None
            shot = sct.grab(mons[min(max(monitor, 1), len(mons)) - 1])
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        if img.width > max_width:
            img = img.resize((max_width, round(img.height * max_width / img.width)))
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
