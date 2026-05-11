"""Minimalist Amplifier UI: responsive table layout, hairline meters, drag-number gain."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable

import dearpygui.dearpygui as dpg
import sounddevice as sd

from amplifier.audio.devices import NONE_LABEL, label_for_index, list_devices
from amplifier.audio.engine import AudioEngine
from amplifier.config import (
    BLOCK_SIZE,
    GAIN_DEFAULT_DB,
    GAIN_MAX_DB,
    GAIN_MIN_DB,
    LOG_TEXT_MAX_CHARS,
    SAMPLE_RATE,
)
from amplifier.logbus import log_lines
from amplifier.settings import Settings
from amplifier.ui.theme import (
    ACCENT,
    GREEN,
    RED,
    TEXT,
    TEXT_FAINT,
    TEXT_MUTED,
    TEXT_SUBTLE,
    apply_global_theme,
    make_ghost_button_theme,
)
from amplifier.ui.widgets import (
    DragNumber,
    LineMeter,
    add_status_dot,
    update_status_dot,
)

WINDOW_W = 760
WINDOW_H = 680
MIN_INNER_W = 360       # below this, widgets stop scaling

WINDOW_PADDING_X = 18   # matches mvStyleVar_WindowPadding x in theme

FX_ORDER: tuple[tuple[str, str], ...] = (
    ("none", "none"),
    ("distortion", "distortion"),
    ("echo", "echo"),
    ("lowpass", "lowpass"),
)


@dataclass
class UIHandles:
    meter: LineMeter
    gain: DragNumber
    set_status: Callable[[str, bool], None]
    set_footer_rates: Callable[[float, float], None]
    drain_logs: Callable[[], None]
    relayout: Callable[[], None]
    get_persisted_settings: Callable[[], Settings]


def _make_link_theme(color: tuple[int, int, int, int]):
    """Borderless text-link button: just colored text with subtle hover bg."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 255, 12))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 255, 18))
            dpg.add_theme_color(dpg.mvThemeCol_Text, color)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
    return t


