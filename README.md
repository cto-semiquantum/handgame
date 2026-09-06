# Gesture-Controlled Web Game Platform (v2)

A server-side rendered, multi-game platform powered by **Pygame**, **OpenCV**, and **MediaPipe Hands**, served to the browser as a live MJPEG stream with **zero JavaScript**.

Features two distinct game modes controlled exclusively by natural hand gestures:
1. **🏃 Endless Runner**: Fast-paced reflex runner with lane steering, jumping, sliding, and skateboard invincibility power-ups.
2. **🧩 Block Blast**: Grid-based polyomino placement puzzle with 2D hand cursor tracking, pinch-to-grab, release-to-drop, simultaneous multi-line clears, and combo multipliers.

---

## Architecture

```
Webcam --> OpenCV --> CLAHE (Luminance Boost) --> Downscale (320x240)
                            |
                            v
                   MediaPipe Hands (Inference)
                            |
                            v
       Signal Smoothing Engine (gesture.py)
       - Exponential Moving Average (EMA) on 2D coordinates
       - Lane boundary hysteresis band (±0.04)
       - N-frame gesture confirmation window (Debounce)
       - 400ms hand-lost grace period
       - Pinch detector (Thumb Tip <-> Index Tip)
                            |
                            v
                  GameManager (game.py)
                   /                 \
                  v                   v
      RunnerGame (runner_game.py)   BlockBlastGame (block_game.py)
                  \                   /
                   v                 v
           Pygame Headless Off-Screen Render
           + Picture-in-Picture (PiP) Skeleton Overlay
                            |
                            v
              cv2.imencode (JPEG bytes)
                            |
                            v
              Flask MJPEG Stream (/video_feed)
                            |
                            v
        Browser Native <img> (100% Zero JavaScript)
```

---

## Key Improvements in v2

### 1. Signal Smoothing & Detection Reliability
- **CLAHE Lighting Normalization**: Enhances the luminance channel in LAB color space to stabilize landmark detection in dim, uneven, or backlit home environments.
- **Inference Downscaling**: Downscales frames to $320 \times 240$ for MediaPipe inference without degrading the visual camera preview, cutting CPU usage and preventing frame capture stalling.
- **Exponential Moving Average (EMA)**: Eliminates high-frequency coordinate jitter while preserving responsive motion.
- **Lane Boundary Hysteresis**: Employs a $\pm 0.04$ deadband around lane thresholds so hands resting near boundaries no longer flicker between lanes.
- **Gesture Confirmation Window**: Debounces open palm (jump) and closed fist (slide) over a sliding buffer, preventing single-frame tracking glitches from firing false inputs.
- **Hand-Lost Grace Period**: Bridges momentary tracking dropouts (~400ms) by sustaining the last known position and lane state.
- **Picture-in-Picture (PiP) Preview**: Real-time camera thumbnail rendered directly onto the game screen showing the hand skeleton with green (tracking active) or red (tracking lost) status borders.

### 2. Block Blast Game Mode
- **8×8 Puzzle Grid**: Configurable in `config.py` with candy-style rounded blocks, bevel highlights, and drop shadows.
- **3-Piece Tray**: Maintains exactly 3 active pieces generated from a diverse library of polyominoes (1x1, bars, squares, Ls, Ts, Zs, corners).
- **Difficulty Progression**: Introduces more challenging shapes as your score climbs.
- **2D Hand Tracking & Pinch Interaction**:
  - Move hand $\to$ smoothed on-screen cursor.
  - Hover over tray slot + **Pinch** (Thumb + Index) $\to$ Grabs piece.
  - Drag over grid $\to$ Snapped semi-transparent ghost preview.
  - **Release Pinch** $\to$ Drops piece into grid.
  - **Dwell / Hover Fallback**: Hovering over a tray piece for 0.65s auto-selects it for accessibility.
- **Combo Scoring**: Simultaneous row and column clears trigger flashy visual bursts and score multipliers.
- **Game-Over Detection**: Instantly triggers when none of the 3 available tray pieces can legally fit anywhere on the board.

### 3. Zero-JavaScript Web Interface
- Complete application operates with JavaScript disabled in browser settings.
- Video stream leverages native browser `multipart/x-mixed-replace` image streaming.
- Mode switching, game start/restart, settings toggles, and calibration trigger standard HTTP `<form>` POST requests.
- High scores persist across server restarts in `highscores.json`.

---

## Project Structure

```
gesture_game_platform/
├── app.py               # Flask server, decoupled locks, capture loop, web routes
├── config.py            # Global constants, physics, layout, color palette
├── gesture.py           # Enhanced hand tracker, CLAHE, EMA, hysteresis, pinch detector
├── base_game.py         # Shared abstract contract for game modes
├── game.py              # GameManager: mode switcher, high score persistence, PiP composite
├── runner_game.py       # Endless Runner game loop, obstacles, collectibles, HUD
├── block_game.py        # Block Blast puzzle loop, cursor, drag-and-drop, combo banner
├── block_board.py       # 8x8 Board state, placement validation, multi-line clear logic
├── block_piece.py       # Polyomino shapes library, tray manager, candy rendering
├── player.py            # Runner player character physics and hitboxes
├── obstacles.py         # Runner obstacle manager and spawning
├── collectibles.py      # Runner coins and skateboard invincibility power-ups
├── highscores.json      # Session and persistent best score storage
├── requirements.txt     # Pinned Python package dependencies
├── templates/
│   └── index.html       # Zero-JS modern arcade UI, mode tabs, dynamic gesture guide
└── tests/
    ├── test_gesture.py  # Unit tests for EMA smoothing, hysteresis, pinch math
    ├── test_block_blast.py # Unit tests for board mechanics, line clears, combos
    └── test_runner.py   # Unit tests for player physics and collisions
```

