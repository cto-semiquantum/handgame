"""
app.py - High-Performance Multi-Threaded Gesture Platform Hub (v3.0 - Cloud Edition)

Cloud-deploy architecture change (v3.0):
Cloud hosts (Render, Streamlit Cloud, etc.) run headless containers with NO
physical webcam attached, so `cv2.VideoCapture(0)` on the server can never see
the *player's* camera - it can only ever try (and fail) to see a server camera
that doesn't exist. Frame capture therefore now happens in the BROWSER via
getUserMedia, and each frame is POSTed to /process_frame for MediaPipe
inference. Rendering stays server-side, unchanged.

- Thread (_game_render_worker): Strict 30 FPS physics update and off-screen rendering
- /process_frame: receives a JPEG frame captured by the client's own webcam,
  runs MediaPipe gesture inference on it, and stores the latest result
- /api/stats: Dedicated endpoint for seamless DOM updates with ZERO page reload
"""

import os
import threading
import time

# GameManager (imported below) uses pygame purely as an off-screen 2D renderer -
# no window or audio is ever needed. Headless cloud containers (Render,
# Streamlit Cloud, etc.) have no display or sound device, and SDL's real
# video/audio drivers can fail or hang trying to find one. Forcing the
# "dummy" drivers before pygame is imported anywhere makes pygame.init()
# succeed reliably on any headless host.
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import cv2
import numpy as np
from flask import Flask, Response, render_template, redirect, url_for, request, jsonify

import config
from game import GameManager
from gesture import GestureRecognizer

app = Flask(__name__)
# Cap upload size for incoming webcam frames (protects against abuse / oversized posts)
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024  # 3 MB

game = GameManager()
recognizer = GestureRecognizer()

# --- Frame hand-off between the HTTP layer and the inference thread ---
# /process_frame used to decode + run MediaPipe inline, inside the request
# handler. That works, but it means the client's fetch() doesn't resolve
# until a full inference pass finishes - so if a frame takes 150ms to
# process, the browser's capture loop is effectively throttled to that
# speed too, and any backlog makes hand tracking feel laggy.
# Instead, /process_frame just stashes the newest raw frame and returns
# immediately (sub-millisecond), while a single dedicated thread pulls
# whatever the newest frame is and runs inference on it continuously. Old,
# not-yet-processed frames are simply dropped - we only ever care about the
# most recent one, since this is a live control signal, not a queue to drain.
_pending_lock = threading.Lock()
_pending_frame_bytes = None
_frame_ready = threading.Event()

_gesture_lock = threading.Lock()
_latest_gesture = {
    'lane': 1,
    'gesture': 'run',
    'jump_triggered': False,
    'stop_triggered': False,
    'cursor_pos': (0.5, 0.5),
    'is_pinching': False,
    'is_fist': False,
    'is_open_palm': False,
    'hand_detected': False,
    'in_grace_period': False,
    'is_calibrating': False,
    'pip_frame': None,
    'slot': None,
    'action': None,
    'move_cursor': None,
}

_frame_lock = threading.Lock()
try:
    _latest_jpeg = game.get_jpeg_bytes()
except Exception:
    _latest_jpeg = None

_last_frame_received_at = 0.0
_CAMERA_TIMEOUT_S = 2.0  # if no client frame arrives for this long, treat hand as lost

_running = True
_threads_started = False
_threads_lock = threading.Lock()


def _gesture_inference_worker():
    """Dedicated single-consumer thread: waits for a new webcam frame to
    arrive, decodes it, and runs MediaPipe on it. Because only this one
    thread ever calls recognizer.process(), there's no lock contention and
    no risk of two frames being processed out of order."""
    global _latest_gesture, _pending_frame_bytes

    while _running:
        if not _frame_ready.wait(timeout=0.5):
            continue  # no new frame recently; loop back and check _running

        _frame_ready.clear()
        with _pending_lock:
            raw = _pending_frame_bytes
            _pending_frame_bytes = None

        if raw is None:
            continue

        arr = np.frombuffer(raw, dtype=np.uint8)
        frame_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame_bgr is None:
            continue

        result = recognizer.process(frame_bgr)
        with _gesture_lock:
            _latest_gesture = result


