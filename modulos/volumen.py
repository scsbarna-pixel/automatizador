"""Control del volumen general del sistema para el botón MIC.

Comportamiento:
- Primer toque MIC: baja el volumen al 15% con una rampa de 1 segundo.
- Segundo toque MIC: sube el volumen al 100% al instante.
"""

import ctypes
import threading
import time
from typing import Optional


_MIN_LEVEL = 0
_MAX_LEVEL = 0xFFFF


class VolumeController:
    """Controla el volumen maestro y alterna entre modo MIC activo/inactivo."""

    def __init__(self):
        self._lock = threading.Lock()
        self._fade_thread = None  # type: Optional[threading.Thread]
        self._cancel_fade = threading.Event()
        self._mic_mode = False

    def toggle_mic_mode(self):
        """Alterna el estado del botón MIC.

        Returns:
            bool: True si MIC queda activo (volumen al 15%), False si queda inactivo
            (volumen al 100%).
        """
        with self._lock:
            self._mic_mode = not self._mic_mode
            mic_mode = self._mic_mode

        if mic_mode:
            self._fade_to_percent(target_percent=15, duration_seconds=1.0)
        else:
            self._set_volume_percent(100)

        return mic_mode

    def _fade_to_percent(self, target_percent, duration_seconds):
        self._cancel_existing_fade()
        self._cancel_fade.clear()

        def runner():
            start = self._get_volume_percent()
            steps = max(1, int(duration_seconds * 20))  # ~20 fps
            sleep_time = duration_seconds / steps

            for i in range(1, steps + 1):
                if self._cancel_fade.is_set():
                    return

                ratio = i / float(steps)
                level = int(round(start + (target_percent - start) * ratio))
                self._set_volume_percent(level)
                time.sleep(sleep_time)

            self._set_volume_percent(target_percent)

        self._fade_thread = threading.Thread(target=runner)
        self._fade_thread.daemon = True
        self._fade_thread.start()

    def _cancel_existing_fade(self):
        self._cancel_fade.set()
        if self._fade_thread and self._fade_thread.is_alive():
            self._fade_thread.join(timeout=0.2)
        self._fade_thread = None

    @staticmethod
    def _set_volume_percent(percent):
        percent = max(0, min(100, int(percent)))
        scalar = int((_MAX_LEVEL - _MIN_LEVEL) * (percent / 100.0))
        packed = (scalar & 0xFFFF) | (scalar << 16)
        ctypes.windll.winmm.waveOutSetVolume(0, packed)

    @staticmethod
    def _get_volume_percent():
        current = ctypes.c_uint32()
        ctypes.windll.winmm.waveOutGetVolume(0, ctypes.byref(current))
        left = current.value & 0xFFFF
        right = (current.value >> 16) & 0xFFFF
        avg = (left + right) // 2
        return int(round(avg * 100.0 / _MAX_LEVEL))
