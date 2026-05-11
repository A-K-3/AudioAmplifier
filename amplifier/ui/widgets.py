"""Minimalist channel widgets: drag-number, line meter, status dot."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import dearpygui.dearpygui as dpg

from amplifier.config import (
    GAIN_DRAG_DB_PER_PIXEL,
    GAIN_MAX_DB,
    GAIN_MIN_DB,
    METER_MAX_DB,
    METER_MIN_DB,
)
from amplifier.ui.theme import (
    RED,
    STROKE,
    TEXT,
    TEXT_FAINT,
)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _amp_to_db(amp: float) -> float:
    if amp <= 1e-6:
        return METER_MIN_DB
    return 20.0 * math.log10(amp)


def _amp_to_meter_t(amp: float) -> float:
    """Map linear 0..1 amplitude to a 0..1 meter position via dB scale."""
    db = _amp_to_db(amp)
    if db <= METER_MIN_DB:
        return 0.0
    if db >= METER_MAX_DB:
        return 1.0
    return (db - METER_MIN_DB) / (METER_MAX_DB - METER_MIN_DB)


def _level_color(t: float) -> tuple[int, int, int, int]:
    """Smooth color along the meter: muted → bright text → red at peak."""
    # 0..0.7: TEXT_FAINT → TEXT
    # 0.7..0.9: TEXT
    # 0.9..1.0: TEXT → RED
    if t <= 0.0:
        return TEXT_FAINT
    if t >= 1.0:
        return RED
    if t < 0.7:
        s = t / 0.7
        a = TEXT_FAINT
        b = TEXT
        return (
            int(a[0] + (b[0] - a[0]) * s),
            int(a[1] + (b[1] - a[1]) * s),
            int(a[2] + (b[2] - a[2]) * s),
            255,
        )
    if t < 0.9:
        return TEXT
    s = (t - 0.9) / 0.1
    a = TEXT
    b = RED
    return (
        int(a[0] + (b[0] - a[0]) * s),
        int(a[1] + (b[1] - a[1]) * s),
        int(a[2] + (b[2] - a[2]) * s),
        255,
    )


# ─── DragNumber: huge mono readout that doubles as the gain control ──────────


@dataclass
class _DragState:
    drag_active: bool = False
    drag_start_x: float = 0.0
    drag_start_value: float = 0.0


class DragNumber:
    """Big mono number — horizontal drag changes value, double-click resets."""

    def __init__(
        self,
        tag: str,
        width: int,
        height: int,
        get_value: Callable[[], float],
        set_value: Callable[[float], None],
        format_value: Callable[[float], str],
        font_big: int | None,
        font_small: int | None = None,
        unit_label: str = "dB",
        min_value: float = GAIN_MIN_DB,
        max_value: float = GAIN_MAX_DB,
        default_value: float = 0.0,
        sensitivity: float = GAIN_DRAG_DB_PER_PIXEL,
    ) -> None:
        self.tag = tag
        self.width = width
        self.height = height
        self.get_value = get_value
        self.set_value = set_value
        self.format_value = format_value
        self.font_big = font_big
        self.font_small = font_small
        self.unit_label = unit_label
        self.min = min_value
        self.max = max_value
        self.default = default_value
        self.sensitivity = sensitivity
        self.state = _DragState()
        self.text_tag = f"{tag}_value"
        self.bar_tag = f"{tag}_bar"

    # Input handling -----------------------------------------------------------

    def _on_clicked(self, _s, _a, _u):
        self.state.drag_active = True
        self.state.drag_start_x = dpg.get_mouse_pos(local=False)[0]
        self.state.drag_start_value = self.get_value()

    def _on_active(self, _s, _a, _u):
        if not self.state.drag_active:
            self.state.drag_active = True
            self.state.drag_start_x = dpg.get_mouse_pos(local=False)[0]
            self.state.drag_start_value = self.get_value()
        cur_x = dpg.get_mouse_pos(local=False)[0]
        dx = cur_x - self.state.drag_start_x
        new_v = self.state.drag_start_value + dx * self.sensitivity
        new_v = _clamp(new_v, self.min, self.max)
        self.set_value(new_v)
        self.refresh()

    def _on_deactivated(self, _s, _a, _u):
        self.state.drag_active = False

    def _on_double_click(self, _s, _a, _u):
        self.set_value(self.default)
        self.state.drag_active = False
        self.refresh()

    # Construction -------------------------------------------------------------

    def build(self) -> None:
        with dpg.drawlist(width=self.width, height=self.height, tag=self.tag):
            pass
        with dpg.item_handler_registry(tag=f"{self.tag}_handlers"):
            dpg.add_item_clicked_handler(button=0, callback=self._on_clicked)
            dpg.add_item_active_handler(callback=self._on_active)
            dpg.add_item_deactivated_handler(callback=self._on_deactivated)
            dpg.add_item_double_clicked_handler(button=0, callback=self._on_double_click)
        dpg.bind_item_handler_registry(self.tag, f"{self.tag}_handlers")
        self.refresh()

    def resize(self, width: int, height: int | None = None) -> None:
        self.width = max(120, int(width))
        if height is not None:
            self.height = max(60, int(height))
        dpg.configure_item(self.tag, width=self.width, height=self.height)
        self.refresh()

    def refresh(self) -> None:
        dpg.delete_item(self.tag, children_only=True)
        v = self.get_value()
        text = self.format_value(v)

        # Text drawn via draw_text — we use a moderately large size that's
        # crisper than scaling the bound font; DPG renders at this size from
        # the bound atlas glyphs.
        text_size = self.height - 36
        # Approx character width for Consolas-ish digits at this size:
        # Real value comes from font metrics; fudge factor 0.55 works.
        approx_w = len(text) * text_size * 0.55
        x_text = (self.width - approx_w) / 2
        y_text = (self.height - text_size) / 2 - 8
        dpg.draw_text((x_text, y_text), text, color=TEXT,
                      size=text_size, parent=self.tag)

        # Hint line under the number
        hint = "drag to adjust  ·  double-click resets"
        hint_size = 12
        hint_w = len(hint) * hint_size * 0.55
        dpg.draw_text(((self.width - hint_w) / 2,
                       y_text + text_size + 10),
                      hint, color=TEXT_FAINT, size=hint_size, parent=self.tag)


# ─── LineMeter: two thin horizontal lines (in / out) ──────────────────────────


@dataclass
class _MeterChannel:
    label: str
    last_amp: float = 0.0


@dataclass
class LineMeter:
    """Two thin horizontal level lines (top = IN, bottom = OUT)."""

    tag: str
    width: int
    height: int
    line_thickness: int = 3
    label_top: str = "in"
    label_bot: str = "out"
    channels: tuple[_MeterChannel, _MeterChannel] = field(init=False)

    def __post_init__(self):
        self.channels = (_MeterChannel(self.label_top), _MeterChannel(self.label_bot))

    def build(self) -> None:
        with dpg.drawlist(width=self.width, height=self.height, tag=self.tag):
            pass
        self.redraw()

    def resize(self, width: int, height: int | None = None) -> None:
        self.width = max(120, int(width))
        if height is not None:
            self.height = max(20, int(height))
        dpg.configure_item(self.tag, width=self.width, height=self.height)
        self.redraw()

    def update(self, amp_top: float, amp_bot: float) -> None:
        self.channels[0].last_amp = amp_top
        self.channels[1].last_amp = amp_bot
        self.redraw()

    def redraw(self) -> None:
        dpg.delete_item(self.tag, children_only=True)
        label_w = 36
        body_x0 = 0
        body_x1 = self.width - label_w - 8
        body_w = body_x1 - body_x0

        # Two stacked lines, vertically centered with a small gap
        line_gap = max(8, (self.height - 2 * self.line_thickness) // 2)
        y_top = self.height // 2 - line_gap // 2 - self.line_thickness
        y_bot = self.height // 2 + line_gap // 2

        for row, ch in enumerate(self.channels):
            y = y_top if row == 0 else y_bot
            # Background line — full width, very subtle
            dpg.draw_line(
                (body_x0, y + self.line_thickness // 2),
                (body_x1, y + self.line_thickness // 2),
                color=STROKE, thickness=self.line_thickness, parent=self.tag,
            )
            # Foreground fill
            t = _amp_to_meter_t(ch.last_amp)
            if t > 0.0:
                fill_x = body_x0 + body_w * t
                color = _level_color(t)
                dpg.draw_line(
                    (body_x0, y + self.line_thickness // 2),
                    (fill_x, y + self.line_thickness // 2),
                    color=color, thickness=self.line_thickness, parent=self.tag,
                )
            # Channel label, right-aligned
            label_x = body_x1 + 12
            label_y = y - 4
            dpg.draw_text((label_x, label_y), ch.label,
                          color=TEXT_FAINT, size=12, parent=self.tag)


# ─── Status dot ──────────────────────────────────────────────────────────────


def add_status_dot(tag: str, size: int = 12) -> None:
    with dpg.drawlist(width=size + 4, height=size + 4, tag=tag):
        pass


def update_status_dot(tag: str, color: tuple[int, int, int, int],
                      glow: bool = True, size: int = 12) -> None:
    if not dpg.does_item_exist(tag):
        return
    dpg.delete_item(tag, children_only=True)
    cx = (size + 4) / 2
    cy = (size + 4) / 2
    if glow:
        halo = (color[0], color[1], color[2], 50)
        dpg.draw_circle((cx, cy), size / 2 + 2, color=(0, 0, 0, 0), fill=halo, parent=tag)
    dpg.draw_circle((cx, cy), size / 2 - 2, color=(0, 0, 0, 0), fill=color, parent=tag)
