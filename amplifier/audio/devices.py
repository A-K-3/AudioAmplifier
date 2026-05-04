from __future__ import annotations

import sounddevice as sd

NONE_LABEL = "(none)"

HOST_API_PREFERENCE = ("WASAPI", "MME", "DirectSound", "WDM-KS")

HIDDEN_NAME_PATTERNS = (
    "asignador de sonido microsoft",
    "microsoft sound mapper",
    "controlador primario",
    "primary sound",
)


def _api_rank(api_name: str) -> int:
    for i, p in enumerate(HOST_API_PREFERENCE):
        if p in api_name:
            return i
    return 999


def _api_short(api_name: str) -> str:
    for short in ("WASAPI", "WDM-KS", "DirectSound", "MME"):
        if short in api_name:
            return short
    return api_name


def _is_hidden(name: str) -> bool:
    nl = name.lower()
    return any(p in nl for p in HIDDEN_NAME_PATTERNS)


def _normalize(name: str) -> str:
    # MME truncates device names at 31 chars; collapse on that prefix so MME
    # entries dedupe with the full-name WASAPI / WDM-KS ones.
    return name[:31].strip().lower()


def list_devices(show_all: bool = False) -> tuple[dict[str, int], dict[str, int]]:
    """Return (input_map, output_map): label -> device index.

    show_all=True keeps every (device, host API) pair separately so users can
    fall back to a different API if the preferred one rejects the format.
    """
    devices = sd.query_devices()
    apis = sd.query_hostapis()

    if show_all:
        input_map: dict[str, int] = {}
        output_map: dict[str, int] = {}
        for i, d in enumerate(devices):
            name = d["name"]
            if _is_hidden(name):
                continue
            api = apis[d["hostapi"]]["name"]
            label = f"{name}  [{_api_short(api)}]"
            if d["max_input_channels"] > 0:
                input_map[label] = i
            if d["max_output_channels"] > 0:
                output_map[label] = i
        return input_map, output_map

    in_best: dict[str, tuple[int, str, str, int]] = {}
    out_best: dict[str, tuple[int, str, str, int]] = {}
    for i, d in enumerate(devices):
        name = d["name"]
        if _is_hidden(name):
            continue
        api = apis[d["hostapi"]]["name"]
        rank = _api_rank(api)
        norm = _normalize(name)

        if d["max_input_channels"] > 0:
            cur = in_best.get(norm)
            if cur is None or rank < cur[3]:
                in_best[norm] = (i, name, api, rank)
        if d["max_output_channels"] > 0:
            cur = out_best.get(norm)
            if cur is None or rank < cur[3]:
                out_best[norm] = (i, name, api, rank)

    input_map = {f"{name}  [{_api_short(api)}]": idx for (idx, name, api, _) in in_best.values()}
    output_map = {f"{name}  [{_api_short(api)}]": idx for (idx, name, api, _) in out_best.values()}
    return input_map, output_map


def label_for_index(mapping: dict[str, int], idx: int | None) -> str | None:
    if idx is None:
        return None
    for label, value in mapping.items():
        if value == idx:
            return label
    return None
