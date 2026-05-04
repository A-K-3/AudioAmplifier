from __future__ import annotations

import ctypes
import sys
import time

import dearpygui.dearpygui as dpg

from amplifier.audio.engine import AudioEngine
from amplifier.config import PEAK_DECAY
from amplifier.logbus import LogTee
from amplifier.ui.window import build_ui, drain_logs_to_widget


WINDOW_SIZE = 880


def _centered_viewport(size: int) -> tuple[int, int, int]:
    try:
        user32 = ctypes.windll.user32
        sw = int(user32.GetSystemMetrics(0))
        sh = int(user32.GetSystemMetrics(1))
    except Exception:
        sw, sh = 1920, 1080
    x = max(0, (sw - size) // 2)
    y = max(0, (sh - size) // 2)
    return size, x, y


def run() -> int:
    sys.stderr = LogTee(sys.stderr)

    size, x, y = _centered_viewport(WINDOW_SIZE)
    engine = AudioEngine()
    build_ui(engine, viewport_size=size, viewport_pos=(x, y))
    try:
        engine.start()
        dpg.set_value("status_text", "running")
    except Exception as e:
        dpg.set_value("status_text", f"start error: {e}")

    last_rate_t = time.monotonic()
    last_in_count = 0
    last_out_count = 0

    while dpg.is_dearpygui_running():
        s = engine.state
        s.meter_in = max(s.peak_in, s.meter_in * PEAK_DECAY)
        s.meter_out = max(s.peak_out, s.meter_out * PEAK_DECAY)
        dpg.set_value("vu_in", min(s.meter_in, 1.0))
        dpg.set_value("vu_out", min(s.meter_out, 1.0))

        now = time.monotonic()
        dt = now - last_rate_t
        if dt >= 1.0:
            in_rate = (s.in_callbacks - last_in_count) / dt
            out_rate = (s.out_callbacks - last_out_count) / dt
            dpg.set_value("rate_in", f"{in_rate:.0f} cb/s")
            dpg.set_value("rate_out", f"{out_rate:.0f} cb/s")
            last_in_count = s.in_callbacks
            last_out_count = s.out_callbacks
            last_rate_t = now

        drain_logs_to_widget()
        dpg.render_dearpygui_frame()

    engine.stop()
    dpg.destroy_context()
    return 0
