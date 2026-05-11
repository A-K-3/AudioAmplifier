"""Persistent user settings stored at %APPDATA%\\Amplifier\\settings.json.

Scope is intentionally narrow: only the three device choices (input, output,
monitor) plus the show-all-variants flag (which affects how device labels
resolve on next launch). Audio state (gain / effect / mute / monitor toggle)
is *not* persisted — those reset to defaults each session by design.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

APP_DIR_NAME = "Amplifier"
SETTINGS_FILENAME = "settings.json"


@dataclass
class Settings:
    # Device labels exactly as they appear in the combo (name + API suffix).
    # Stored by name rather than PortAudio index, since indices are not
    # stable across reboots or USB rearrangement.
    input_label: str = ""
    output_label: str = ""
    monitor_label: str = ""

    # Affects which device labels the combo lists on next launch.
    show_all_variants: bool = False


def settings_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home()
    return base / APP_DIR_NAME


def settings_path() -> Path:
    return settings_dir() / SETTINGS_FILENAME


def load() -> Settings:
    """Return saved Settings, falling back to defaults on missing/corrupt file."""
    path = settings_path()
    if not path.exists():
        return Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    known = {f.name for f in fields(Settings)}
    clean = {k: v for k, v in data.items() if k in known}
    try:
        return Settings(**clean)
    except TypeError:
        return Settings()


def save(s: Settings) -> None:
    """Write settings atomically; raises on I/O failure (caller handles)."""
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(asdict(s), indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)
