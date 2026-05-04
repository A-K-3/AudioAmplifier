# Amplifier

Real-time microphone amplifier with effects, dual-output routing and a Dear PyGui UI.

Captures from any input device, applies gain + effects (distortion / echo / low-pass), and routes the processed signal to two destinations in parallel: a "public" output. Built for Windows.

## Features

- Real-time mic processing at 48 kHz / 256-sample blocks (~5 ms latency)
- Effects: clean gain, soft-clip distortion, echo with feedback, one-pole low-pass
- Dual independent output streams (public + monitor) — each can live on a different host API
- Device dropdowns deduplicated by physical device, with the best host API picked automatically
- "Show all variants" toggle to fall back to MME / DirectSound when WASAPI rejects a format
- Live VU meters per stream, callback-rate counters, copyable in-app log panel

## Requirements

- Windows 10 / 11
- Python 3.10+ (tested on 3.14)

## Install

```bash
git clone <repo-url> Amplifier
cd Amplifier
python -m venv .venv
.venv\Scripts\activate
pip install sounddevice numpy dearpygui
```

## Run

```bash
python main.py
```