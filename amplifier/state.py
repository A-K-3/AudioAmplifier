from dataclasses import dataclass


@dataclass
class State:
    gain_db: float = 6.0
    effect: str = "none"   # none | distortion | echo | lowpass
    muted: bool = False
    monitor: bool = True
    peak_in: float = 0.0
    peak_out: float = 0.0
    meter_in: float = 0.0
    meter_out: float = 0.0
    in_callbacks: int = 0
    out_callbacks: int = 0