def _game_render_worker():
    """Runs continuously, applying the latest gesture to the game and rendering
    frames. This thread never touches a camera - it only reads whatever
    /process_frame last wrote into _latest_gesture."""
    global _latest_jpeg

    target_dt = 1.0 / config.FPS

    while _running:
        try:
            start_t = time.time()

            with _gesture_lock:
                current_gesture = _latest_gesture.copy()
                # Clear one-shot pulse triggers
                _latest_gesture['jump_triggered'] = False
                _latest_gesture['stop_triggered'] = False
                _latest_gesture['action'] = None
                _latest_gesture['slot'] = None
                _latest_gesture['move_cursor'] = None

            # If the browser hasn't sent a webcam frame recently (tab backgrounded,
            # permission revoked, camera busy, page just loaded, etc.) treat the
            # hand as lost instead of freezing on stale data forever.
            if time.time() - _last_frame_received_at > _CAMERA_TIMEOUT_S:
                current_gesture['hand_detected'] = False
                current_gesture['gesture'] = 'none'
                current_gesture['in_grace_period'] = False

            game.apply_gesture(current_gesture)
            game.update(target_dt)

            jpeg_bytes = game.get_jpeg_bytes()
            if jpeg_bytes is not None:
                with _frame_lock:
                    _latest_jpeg = jpeg_bytes

            elapsed = time.time() - start_t
            sleep_time = max(0.001, target_dt - elapsed)
            time.sleep(sleep_time)
        except Exception:
            time.sleep(0.02)


_render_thread = None
_inference_thread = None


def _start_background_threads():
    """Starts the render + inference workers, guaranteeing they are alive
    both under direct execution and inside forked WSGI (gunicorn) workers."""
    global _render_thread, _inference_thread
    with _threads_lock:
        if _render_thread is None or not _render_thread.is_alive():
            _render_thread = threading.Thread(target=_game_render_worker, daemon=True)
            _render_thread.start()
        if _inference_thread is None or not _inference_thread.is_alive():
            _inference_thread = threading.Thread(target=_gesture_inference_worker, daemon=True)
            _inference_thread.start()


@app.before_request
def _ensure_threads_alive():
    """Guarantees render and inference threads are running in whichever worker handles requests."""
    if _render_thread is None or not _render_thread.is_alive() or _inference_thread is None or not _inference_thread.is_alive():
        _start_background_threads()


def _mjpeg_generator():
    """Streams MJPEG frames continuously without page refresh."""
    frame_interval = 1.0 / config.FPS
    while True:
        with _frame_lock:
            frame = _latest_jpeg

        if frame is not None:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n'
                b'Content-Length: ' + str(len(frame)).encode('ascii') + b'\r\n\r\n'
                + frame + b'\r\n'
            )
        time.sleep(frame_interval)


# ---- Web Routes ----

@app.route('/')
def index():
    state_info = game.get_state()
    return render_template(
        'index.html',
        mode=state_info['mode'],
        state=state_info['state'],
        score=state_info['score'],
        high_score=state_info['high_score'],
        show_camera_pip=state_info['show_camera_pip'],
        details=state_info['details'],
        camera_mirror=config.CAMERA_MIRROR,
        inference_width=config.INFERENCE_WIDTH,
        inference_height=config.INFERENCE_HEIGHT,
    )


@app.route('/api/stats')
def api_stats():
    """Returns real-time JSON statistics so page can update cleanly with zero blink."""
    state_info = game.get_state()
    with _gesture_lock:
        g = _latest_gesture.copy()

    camera_active = (time.time() - _last_frame_received_at) <= _CAMERA_TIMEOUT_S

    return jsonify({
        'mode': state_info['mode'],
        'state': state_info['state'],
        'score': state_info['score'],
        'high_score': state_info['high_score'],
        'distance_m': state_info['details'].get('distance_m', 0),
        'coins': state_info['details'].get('coins', 0),
        'combo_streak': state_info['details'].get('combo_streak', 0),
        'held_piece': state_info['details'].get('held_piece'),
        'gesture': g.get('gesture', 'run'),
        'lane': g.get('lane', 1),
        'cursor_pos': g.get('cursor_pos'),
        'is_pinching': g.get('is_pinching', False),
        'is_fist': g.get('is_fist', False),
        'is_open_palm': g.get('is_open_palm', False),
        'hand_detected': g.get('hand_detected', False) and camera_active,
        'camera_active': camera_active,
        'show_camera_pip': game.show_camera_pip,
        'camera_mirror': config.CAMERA_MIRROR,
    })


