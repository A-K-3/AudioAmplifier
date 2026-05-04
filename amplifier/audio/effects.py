from __future__ import annotations

import numpy as np


def db_to_linear(db: float) -> float:
    # Cap so runaway slider values can't exceed float32 range (~3.4e38).
    return float(10.0 ** (min(db, 300.0) / 20.0))


def soft_clip(x: np.ndarray, drive: float = 3.0) -> np.ndarray:
    return np.tanh(x * drive).astype(np.float32)


class EchoEffect:
    def __init__(self, sample_rate: int, seconds: float, feedback: float, mix: float):
        self.buf = np.zeros(int(sample_rate * seconds), dtype=np.float32)
        self.idx = 0
        self.feedback = feedback
        self.mix = mix

    def process(self, x: np.ndarray) -> np.ndarray:
        out = np.empty_like(x)
        buf = self.buf
        n = buf.size
        i = self.idx
        fb = self.feedback
        mix = self.mix
        for k in range(x.size):
            delayed = buf[i]
            sample = x[k] + delayed * fb
            buf[i] = sample
            out[k] = x[k] * (1 - mix) + delayed * mix
            i = (i + 1) % n
        self.idx = i
        return out


class LowPassEffect:
    """One-pole IIR low-pass filter."""

    def __init__(self, sample_rate: int, cutoff_hz: float):
        rc = 1.0 / (2 * np.pi * cutoff_hz)
        dt = 1.0 / sample_rate
        self.alpha = dt / (rc + dt)
        self.prev = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        out = np.empty_like(x)
        a = self.alpha
        y = self.prev
        for k in range(x.size):
            y = y + a * (x[k] - y)
            out[k] = y
        self.prev = y
        return out
