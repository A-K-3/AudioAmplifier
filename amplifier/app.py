from __future__ import annotations

import ctypes
import sys
import time

import dearpygui.dearpygui as dpg

from amplifier.audio.engine import AudioEngine
from amplifier.config import PEAK_DECAY
from amplifier.logbus import LogTee
from amplifier import settings as user_settings
from amplifier.ui.window import WINDOW_H, WINDOW_W, build_ui


def _centered_viewport(w: int, h: int) -> tuple[int, int]:
    try:
        user32 = ctypes.windll.user32
        sw = int(user32.GetSystemMetrics(0))
        sh = int(user32.GetSystemMetrics(1))
    except Exception:
        sw, sh = 1920, 1080
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    return x, y


def run() -> int:
    sys.stderr = LogTee(sys.stderr)

    saved = user_settings.load()
    x, y = _centered_viewport(WINDOW_W, WINDOW_H)
    engine = AudioEngine()
    handles = build_ui(engine, settings=saved, viewport_pos=(x, y))
    try:
        engine.start()
        handles.set_status("running", ok=True)
    except Exception as e:
        handles.set_status(f"start error: {e}", ok=False)

    last_rate_t = time.monotonic()
    last_in_count = 0
    last_out_count = 0

    while dpg.is_dearpygui_running():
        s = engine.state
        s.meter_in = max(s.peak_in, s.meter_in * PEAK_DECAY)
        s.meter_out = max(s.peak_out, s.meter_out * PEAK_DECAY)
        handles.meter.update(s.meter_in, s.meter_out)

        now = time.monotonic()
        dt = now - last_rate_t
        if dt >= 1.0:
            in_rate = (s.in_callbacks - last_in_count) / dt
            out_rate = (s.out_callbacks - last_out_count) / dt
            handles.set_footer_rates(in_rate, out_rate)
            last_in_count = s.in_callbacks
            last_out_count = s.out_callbacks
            last_rate_t = now

        handles.drain_logs()
        dpg.render_dearpygui_frame()

    try:
        user_settings.save(handles.get_persisted_settings())
    except Exception as e:
        print(f"[settings save] {e}", file=sys.__stderr__)

    engine.stop()
    dpg.destroy_context()
    return 0