@app.route('/video_feed')
def video_feed():
    response = Response(
        _mjpeg_generator(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@app.route('/current_frame.jpg')
def current_frame():
    with _frame_lock:
        frame = _latest_jpeg
    if frame is None:
        frame = game.get_jpeg_bytes()
    if frame is None:
        return ('', 204)
    response = Response(frame, mimetype='image/jpeg')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@app.route('/process_frame', methods=['POST'])
def process_frame():
    """Receives one JPEG frame captured by the CLIENT's webcam (browser-side
    getUserMedia) and hands it off to the dedicated inference thread. This
    returns almost immediately - it does NOT wait for MediaPipe to finish -
    so the browser's capture loop never gets throttled by inference speed."""
    global _pending_frame_bytes, _last_frame_received_at

    raw = request.get_data()
    if not raw:
        return jsonify({'ok': False, 'error': 'empty frame'}), 400

    with _pending_lock:
        _pending_frame_bytes = raw
    _frame_ready.set()
    _last_frame_received_at = time.time()

    return jsonify({'ok': True})


def _action_response(extra=None):
    if (request.is_json or 
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '')):
        data = {'ok': True, 'state': game.get_state()}
        if extra:
            data.update(extra)
        return jsonify(data)
    return redirect(url_for('index'))


@app.route('/select_mode', methods=['POST'])
def select_mode():
    data = request.get_json(silent=True) or {}
    new_mode = request.form.get('mode') or data.get('mode') or 'runner'
    game.set_mode(new_mode)
    return _action_response({'mode': new_mode})


@app.route('/start', methods=['POST'])
def start():
    game.start()
    return _action_response()


@app.route('/restart', methods=['POST'])
def restart():
    game.start()
    return _action_response()


@app.route('/toggle_pip', methods=['POST'])
def toggle_pip():
    game.show_camera_pip = not game.show_camera_pip
    return _action_response({'show_camera_pip': game.show_camera_pip})


@app.route('/calibrate', methods=['POST'])
def calibrate():
    recognizer.start_calibration(duration_s=1.5)
    return _action_response({'is_calibrating': True})


@app.route('/toggle_mirror', methods=['POST'])
def toggle_mirror():
    config.CAMERA_MIRROR = not config.CAMERA_MIRROR
    return _action_response({'camera_mirror': config.CAMERA_MIRROR})


@app.route('/api/action', methods=['POST'])
def api_action():
    """High-speed gesture telemetry & action endpoint.
    Accepts lightweight JSON signals from client-side hand tracker (0ms latency, zero bandwidth bloat)
    or keyboard fallback."""
    global _last_frame_received_at
    _last_frame_received_at = time.time()

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    action = data.get('action')
    lane = data.get('lane')
    cursor = data.get('cursor')
    is_pinching = data.get('is_pinching')
    is_fist = data.get('is_fist')
    is_open_palm = data.get('is_open_palm')
    hand_detected = data.get('hand_detected')

    slot = data.get('slot')
    move_cursor = data.get('move_cursor')

    with _gesture_lock:
        if hand_detected is not None:
            _latest_gesture['hand_detected'] = bool(hand_detected)
        if lane is not None:
            _latest_gesture['lane'] = max(0, min(2, int(lane)))
            _latest_gesture['hand_detected'] = True
        if cursor is not None and isinstance(cursor, (list, tuple)) and len(cursor) >= 2:
            _latest_gesture['cursor_pos'] = (max(0.0, min(1.0, float(cursor[0]))),
                                             max(0.0, min(1.0, float(cursor[1]))))
            _latest_gesture['hand_detected'] = True
        if slot is not None:
            _latest_gesture['slot'] = int(slot)
            _latest_gesture['hand_detected'] = True
        if move_cursor is not None:
            _latest_gesture['move_cursor'] = move_cursor
            _latest_gesture['hand_detected'] = True
        if is_pinching is not None:
            _latest_gesture['is_pinching'] = bool(is_pinching)
        if is_fist is not None:
            _latest_gesture['is_fist'] = bool(is_fist)
        if is_open_palm is not None:
            _latest_gesture['is_open_palm'] = bool(is_open_palm)

        if action == 'jump':
            _latest_gesture['jump_triggered'] = True
            _latest_gesture['gesture'] = 'jump'
        elif action in ('stop', 'pause'):
            _latest_gesture['stop_triggered'] = True
            _latest_gesture['gesture'] = 'stop'
        elif action == 'run':
            _latest_gesture['gesture'] = 'run'
        elif action in ('drop', 'place', 'cancel', 'return_tray'):
            _latest_gesture['action'] = action
        elif action == 'left':
            _latest_gesture['lane'] = 0
            _latest_gesture['hand_detected'] = True
        elif action == 'center':
            _latest_gesture['lane'] = 1
            _latest_gesture['hand_detected'] = True
        elif action == 'right':
            _latest_gesture['lane'] = 2
            _latest_gesture['hand_detected'] = True

    if action == 'start':
        game.start()
    elif action == 'restart':
        game.start()

    return jsonify({'ok': True, 'state': game.get_state()})


@app.route('/healthz')
def healthz():
    """Simple health check endpoint for Render / uptime monitors."""
    return jsonify({'status': 'ok'})


# Start the render worker as soon as the module loads, so it works both under
# `python app.py` (local dev) AND under a WSGI server like gunicorn in
# production (gunicorn never runs the `if __name__ == "__main__"` block below).
_start_background_threads()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    try:
        app.run(host='0.0.0.0', port=port, threaded=True, debug=False)
    finally:
        _running = False
        recognizer.close()
