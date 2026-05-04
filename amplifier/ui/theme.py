"""Linear / Vercel-inspired dark theme: zinc grays + a single lime accent."""

from __future__ import annotations

import os

import dearpygui.dearpygui as dpg

from amplifier.config import FONT_SIZE_PX

WINDOWS_FONT_DIR = r"C:\Windows\Fonts"
_REGULAR_CANDIDATES = ("segoeui.ttf", "tahoma.ttf", "arial.ttf", "calibri.ttf")
_BOLD_CANDIDATES = ("segoeuib.ttf", "tahomabd.ttf", "arialbd.ttf", "calibrib.ttf")

# Palette (RGBA)
BG = (10, 10, 11, 255)
BG_ELEVATED = (17, 17, 20, 255)
BG_SUBTLE = (27, 27, 31, 255)
BG_HOVER = (38, 38, 43, 255)
BORDER = (39, 39, 42, 255)
BORDER_HOVER = (63, 63, 70, 255)

TEXT = (250, 250, 250, 255)
TEXT_MUTED = (161, 161, 170, 255)
TEXT_SUBTLE = (113, 113, 122, 255)

ACCENT = (249, 115, 22, 255)
ACCENT_DIM = (234, 88, 12, 255)
ACCENT_DEEP = (124, 45, 18, 255)
RED = (239, 68, 68, 255)


def apply_global_theme() -> dict[str, int | None]:
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, BG_ELEVATED)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, BG_ELEVATED)
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, BG_ELEVATED)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, BG)

            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_TextSelectedBg, ACCENT_DEEP)

            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, BG_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, BG_HOVER)

            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Separator, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorHovered, BORDER_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorActive, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_Button, BG_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT_DEEP)

            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, ACCENT_DIM)

            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogramHovered, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_Header, BG_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, ACCENT_DEEP)

            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, BG_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, ACCENT_DIM)

            dpg.add_theme_color(dpg.mvThemeCol_Tab, BG_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, ACCENT_DEEP)

            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 10)
            dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing, 14)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 12)
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
    fonts: dict[str, int | None] = {"default": None, "title": None}
    regular = _find_font(_REGULAR_CANDIDATES)
    bold = _find_font(_BOLD_CANDIDATES)
    if regular is None:
        return fonts
    with dpg.font_registry():
        default_font = dpg.add_font(regular, FONT_SIZE_PX)
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Default, parent=default_font)
        fonts["default"] = default_font
        if bold is not None:
            title_font = dpg.add_font(bold, FONT_SIZE_PX + 8)
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Default, parent=title_font)
            fonts["title"] = title_font
    dpg.bind_font(default_font)
    return fonts


def make_progress_bar_theme(fill: tuple[int, int, int, int]):
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvProgressBar):
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, fill)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, BG_SUBTLE)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
    return t


def make_card_theme():
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, BG_ELEVATED)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 18, 14)
    return t