---

## Quickstart & Setup

### 1. Requirements
Ensure Python 3.10 or 3.11 is installed.

### 2. Activate Virtual Environment & Install Dependencies
```bash
# If using existing venv from gesture_runner2:
..\gesture_runner2\venv\Scripts\activate

# Or create a fresh virtual environment:
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### 3. Run the Platform
```bash
python app.py
```

### 4. Open in Browser
Navigate to:
```
http://localhost:5000
```

1. Select your desired game mode (**Endless Runner** or **Block Blast**) from the top tabs.
2. Ensure your webcam is connected and click **▶ Start**.
3. Position your hand so the green outline appears on the top-right camera PiP thumbnail!

---

## Running the Automated Test Suite

Run all unit tests using Python's built-in test runner:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## v3.0 — Cloud Deployment Update

**The change:** v2 called `cv2.VideoCapture(0)` *on the server*. That only works when the server and the webcam are the same machine (running locally). On Render, Streamlit Cloud, or any cloud host, the server is a headless container with no camera — so `/video_feed` rendered, but no gesture data was ever produced.

**The fix:** the browser now captures the player's webcam (`getUserMedia`) and POSTs a JPEG frame roughly every 100ms to a new `POST /process_frame` endpoint, which runs the existing MediaPipe pipeline server-side and stores the result for the render loop. This does mean the "zero-JavaScript" claim in v2 no longer holds — a small capture script is required, since there is no other way for a cloud server to see a player's local camera.

Two other headless-hosting fixes bundled in this update:
- `opencv-python` → `opencv-python-headless` (the GUI build fails to import on most cloud containers with `libGL.so.1: cannot open shared object file`).
- `SDL_VIDEODRIVER`/`SDL_AUDIODRIVER` forced to `dummy` before pygame is imported, so `pygame.init()` can't hang or fail looking for a display/sound device that doesn't exist.

### Deploying on Render
1. Push this repo to GitHub.
2. In Render: New → Web Service → connect the repo. Render will detect `render.yaml` automatically (or set Build Command `pip install -r requirements.txt` and Start Command `gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT` manually).
3. **Use exactly 1 worker.** Game state (score, board, gesture tracker, high scores) lives in that process's memory — a second worker would run an entirely separate, out-of-sync game.
4. Once deployed, open the URL and allow camera access when your browser prompts — that's what feeds the game.

### Streamlit
Streamlit's execution model (script reruns top-to-bottom on every interaction, no long-lived background threads or custom routes like `/process_frame` or `/video_feed`) doesn't fit this Flask/MJPEG architecture. Render (or any other host that runs a Flask app, e.g. Railway, Fly.io, a VPS) is the natural fit and is what this update targets.

---

## v3.1 — Performance Fix (slow/laggy hand detection)

**The real bug:** the Procfile/render.yaml specified `gunicorn ... --threads 8` without `--worker-class gthread`. Gunicorn's `--threads` flag is *silently ignored* unless the worker class is `gthread` — so the app was actually running on a single-threaded `sync` worker, handling exactly one request at a time. `/video_feed` holds a connection open forever (it's a live MJPEG stream), so as soon as one client opened it, every other request — including every webcam-frame POST — queued up behind it and never got served in a timely way. That alone explains laggy/absent hand tracking far better than raw CPU load does.

Fixed: `--worker-class gthread` added, so `--threads` actually takes effect and requests are handled concurrently.

**Also decoupled inference from the HTTP request.** Previously `/process_frame` ran MediaPipe inline and didn't respond until inference finished, which meant a slow inference tick directly throttled the browser's capture loop. Now the endpoint just hands the newest frame to a dedicated background thread and returns immediately (sub-millisecond); that thread continuously processes whatever the latest frame is, dropping older unprocessed ones. This keeps the browser's send loop running at a steady pace no matter how fast or slow inference is on a given host.

Minor: skip a redundant `cv2.resize` call in `gesture.py` when the incoming frame already matches the inference resolution (it does now, since the client captures at that exact resolution), and tightened the client send interval from 100ms to 66ms (~15fps) now that it's no longer gated by processing time.

**If it's still not smooth after this:** Render's free tier gives a fraction of a CPU core, and MediaPipe + pygame rendering both want real CPU. Software fixes only go so far on a throttled instance — if performance still isn't where you want it, that's a hosting-tier ceiling, not a code bug, and upgrading to a paid instance type is the next lever.

---

## v3.2 — Build Fix: Python version file

**The bug:** `runtime.txt` is a Heroku convention — Render doesn't read it at all. With no version pin Render found, it used its own default (Python 3.14), and `mediapipe==0.10.14` only ships prebuilt wheels through Python 3.11, so the install failed with "No matching distribution found for mediapipe==0.10.14".

**Fixed:** replaced `runtime.txt` with `.python-version` (containing `3.11.9`) at the repo root — this is the file Render actually checks. `render.yaml`'s `PYTHON_VERSION` env var is left in as a backup for anyone deploying via Render's Blueprint flow, but if you connected the repo directly as a Web Service (as the build log here shows), `.python-version` is the one that takes effect.
