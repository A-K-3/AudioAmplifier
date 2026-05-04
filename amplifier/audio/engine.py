"""Audio engine: independent input/output streams connected by queues.

The duplex form is avoided so input and output may live on different host APIs
(MME / WASAPI / WDM-KS / DirectSound), which PortAudio refuses with -9993.
"""

from __future__ import annotations

import queue
import sys
import time

import numpy as np
import sounddevice as sd

from amplifier.audio.effects import EchoEffect, LowPassEffect, db_to_linear, soft_clip
from amplifier.config import (
    BLOCK_SIZE,
    ECHO_FEEDBACK,
    ECHO_MIX,
    ECHO_SECONDS,
    IN_CHANNELS,
    LOWPASS_CUTOFF_HZ,
    QUEUE_DEPTH,
    SAMPLE_RATE,
)
from amplifier.state import State


def _push(q: queue.Queue, item: np.ndarray) -> None:
    """Push, dropping the oldest item if the queue is full."""
    try:
        q.put_nowait(item)
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(item)
        except queue.Full:
            pass


class AudioEngine:
    def __init__(self):
        self.state = State()
        self.echo = EchoEffect(SAMPLE_RATE, ECHO_SECONDS, ECHO_FEEDBACK, ECHO_MIX)
        self.lowpass = LowPassEffect(SAMPLE_RATE, LOWPASS_CUTOFF_HZ)
        self.input_device: int | None = None
        self.output_device: int | None = None
        self.monitor_device: int | None = None

        self.in_stream: sd.InputStream | None = None
        self.out_stream: sd.OutputStream | None = None
        self.mon_stream: sd.OutputStream | None = None
        self.out_q: queue.Queue = queue.Queue(maxsize=QUEUE_DEPTH)
        self.mon_q: queue.Queue = queue.Queue(maxsize=QUEUE_DEPTH)
        self.last_error: str = ""

    def _make_input_callback(self, channels: int, dtype: str):
        is_int = dtype == "int16"
        scale = 1.0 / 32768.0 if is_int else 1.0
        engine = self

        def cb(indata, frames, time_info, status):
            if status:
                print(f"[input status] {status}", file=sys.stderr)
            state = engine.state
            state.in_callbacks += 1

            if channels == 1:
                raw = indata[:, 0]
            else:
                raw = indata.mean(axis=1)
            mono = raw.astype(np.float32, copy=False) * scale
            state.peak_in = float(np.max(np.abs(mono))) if mono.size else 0.0

            if state.muted:
                state.peak_out = 0.0
                return

            x = mono * db_to_linear(state.gain_db)
            if state.effect == "distortion":
                x = soft_clip(x)
            elif state.effect == "echo":
                x = engine.echo.process(x)
            elif state.effect == "lowpass":
                x = engine.lowpass.process(x)
            np.clip(x, -1.0, 1.0, out=x)
            state.peak_out = float(np.max(np.abs(x))) if x.size else 0.0

            _push(engine.out_q, x.copy())
            if state.monitor:
                _push(engine.mon_q, x.copy())

        return cb

    def _make_output_callback(self, q: queue.Queue, channels: int, dtype: str):
        is_int = dtype == "int16"
        state = self.state
        # MME/WDM-KS may deliver blocks of a different size than we asked for;
        # without preserving the leftover, audio sounds chopped/robotic.
        leftover = np.zeros(0, dtype=np.float32)

        def cb(outdata, frames, time_info, status):
            nonlocal leftover
            if status:
                print(f"[output status] {status}", file=sys.stderr)
            state.out_callbacks += 1

            buf = leftover
            while buf.size < frames:
                try:
                    blk = q.get_nowait()
                except queue.Empty:
                    break
                buf = np.concatenate((buf, blk))

            if buf.size < frames:
                pad = np.zeros(frames - buf.size, dtype=np.float32)
                buf = np.concatenate((buf, pad))

            x = buf[:frames]
            leftover = buf[frames:]

            if is_int:
                samples = (np.clip(x, -1.0, 1.0) * 32767).astype(np.int16)
            else:
                samples = x
            outdata[:, 0] = samples
            if channels >= 2:
                outdata[:, 1] = samples
            if channels > 2:
                outdata[:, 2:] = 0
        return cb

    def _open_output_stream(self, device_idx: int | None, q: queue.Queue) -> sd.OutputStream:
        info = sd.query_devices(device_idx, kind="output")
        max_ch = info["max_output_channels"]
        if max_ch <= 0:
            raise RuntimeError(f"device {device_idx} has no output channels")

        candidates: list[tuple[int, str]] = [(2, "float32")]
        if max_ch != 2:
            candidates += [(max_ch, "float32"), (max_ch, "int16")]
        candidates.append((2, "int16"))

        last_err: Exception | None = None
        for ch, dtype in candidates:
            for attempt in range(3):
                try:
                    stream = sd.OutputStream(
                        samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                        channels=ch, dtype=dtype,
                        device=device_idx,
                        callback=self._make_output_callback(q, ch, dtype),
                    )
                    stream.start()
                    print(f"[output] device={device_idx} ({info['name']}): {ch}ch {dtype}",
                          file=sys.stderr)
                    return stream
                except Exception as e:
                    last_err = e
                    msg = str(e)
                    print(f"[output] device={device_idx} {ch}ch {dtype} attempt {attempt+1} "
                          f"failed: {e}", file=sys.stderr)
                    # WASAPI endpoints can need a moment to release after close.
                    if "PaErrorCode -9999" in msg and attempt < 2:
                        time.sleep(0.3)
                        continue
                    break
        raise RuntimeError(f"could not open output device {device_idx}: {last_err}")

    @staticmethod
    def _drain(q: queue.Queue) -> None:
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break

    def _close_attr(self, attr: str) -> None:
        s = getattr(self, attr)
        if s is None:
            return
        try:
            s.stop()
            s.close()
        except Exception as e:
            print(f"[{attr} close] {e}", file=sys.stderr)
        setattr(self, attr, None)

    def open_input(self, device_idx: int | None) -> None:
        self._close_attr("in_stream")
        self.input_device = device_idx
        if device_idx is None:
            print("[input] device=None (no input)", file=sys.stderr)
            return
        info = sd.query_devices(device_idx, kind="input")
        max_in = info["max_input_channels"]
        if max_in <= 0:
            raise RuntimeError(f"device {device_idx} has no input channels")

        candidates: list[tuple[int, str]] = [(IN_CHANNELS, "float32")]
        if max_in > 1:
            candidates += [(max_in, "float32"), (max_in, "int16")]
        candidates.append((IN_CHANNELS, "int16"))

        last_err: Exception | None = None
        for ch, dtype in candidates:
            for attempt in range(3):
                try:
                    self.in_stream = sd.InputStream(
                        samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                        channels=ch, dtype=dtype,
                        device=device_idx,
                        callback=self._make_input_callback(ch, dtype),
                    )
                    self.in_stream.start()
                    print(f"[input] device={device_idx} ({info['name']}): {ch}ch {dtype}",
                          file=sys.stderr)
                    return
                except Exception as e:
                    last_err = e
                    msg = str(e)
                    print(f"[input] device={device_idx} {ch}ch {dtype} attempt {attempt+1} "
                          f"failed: {e}", file=sys.stderr)
                    if "PaErrorCode -9999" in msg and attempt < 2:
                        time.sleep(0.3)
                        continue
                    break
        raise RuntimeError(f"could not open input device {device_idx}: {last_err}")

    def open_output(self, device_idx: int | None) -> None:
        if device_idx is not None and device_idx == self.monitor_device:
            raise RuntimeError(
                "Output and Monitor cannot be the same device. Set Monitor to '(none)' "
                "or pick a different device."
            )
        self._close_attr("out_stream")
        self._drain(self.out_q)
        self.output_device = device_idx
        if device_idx is None:
            return
        self.out_stream = self._open_output_stream(device_idx, self.out_q)

    def open_monitor(self, device_idx: int | None) -> None:
        if device_idx is not None and device_idx == self.output_device:
            raise RuntimeError(
                "Monitor cannot be the same device as Output. Only set Monitor when Output "
                "goes to a device you can't hear (e.g. Realtek -> Stereo Mix)."
            )
        self._close_attr("mon_stream")
        self._drain(self.mon_q)
        self.monitor_device = device_idx
        if device_idx is None:
            return
        self.mon_stream = self._open_output_stream(device_idx, self.mon_q)

    def start(self) -> None:
        self.open_output(self.output_device)
        self.open_monitor(self.monitor_device)
        self.open_input(self.input_device)
        self.last_error = ""

    def stop(self) -> None:
        self._close_attr("in_stream")
        self._close_attr("out_stream")
        self._close_attr("mon_stream")
