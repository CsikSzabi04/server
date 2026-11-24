"""Lower other apps' volume (music, videos) while Auri speaks; restore afterwards.

Windows Core Audio via pycaw. All COM work happens on ONE dedicated thread (COM objects
must not hop threads). Any failure disables ducking quietly — speech never depends on it.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger("auri.voice.ducking")


class Ducker:
    def __init__(self, level: float = 0.3) -> None:
        self.level = max(0.0, min(1.0, level))
        self._saved: dict[int, float] = {}  # pid → original volume
        self._ok = True
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="auri-duck", initializer=self._com_init)

    @staticmethod
    def _com_init() -> None:
        try:
            import comtypes

            comtypes.CoInitialize()
        except Exception:
            pass

    def duck(self) -> None:
        if self._ok:
            self._pool.submit(self._duck)

    def restore(self) -> None:
        if self._ok:
            self._pool.submit(self._restore)

    def _sessions(self):
        from pycaw.pycaw import AudioUtilities

        me = os.getpid()
        for s in AudioUtilities.GetAllSessions():
            if s.Process is not None and s.Process.pid != me:
                yield s

    def _duck(self) -> None:
        try:
            for s in self._sessions():
                pid = s.Process.pid
                if pid in self._saved:
                    continue
                vol = s.SimpleAudioVolume
                self._saved[pid] = vol.GetMasterVolume()
                vol.SetMasterVolume(self._saved[pid] * self.level, None)
        except Exception as e:
            self._ok = False
            log.info("ducking disabled: %s", e)

    def _restore(self) -> None:
        try:
            for s in self._sessions():
                prev = self._saved.pop(s.Process.pid, None)
                if prev is not None:
                    s.SimpleAudioVolume.SetMasterVolume(prev, None)
        except Exception as e:
            log.info("ducking restore failed: %s", e)
        finally:
            self._saved.clear()
