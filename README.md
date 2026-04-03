# MiMi Assistant

A macOS desktop assistant that activates on voice command and lets you control your computer through hand gestures — no internet required.

Say **"Hey Mycroft"** → camera opens → control your Mac with your hands.

---

## Features

- **Wake word detection** — offline, ~80ms response via [openWakeWord](https://github.com/dscripka/openWakeWord)
- **Gesture recognition** — real-time hand tracking via MediaPipe
- **Mouse control** — move cursor, click, right-click, scroll, drag & drop with your hand
- **System actions** — volume, screenshot, mute, lock screen via gestures
- **Privacy-first** — all processing runs locally, nothing leaves your machine

### Gesture Reference

| Gesture | Action | Hold |
|---|---|---|
| ILoveYou | Toggle mouse mode | 1.2s |
| Thumb Up | Volume up | 1.2s |
| Thumb Down | Volume down | 1.2s |
| Open Palm | Screenshot | 1.5s |
| Victory | Mute toggle | 1.2s |
| Closed Fist | Lock screen | 2.0s |

**Mouse mode controls** (active after ILoveYou hold):

| Action | How |
|---|---|
| Move cursor | Index fingertip |
| Left click | Pinch thumb + index |
| Double click | Pinch thumb + index, hold 1.4s |
| Right click | Pinch thumb + middle |
| Scroll | Pointing Up gesture + move |
| Drag & drop | Hand 1 pinches + Hand 2 Pointing Up |

---

## Install

### Via Homebrew (recommended)

```bash
brew tap youssif/mimi
brew install mimi-assistant
mimi-setup
```

> **Note:** Terminal must have Microphone permission.
> System Settings → Privacy & Security → Microphone → Terminal ✓

### From source

```bash
git clone https://github.com/youssif/MiMi_Assistant.git
cd MiMi_Assistant
./install.sh
```

**Prerequisite:** [Homebrew](https://brew.sh) and PortAudio:
```bash
brew install portaudio
```

---

## Usage

MiMi auto-starts whenever you open a Terminal session (set up by `mimi-setup` / `install.sh`).

```bash
mimi-ctl start     # start manually
mimi-ctl stop      # stop
mimi-ctl restart   # restart after changes
mimi-ctl status    # is it running? + last log lines
mimi-ctl logs      # live log tail
```

---

## Project Structure

```
MiMi_Assistant/
├── src/
│   ├── main.py                        # Entry point
│   ├── voice/
│   │   └── openwakeword_activator.py  # Wake word detection
│   ├── camera/
│   │   └── camera_app.py              # Gesture recognition + actions
│   ├── mouse/
│   │   └── mouse_controller.py        # Hand → mouse translation
│   ├── actions/
│   │   └── system_operations.py       # Volume, screenshot, lock, etc.
│   └── utils/
│       └── notifier.py                # macOS notifications
├── models/
│   └── gesture_recognizer.task        # MediaPipe gesture model
├── scripts/
│   ├── mimi-ctl.sh                    # Control script
│   └── mimi-setup.sh                  # Shell profile setup
├── Formula/
│   └── mimi-assistant.rb              # Homebrew formula
├── .github/workflows/
│   └── ci.yml                         # Lint + format CI
├── install.sh                         # One-command setup (git clone users)
└── uninstall.sh                       # Remove MiMi
```

---

## CI

Every push runs `ruff` lint and format checks via GitHub Actions.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
