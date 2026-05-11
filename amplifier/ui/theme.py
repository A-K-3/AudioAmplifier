"""Channel-strip dark theme: deep slate body, segmented LED palette, single accent."""

from __future__ import annotations

import os

import dearpygui.dearpygui as dpg

from amplifier.config import FONT_SIZE_PX

WINDOWS_FONT_DIR = r"C:\Windows\Fonts"
_REGULAR_CANDIDATES = ("segoeui.ttf", "tahoma.ttf", "arial.ttf", "calibri.ttf")
_BOLD_CANDIDATES = ("segoeuib.ttf", "tahomabd.ttf", "arialbd.ttf", "calibrib.ttf")
_MONO_CANDIDATES = ("consola.ttf", "lucon.ttf", "cour.ttf", "consolab.ttf")

# Recent Dear PyGui builds load all glyphs the TTF supports automatically;
# we no longer pre-declare ranges. Spanish accents and ▸ render directly.

# Palette (RGBA)
BG_DEEP = (6, 6, 8, 255)            # outermost / window
BG_PANEL = (14, 14, 17, 255)        # strip body card
BG_RECESS = (4, 4, 6, 255)          # inset wells (meter / knob backplate)
BG_RAISED = (24, 24, 28, 255)       # chips, pills idle
BG_HOVER = (38, 38, 44, 255)
STROKE = (32, 32, 38, 255)
STROKE_HI = (62, 62, 70, 255)

TEXT = (245, 245, 245, 255)
TEXT_MUTED = (160, 160, 168, 255)
TEXT_SUBTLE = (100, 100, 108, 255)
TEXT_FAINT = (70, 70, 78, 255)

ACCENT = (249, 115, 22, 255)        # orange — single accent
ACCENT_DIM = (194, 84, 14, 255)
ACCENT_DEEP = (88, 35, 12, 255)
ACCENT_GLOW = (249, 115, 22, 70)    # translucent halo

GREEN = (74, 222, 128, 255)         # monitor on
GREEN_DEEP = (22, 101, 52, 255)
RED = (239, 68, 68, 255)            # mute / peak
RED_DEEP = (127, 29, 29, 255)
YELLOW = (250, 204, 21, 255)        # mid zone

# Meter LED palette
METER_OFF = (26, 26, 30, 255)
METER_GREEN_ON = (74, 222, 128, 255)
METER_GREEN_OFF = (22, 60, 36, 255)
METER_YELLOW_ON = (250, 204, 21, 255)
METER_YELLOW_OFF = (84, 65, 8, 255)
METER_RED_ON = (239, 68, 68, 255)
METER_RED_OFF = (90, 22, 22, 255)


def apply_global_theme() -> dict[str, int | None]:
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG_DEEP)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, BG_DEEP)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, BG_DEEP)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, BG_DEEP)

            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_TextSelectedBg, ACCENT_DEEP)

            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, BG_RAISED)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, BG_HOVER)

            dpg.add_theme_color(dpg.mvThemeCol_Border, STROKE)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Separator, STROKE)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorHovered, STROKE_HI)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorActive, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_Button, BG_RAISED)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT_DEEP)

            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, ACCENT_DIM)

            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogramHovered, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_Header, BG_RAISED)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, ACCENT_DEEP)

            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, BG_DEEP)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, BG_RAISED)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, ACCENT_DIM)

            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 10)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 8)
            dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing, 14)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 10)
            dpg.add_theme_style(dpg.mvStyleVar_GrabMinSize, 14)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 18, 16)

    dpg.bind_theme(global_theme)
    return _load_fonts()


def _find_font(candidates: tuple[str, ...]) -> str | None:
    for name in candidates:
        path = os.path.join(WINDOWS_FONT_DIR, name)
        if os.path.exists(path):
            return path
    return None


def _load_fonts() -> dict[str, int | None]:
    fonts: dict[str, int | None] = {
        "default": None, "title": None, "mono": None, "mono_big": None, "small": None,
    }
    regular = _find_font(_REGULAR_CANDIDATES)
    bold = _find_font(_BOLD_CANDIDATES)
    mono = _find_font(_MONO_CANDIDATES)
    if regular is None:
        return fonts
    with dpg.font_registry():
        default_font = dpg.add_font(regular, FONT_SIZE_PX)
        fonts["default"] = default_font
        fonts["small"] = dpg.add_font(regular, FONT_SIZE_PX - 3)
        if bold is not None:
            fonts["title"] = dpg.add_font(bold, FONT_SIZE_PX + 6)
        if mono is not None:
            fonts["mono"] = dpg.add_font(mono, FONT_SIZE_PX - 2)
            fonts["mono_big"] = dpg.add_font(mono, FONT_SIZE_PX + 14)
    dpg.bind_font(default_font)
    return fonts


def make_ghost_button_theme():
    """Borderless small button (header gear, log close, etc)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, BG_RAISED)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_MUTED)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
    return t
