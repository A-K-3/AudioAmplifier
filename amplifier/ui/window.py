"""Build the Dear PyGui window: cards for Devices / Mix / Levels / Log."""

from __future__ import annotations

import sys

import dearpygui.dearpygui as dpg

from amplifier.audio.devices import NONE_LABEL, label_for_index, list_devices
from amplifier.audio.engine import AudioEngine
from amplifier.config import LOG_TEXT_MAX_CHARS
from amplifier.logbus import log_lines
from amplifier.ui.theme import (
    ACCENT,
    RED,
    TEXT,
    TEXT_MUTED,
    TEXT_SUBTLE,
    apply_global_theme,
    make_card_theme,
    make_progress_bar_theme,
)

import sounddevice as sd


def build_ui(engine: AudioEngine, viewport_size: int = 820,
             viewport_pos: tuple[int, int] | None = None) -> None:
    maps: dict[str, dict[str, int]] = {"input": {}, "output": {}}
    initial_in_map, initial_out_map = list_devices(show_all=False)
    maps["input"] = initial_in_map
    maps["output"] = initial_out_map

    in_labels = list(initial_in_map.keys())
    out_labels = list(initial_out_map.keys())
    out_combo_labels = [NONE_LABEL] + out_labels
    mon_labels = [NONE_LABEL] + out_labels

    default_in_idx, default_out_idx = sd.default.device

    default_in_label = (label_for_index(initial_in_map, default_in_idx)
                        or (in_labels[0] if in_labels else ""))
    default_mon_label = label_for_index(initial_out_map, default_out_idx) or NONE_LABEL
    default_out_label = NONE_LABEL

    engine.input_device = initial_in_map.get(default_in_label)
    engine.output_device = None
    engine.monitor_device = (None if default_mon_label == NONE_LABEL
                             else initial_out_map.get(default_mon_label))

    def set_status(text: str, ok: bool = True) -> None:
        dpg.set_value("status_text", text)
        dpg.configure_item("status_text", color=TEXT_MUTED if ok else RED)
        dpg.configure_item("status_dot", color=ACCENT if ok else RED)

    def safe(action, label: str) -> None:
        try:
            action()
            set_status("running", ok=True)
        except Exception as e:
            set_status(f"{label} error", ok=False)
            print(f"[{label}] {e}", file=sys.stderr)

    def on_input_change(_s, value, _u):
        print(f"[ui] input -> {value}", file=sys.stderr)
        safe(lambda: engine.open_input(maps["input"].get(value)), "input")

    def on_output_change(_s, value, _u):
        print(f"[ui] output -> {value}", file=sys.stderr)
        idx = None if value == NONE_LABEL else maps["output"].get(value)
        safe(lambda: engine.open_output(idx), "output")

    def on_monitor_change(_s, value, _u):
        print(f"[ui] monitor -> {value}", file=sys.stderr)
        idx = None if value == NONE_LABEL else maps["output"].get(value)
        safe(lambda: engine.open_monitor(idx), "monitor")

    def on_show_all_change(_s, value, _u):
        new_in, new_out = list_devices(show_all=bool(value))
        maps["input"] = new_in
        maps["output"] = new_out
        new_out_combo = [NONE_LABEL] + list(new_out.keys())
        new_mon_combo = [NONE_LABEL] + list(new_out.keys())
        dpg.configure_item("input_combo", items=list(new_in.keys()))
        dpg.configure_item("output_combo", items=new_out_combo)
        dpg.configure_item("monitor_combo", items=new_mon_combo)
        print(f"[ui] show_all={bool(value)}: {len(new_in)} inputs, "
              f"{len(new_out)} outputs", file=sys.stderr)

    def on_gain(_s, value, _u):
        engine.state.gain_db = float(value)

    def on_effect(_s, value, _u):
        engine.state.effect = value

    def on_mute(_s, value, _u):
        engine.state.muted = bool(value)

    def on_monitor_toggle(_s, value, _u):
        engine.state.monitor = bool(value)

    def copy_logs():
        dpg.set_clipboard_text(dpg.get_value("log_text"))

    def clear_logs():
        dpg.set_value("log_text", "")

    dpg.create_context()
    fonts = apply_global_theme()

    card_theme = make_card_theme()
    meter_theme = make_progress_bar_theme(ACCENT)

    with dpg.window(tag="main_win", no_close=True, no_title_bar=True,
                    no_resize=True, no_move=True, no_scrollbar=True):
        with dpg.group(horizontal=True):
            dpg.add_text("AMPLIFIER", color=TEXT, tag="title_text")
            dpg.add_spacer(width=18)
            dpg.add_text("●", color=ACCENT, tag="status_dot")
            dpg.add_text("starting…", color=TEXT_MUTED, tag="status_text")

        if fonts.get("title") is not None:
            dpg.bind_item_font("title_text", fonts["title"])

        dpg.add_spacer(height=4)

        widget_w = 560

        with dpg.child_window(border=True, width=-1, height=270,
                              no_scrollbar=True) as devices_card:
            dpg.add_text("DEVICES", color=TEXT_SUBTLE)
            dpg.add_separator()
            dpg.add_combo(in_labels, label="Input",
                          default_value=default_in_label,
                          callback=on_input_change, width=widget_w, tag="input_combo")
            dpg.add_combo(out_combo_labels, label="Output",
                          default_value=default_out_label,
                          callback=on_output_change, width=widget_w, tag="output_combo")
            dpg.add_combo(mon_labels, label="Monitor",
                          default_value=default_mon_label,
                          callback=on_monitor_change, width=widget_w, tag="monitor_combo")
            dpg.add_checkbox(label="Show all device variants",
                             callback=on_show_all_change)
            dpg.add_text("Output and Monitor must be different devices.",
                         color=TEXT_SUBTLE)
        dpg.bind_item_theme(devices_card, card_theme)

        with dpg.child_window(border=True, width=-1, height=200,
                              no_scrollbar=True) as mix_card:
            dpg.add_text("MIX", color=TEXT_SUBTLE)
            dpg.add_separator()
            dpg.add_slider_float(label="Gain (dB)",
                                 default_value=engine.state.gain_db,
                                 min_value=-40.0, max_value=1000.0,
                                 callback=on_gain, width=widget_w)
            with dpg.group(horizontal=True):
                dpg.add_text("Effect", color=TEXT_MUTED)
                dpg.add_spacer(width=12)
                dpg.add_radio_button(["none", "distortion", "echo", "lowpass"],
                                     default_value=engine.state.effect,
                                     callback=on_effect, horizontal=True)
            with dpg.group(horizontal=True):
                dpg.add_checkbox(label="Mute", callback=on_mute)
                dpg.add_spacer(width=28)
                dpg.add_checkbox(label="Monitor on", default_value=True,
                                 callback=on_monitor_toggle)
        dpg.bind_item_theme(mix_card, card_theme)

        with dpg.child_window(border=True, width=-1, height=140,
                              no_scrollbar=True) as levels_card:
            dpg.add_text("LEVELS", color=TEXT_SUBTLE)
            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_text("In ", color=TEXT_MUTED)
                dpg.add_progress_bar(tag="vu_in", default_value=0.0, width=widget_w)
                dpg.add_text("0 cb/s", tag="rate_in", color=TEXT_SUBTLE)
            with dpg.group(horizontal=True):
                dpg.add_text("Out", color=TEXT_MUTED)
                dpg.add_progress_bar(tag="vu_out", default_value=0.0, width=widget_w)
                dpg.add_text("0 cb/s", tag="rate_out", color=TEXT_SUBTLE)
        dpg.bind_item_theme(levels_card, card_theme)
        dpg.bind_item_theme("vu_in", meter_theme)
        dpg.bind_item_theme("vu_out", meter_theme)

        with dpg.child_window(border=True, width=-1, height=-1,
                              no_scrollbar=True) as log_card:
            with dpg.group(horizontal=True):
                dpg.add_text("LOG", color=TEXT_SUBTLE)
                dpg.add_spacer(width=14)
                dpg.add_button(label="Copy", callback=copy_logs)
                dpg.add_button(label="Clear", callback=clear_logs)
            dpg.add_separator()
            dpg.add_input_text(tag="log_text", multiline=True, readonly=True,
                               width=-1, height=-1, default_value="")
        dpg.bind_item_theme(log_card, card_theme)

    vp_kwargs = dict(title="Amplifier", width=viewport_size, height=viewport_size,
                     resizable=True, decorated=True)
    if viewport_pos is not None:
        vp_kwargs["x_pos"], vp_kwargs["y_pos"] = viewport_pos
    dpg.create_viewport(**vp_kwargs)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_win", True)
    dpg.show_viewport()


def drain_logs_to_widget() -> None:
    if not log_lines:
        return
    chunks = []
    while log_lines:
        try:
            chunks.append(log_lines.popleft())
        except IndexError:
            break
    if not chunks:
        return
    current = dpg.get_value("log_text")
    new = current + ("\n" if current else "") + "\n".join(chunks)
    if len(new) > LOG_TEXT_MAX_CHARS:
        new = new[-LOG_TEXT_MAX_CHARS:]
    dpg.set_value("log_text", new)