def _make_layout_table_theme():
    """A table used purely for layout — zero borders, tight padding."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvTable):
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderLight, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderStrong, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, (0, 0, 0, 0))
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 0, 4)
    return t


@dataclass
class _Themes:
    link_muted: int = 0
    link_text: int = 0
    link_accent: int = 0
    link_red: int = 0
    link_green: int = 0
    ghost: int = 0
    layout_table: int = 0
    fonts: dict = field(default_factory=dict)


def _build_themes() -> _Themes:
    fonts = apply_global_theme()
    return _Themes(
        link_muted=_make_link_theme(TEXT_MUTED),
        link_text=_make_link_theme(TEXT),
        link_accent=_make_link_theme(ACCENT),
        link_red=_make_link_theme(RED),
        link_green=_make_link_theme(GREEN),
        ghost=make_ghost_button_theme(),
        layout_table=_make_layout_table_theme(),
        fonts=fonts,
    )


def _layout_table(tag: str, columns: list[dict]):
    """Helper to build a borderless layout table.

    Each column dict: {"stretch": True} or {"fixed": int_width}.
    """
    table = dpg.add_table(
        tag=tag, header_row=False,
        borders_innerH=False, borders_innerV=False,
        borders_outerH=False, borders_outerV=False,
        policy=dpg.mvTable_SizingStretchProp,
        no_pad_innerX=True, no_pad_outerX=True,
    )
    for col in columns:
        if "fixed" in col:
            dpg.add_table_column(parent=tag, width_fixed=True,
                                 init_width_or_weight=col["fixed"])
        else:
            dpg.add_table_column(parent=tag, width_stretch=True,
                                 init_width_or_weight=col.get("weight", 1.0))
    return table


def build_ui(engine: AudioEngine,
             settings: Settings | None = None,
             viewport_pos: tuple[int, int] | None = None) -> UIHandles:
    if settings is None:
        settings = Settings()

    show_all_state = {"value": bool(settings.show_all_variants)}
    maps: dict[str, dict[str, int]] = {"input": {}, "output": {}}
    initial_in_map, initial_out_map = list_devices(show_all=show_all_state["value"])
    maps["input"] = initial_in_map
    maps["output"] = initial_out_map

    default_in_idx, default_out_idx = sd.default.device

    def pick_initial(saved: str, available: dict[str, int],
                     fallback: str) -> str:
        if saved and saved in available:
            return saved
        return fallback

    sys_in_label = (label_for_index(initial_in_map, default_in_idx)
                    or next(iter(initial_in_map), ""))
    sys_mon_label = label_for_index(initial_out_map, default_out_idx) or NONE_LABEL

    default_in_label = pick_initial(settings.input_label, initial_in_map,
                                    sys_in_label)
    default_out_label = pick_initial(settings.output_label,
                                     {**initial_out_map, NONE_LABEL: -1},
                                     NONE_LABEL)
    default_mon_label = pick_initial(settings.monitor_label,
                                     {**initial_out_map, NONE_LABEL: -1},
                                     sys_mon_label)

    # Output and Monitor must differ — drop output to NONE if a stale save
    # has them clashing.
    if (default_out_label != NONE_LABEL
            and default_out_label == default_mon_label):
        default_out_label = NONE_LABEL

    engine.input_device = initial_in_map.get(default_in_label)
    engine.output_device = (None if default_out_label == NONE_LABEL
                            else initial_out_map.get(default_out_label))
    engine.monitor_device = (None if default_mon_label == NONE_LABEL
                             else initial_out_map.get(default_mon_label))

    dpg.create_context()
    themes = _build_themes()

    fx_buttons: dict[str, int] = {}

    # ──────────── helpers ────────────────────────────────────────────────────

    def set_status(text: str, ok: bool = True) -> None:
        update_status_dot("status_dot", ACCENT if ok else RED, glow=True, size=12)
        if dpg.does_item_exist("status_text"):
            dpg.set_value("status_text", text)
            dpg.configure_item("status_text",
                               color=TEXT_MUTED if ok else RED)

    def safe(action, label: str) -> None:
        try:
            action()
            set_status("running", ok=True)
        except Exception as e:
            set_status(f"{label} error", ok=False)
            print(f"[{label}] {e}", file=sys.stderr)

    def on_input_pick(_s, value, _u):
        idx = maps["input"].get(value)
        safe(lambda: engine.open_input(idx), "input")

    def on_output_pick(_s, value, _u):
        idx = None if value == NONE_LABEL else maps["output"].get(value)
        safe(lambda: engine.open_output(idx), "output")

    def on_monitor_pick(_s, value, _u):
        idx = None if value == NONE_LABEL else maps["output"].get(value)
        safe(lambda: engine.open_monitor(idx), "monitor")

    def on_show_all_change(_s, value, _u):
        show_all_state["value"] = bool(value)
        new_in, new_out = list_devices(show_all=show_all_state["value"])
        maps["input"] = new_in
        maps["output"] = new_out
        dpg.configure_item("input_combo", items=list(new_in.keys()))
        dpg.configure_item("output_combo", items=[NONE_LABEL] + list(new_out.keys()))
        dpg.configure_item("monitor_combo", items=[NONE_LABEL] + list(new_out.keys()))

    def get_gain() -> float:
        return engine.state.gain_db

    def set_gain(v: float) -> None:
        engine.state.gain_db = float(v)

    def fmt_gain(v: float) -> str:
        sign = "+" if v >= 0 else "−"
        return f"{sign}{abs(v):.1f} dB"

    def rebind_fx_themes() -> None:
        for val, tag in fx_buttons.items():
            dpg.bind_item_theme(
                tag,
                themes.link_accent if val == engine.state.effect else themes.link_muted,
            )

    def on_fx_click(_sender, _app_data, user_data) -> None:
        engine.state.effect = user_data
        print(f"[ui] effect -> {user_data}", file=sys.stderr)
        rebind_fx_themes()

    def sync_transport() -> None:
        muted = engine.state.muted
        monitor = engine.state.monitor
        dpg.set_item_label("btn_mute", "muted" if muted else "mute")
        dpg.bind_item_theme("btn_mute",
                            themes.link_red if muted else themes.link_muted)
        dpg.set_item_label("btn_monitor",
                           "monitor on" if monitor else "monitor off")
        dpg.bind_item_theme("btn_monitor",
                            themes.link_green if monitor else themes.link_muted)

    def on_mute_click(_s, _a, _u) -> None:
        engine.state.muted = not engine.state.muted
        sync_transport()

    def on_monitor_click(_s, _a, _u) -> None:
        engine.state.monitor = not engine.state.monitor
        sync_transport()

    def toggle_log_window(_s=None, _a=None, _u=None) -> None:
        if dpg.does_item_exist("log_window"):
            shown = dpg.is_item_shown("log_window")
            dpg.configure_item("log_window", show=not shown)

    def copy_logs():
        dpg.set_clipboard_text(dpg.get_value("log_text"))

    def clear_logs():
        dpg.set_value("log_text", "")

    def current_inner_width() -> int:
        try:
            vw = dpg.get_viewport_client_width()
        except Exception:
            vw = WINDOW_W
        return max(MIN_INNER_W, vw - 2 * WINDOW_PADDING_X)

    # ──────────── window ─────────────────────────────────────────────────────

    with dpg.window(tag="main_win", no_close=True, no_title_bar=True,
                    no_resize=False, no_move=True, no_scrollbar=True):
        # ── Header: 3 cols (title stretch | status group fixed | menu fixed)
        _layout_table("tbl_header", [{"stretch": True}, {"fixed": 140},
                                     {"fixed": 36}])
        dpg.bind_item_theme("tbl_header", themes.layout_table)
        with dpg.table_row(parent="tbl_header"):
            dpg.add_text("AMPLIFIER", tag="title_text", color=TEXT)
            with dpg.group(horizontal=True):
                add_status_dot("status_dot", size=12)
                dpg.add_spacer(width=6)
                dpg.add_text("running", tag="status_text", color=TEXT_MUTED)
            more_btn = dpg.add_button(label="•••", tag="btn_more")
            dpg.bind_item_theme(more_btn, themes.ghost)
            with dpg.popup(more_btn, mousebutton=dpg.mvMouseButton_Left,
                           modal=False, tag="popup_more"):
                dpg.add_text("SETTINGS", color=TEXT_SUBTLE)
                dpg.add_separator()
                dpg.add_checkbox(label="Show all device variants",
                                 default_value=show_all_state["value"],
                                 callback=on_show_all_change)
                dpg.add_text("Output and Monitor must be different devices.",
                             color=TEXT_FAINT, wrap=240)
                dpg.add_separator()
                dpg.add_button(label="Toggle log (F9)", callback=toggle_log_window)

        if themes.fonts.get("title"):
            dpg.bind_item_font("title_text", themes.fonts["title"])
        update_status_dot("status_dot", ACCENT, glow=True, size=12)

        dpg.add_spacer(height=22)

        # ── Device rows: one table, 2 cols (label fixed, combo stretch)
        _layout_table("tbl_devices", [{"fixed": 88}, {"stretch": True}])
        dpg.bind_item_theme("tbl_devices", themes.layout_table)

        def add_device_row(label: str, default_value: str,
                           combo_tag: str, items: list[str], on_pick) -> None:
            with dpg.table_row(parent="tbl_devices"):
                dpg.add_text(label, color=TEXT_MUTED)
                dpg.add_combo(items, default_value=default_value,
                              callback=on_pick, width=-1, tag=combo_tag)

        add_device_row("Input", default_in_label or NONE_LABEL,
                       "input_combo", list(initial_in_map.keys()),
                       on_input_pick)
        add_device_row("Output", default_out_label,
                       "output_combo",
                       [NONE_LABEL] + list(initial_out_map.keys()),
                       on_output_pick)
        add_device_row("Monitor", default_mon_label,
                       "monitor_combo",
                       [NONE_LABEL] + list(initial_out_map.keys()),
                       on_monitor_pick)

        dpg.add_spacer(height=24)

        # ── Hairline meter (resized via callback)
        meter = LineMeter(tag="line_meter", width=current_inner_width(), height=44,
                          line_thickness=3, label_top="in", label_bot="out")
        meter.build()

        dpg.add_spacer(height=20)

        # ── Big drag-number gain (resized via callback)
        gain = DragNumber(
            tag="gain_num",
            width=current_inner_width(),
            height=140,
            get_value=get_gain,
            set_value=set_gain,
            format_value=fmt_gain,
            font_big=themes.fonts.get("mono_big"),
            font_small=themes.fonts.get("small"),
            min_value=GAIN_MIN_DB,
            max_value=GAIN_MAX_DB,
            default_value=GAIN_DEFAULT_DB,
        )
        gain.build()

        dpg.add_spacer(height=14)

        # ── FX tabs: 6 cols (stretch | btn | btn | btn | btn | stretch)
        # 96px per cell fits "distortion" (longest label) at the small font.
        _layout_table("tbl_fx",
                      [{"stretch": True}] + [{"fixed": 96}] * 4 + [{"stretch": True}])
        dpg.bind_item_theme("tbl_fx", themes.layout_table)
        with dpg.table_row(parent="tbl_fx"):
            dpg.add_spacer()
            for label, value in FX_ORDER:
                tag = f"fx_btn_{value}"
                dpg.add_button(label=label, tag=tag, width=-1,
                               user_data=value, callback=on_fx_click)
                fx_buttons[value] = tag
            dpg.add_spacer()
        rebind_fx_themes()

        dpg.add_spacer(height=14)

        # ── Transport: 5 cols (stretch | mute | gap fixed | monitor | stretch)
        _layout_table("tbl_transport",
                      [{"stretch": True}, {"fixed": 90}, {"fixed": 32},
                       {"fixed": 130}, {"stretch": True}])
        dpg.bind_item_theme("tbl_transport", themes.layout_table)
        with dpg.table_row(parent="tbl_transport"):
            dpg.add_spacer()
            dpg.add_button(label="mute", tag="btn_mute", width=-1,
                           callback=on_mute_click)
            dpg.add_spacer()
            dpg.add_button(label="monitor on", tag="btn_monitor", width=-1,
                           callback=on_monitor_click)
            dpg.add_spacer()
        sync_transport()

        dpg.add_spacer(height=18)

        # ── Footer: 2 cols (text stretch | F9 fixed)
        _layout_table("tbl_footer", [{"stretch": True}, {"fixed": 70}])
        dpg.bind_item_theme("tbl_footer", themes.layout_table)
        with dpg.table_row(parent="tbl_footer"):
            footer_text = f"{SAMPLE_RATE // 1000} kHz · {BLOCK_SIZE} smp · 0 cb/s"
            dpg.add_text(footer_text, tag="footer_text", color=TEXT_FAINT)
            hint_btn = dpg.add_button(label="F9 log", callback=toggle_log_window)
            dpg.bind_item_theme(hint_btn, themes.link_muted)

        if themes.fonts.get("mono"):
            dpg.bind_item_font("footer_text", themes.fonts["mono"])

    # ── Hidden log window ────────────────────────────────────────────────
    with dpg.window(label="LOG", tag="log_window", show=False,
                    width=640, height=320, pos=(60, 320), no_scrollbar=True):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Copy", callback=copy_logs)
            dpg.add_button(label="Clear", callback=clear_logs)
            dpg.add_button(label="Close",
                           callback=lambda: dpg.configure_item("log_window", show=False))
        dpg.add_separator()
        dpg.add_input_text(tag="log_text", multiline=True, readonly=True,
                           width=-1, height=-1, default_value="")

    # ── F9 toggle ────────────────────────────────────────────────────────
    with dpg.handler_registry():
        dpg.add_key_press_handler(key=dpg.mvKey_F9, callback=toggle_log_window)

    # ── Drivers ──────────────────────────────────────────────────────────
    def set_footer_rates(in_rate: float, out_rate: float) -> None:
        avg = int((in_rate + out_rate) / 2)
        dpg.set_value(
            "footer_text",
            f"{SAMPLE_RATE // 1000} kHz · {BLOCK_SIZE} smp · {avg} cb/s",
        )

    def drain_logs() -> None:
        if not log_lines or not dpg.does_item_exist("log_text"):
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

    def relayout(*_args) -> None:
        new_inner = current_inner_width()
        meter.resize(new_inner)
        gain.resize(new_inner)

    def get_persisted_settings() -> Settings:
        def safe_value(tag: str, fallback: str = "") -> str:
            if dpg.does_item_exist(tag):
                try:
                    return dpg.get_value(tag) or fallback
                except Exception:
                    return fallback
            return fallback
        return Settings(
            input_label=safe_value("input_combo"),
            output_label=safe_value("output_combo", NONE_LABEL),
            monitor_label=safe_value("monitor_combo", NONE_LABEL),
            show_all_variants=bool(show_all_state["value"]),
        )

    # ── Viewport ─────────────────────────────────────────────────────────
    vp_kwargs = dict(title="Amplifier", width=WINDOW_W, height=WINDOW_H,
                     resizable=True, decorated=True,
                     min_width=440, min_height=520)
    if viewport_pos is not None:
        vp_kwargs["x_pos"], vp_kwargs["y_pos"] = viewport_pos
    dpg.create_viewport(**vp_kwargs)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_win", True)
    dpg.set_viewport_resize_callback(relayout)
    dpg.show_viewport()
    relayout()

    return UIHandles(
        meter=meter,
        gain=gain,
        set_status=set_status,
        set_footer_rates=set_footer_rates,
        drain_logs=drain_logs,
        relayout=relayout,
        get_persisted_settings=get_persisted_settings,
    )
