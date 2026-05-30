"""
app.py – Football AI Analytics Backend
---------------------------------------
Video detection uses FootballAnalyzer. Match Event Spotting uses the
ball_model_FULL_OBJECT.pt pipeline directly.

Start:
    cd backend/Ai
    python app.py
"""

import os
import sys
import uuid
import threading
import time
import io
import subprocess
import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request
import cv2
import numpy as np
from collections import defaultdict, deque
from functools import wraps
from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
from ultralytics import YOLO
import supervision as sv

# ── Import the module (all inference goes through it) ──────────────────────────
os.environ.setdefault("KERAS_BACKEND", "numpy")  # must be set BEFORE keras import
from module import FootballAnalyzer, ActionRecognitionModel

try:
    import torch
except ImportError:
    torch = None

DEVICE = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(
    app,
    origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:4201",
        "http://127.0.0.1:4201",
    ],
    allow_headers=["Content-Type", "Authorization"],
)

JWT_SECRET = (
    os.getenv("JWT_SECRET")
    or os.getenv("Jwt__Secret")
    or "AI-Sports-Analytics-Development-JWT-Secret-Change-Me-2026"
)
JWT_ISSUER = os.getenv("JWT_ISSUER") or os.getenv("Jwt__Issuer") or "AI Sports Analytics"
JWT_AUDIENCE = (
    os.getenv("JWT_AUDIENCE")
    or os.getenv("Jwt__Audience")
    or "AI Sports Analytics Frontend"
)
ROLE_CLAIM = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
AUTHENTICATED_ROLES = {"Admin", "User"}


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _decode_jwt(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid access token.")

    header = json.loads(_base64url_decode(parts[0]))
    if header.get("alg") != "HS256":
        raise ValueError("Unsupported access token.")

    signed_value = f"{parts[0]}.{parts[1]}".encode("utf-8")
    expected_signature = hmac.new(
        JWT_SECRET.encode("utf-8"),
        signed_value,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(_base64url_decode(parts[2]), expected_signature):
        raise ValueError("Invalid access token signature.")

    payload = json.loads(_base64url_decode(parts[1]))
    now = int(time.time())

    if int(payload.get("exp", 0)) <= now:
        raise ValueError("Access token has expired.")
    if payload.get("iss") != JWT_ISSUER:
        raise ValueError("Invalid access token issuer.")

    audience = payload.get("aud")
    if isinstance(audience, list):
        valid_audience = JWT_AUDIENCE in audience
    else:
        valid_audience = audience == JWT_AUDIENCE

    if not valid_audience:
        raise ValueError("Invalid access token audience.")

    return payload


def require_auth(*allowed_roles):
    def decorator(handler):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.lower().startswith("bearer "):
                return jsonify({"error": "Authentication is required."}), 401

            try:
                payload = _decode_jwt(auth_header[7:].strip())
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 401

            role = payload.get("role") or payload.get(ROLE_CLAIM)
            if allowed_roles and role not in allowed_roles:
                return jsonify({"error": "You do not have permission to access this resource."}), 403

            request.current_user = payload
            return handler(*args, **kwargs)

        return wrapper

    return decorator


def _refresh_job_auth_from_request(job: dict | None) -> None:
    """Keep long-running jobs paired with the newest valid bearer token from polling."""
    if job is None:
        return

    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        job["auth_header"] = auth_header
        current_user = getattr(request, "current_user", {}) or {}
        job["auth_expires_at"] = current_user.get("exp")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PLAYER_MODEL_PATH = os.path.join(BASE_DIR, "best.pt")
FIELD_MODEL_PATH  = os.path.join(BASE_DIR, "yolo-football-pitch-detection.pt")
BALL_ACTION_MODEL_PATH = os.path.join(BASE_DIR, "ball_model_FULL_OBJECT.pt")
BALL_ACTION_CONFIG_PATH = os.path.join(BASE_DIR, "ball_action_model_config.json")
DOTNET_API_BASE = os.getenv("DOTNET_API_BASE", "http://localhost:5067").rstrip("/")


DEFAULT_BALL_ACTION_CONFIG = {
    "UrlLocal": "match",
    "range": {
        "halves": [1],
        "start_ms": 0,
        "end_ms": 0,
        "start_frame": 0,
        "end_frame": 0,
    },
    "classes": [
        "PASS_left",
        "PASS_right",
        "DRIVE_left",
        "DRIVE_right",
        "HIGH PASS_left",
        "HIGH PASS_right",
        "HEADER_left",
        "HEADER_right",
        "OUT_left",
        "OUT_right",
        "THROW IN_left",
        "THROW IN_right",
    ],
    "input": {
        "num_frames": 15,
        "frame_step": 2,
        "image_height": 736,
        "image_width": 1280,
        "predict_stride_frames": 1,
        "batch_size": 4,
    },
    "postprocess": {
        "gauss_sigma": 3.0,
        "height": 0.2,
        "distance_frames": 15,
    },
    "analytics_labels": ["HIGH PASS", "HEADER", "OUT", "THROW IN"],
    "rule": "Only one prediction per same second per half. Keep highest confidence.",
    "predictions": [],
}


def _load_ball_action_config() -> dict:
    try:
        with open(BALL_ACTION_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as exc:
        print(f"[STARTUP] Ball action config warning: {exc}; using defaults.", flush=True)
        config = dict(DEFAULT_BALL_ACTION_CONFIG)

    merged = dict(DEFAULT_BALL_ACTION_CONFIG)
    merged.update(config)
    merged["range"] = {**DEFAULT_BALL_ACTION_CONFIG["range"], **config.get("range", {})}
    merged["input"] = {**DEFAULT_BALL_ACTION_CONFIG["input"], **config.get("input", {})}
    merged["postprocess"] = {
        **DEFAULT_BALL_ACTION_CONFIG["postprocess"],
        **config.get("postprocess", {}),
    }
    return merged


BALL_ACTION_CONFIG = _load_ball_action_config()

# ── Load models ONCE at startup ────────────────────────────────────────────────
print("[STARTUP] Loading YOLO models …")
try:
    PLAYER_MODEL = YOLO(PLAYER_MODEL_PATH)
    FIELD_MODEL  = YOLO(FIELD_MODEL_PATH)
    print("[STARTUP] Models loaded successfully.")
except Exception as e:
    PLAYER_MODEL = None
    FIELD_MODEL  = None
    print(f"[STARTUP] ERROR loading models: {e}")

# ── Load Ball Action model ONCE at startup ─────────────────────────────────────
# This model detects: throw_in, out, high_pass, header
BALL_ACTION_MODEL_ERROR = None
print("[STARTUP] Loading Ball Action model …")
try:
    # Add current directory to path so ultralytics can unpickle the 'src' module
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    if torch is None:
        raise RuntimeError("PyTorch is not installed.")

    BALL_ACTION_MODEL = torch.load(
        BALL_ACTION_MODEL_PATH,
        map_location=DEVICE,
        weights_only=False,
    )
    BALL_ACTION_MODEL.eval()
    BALL_ACTION_MODEL.to(DEVICE)
    BALL_ACTION_CLASSES = {
        idx: name for idx, name in enumerate(BALL_ACTION_CONFIG.get("classes", []))
    }
    print(f"[STARTUP] Ball Action model loaded. Classes: {BALL_ACTION_CLASSES}")
except Exception as e:
    BALL_ACTION_MODEL = None
    BALL_ACTION_CLASSES = {}
    BALL_ACTION_MODEL_ERROR = (
        f"{type(e).__name__}: {e}. Expected a PyTorch 15-frame action spotting "
        "checkpoint with the 12 classes from ball_action_model_config.json."
    )
    print(f"[STARTUP] WARNING: Ball Action model failed to load: {e}")
    print("[STARTUP]   Action spotting jobs are disabled until the correct model is provided.")

BALL_ACTION_MODEL_LOCK = threading.Lock()

# ── Load Keras action recognition model ONCE at startup ────────────────────────
print("[STARTUP] Loading Keras action recognition model …")
try:
    ACTION_MODEL = ActionRecognitionModel()
    print("[STARTUP] Action recognition model loaded successfully.")
except Exception as e:
    ACTION_MODEL = None
    print(f"[STARTUP] ERROR loading action recognition model: {e}")

# ── Device detection ───────────────────────────────────────────────────────────
print(f"[STARTUP] Inference device: {DEVICE}")

# ── Pre-warm TeamClassifier (downloads DINOv2 on first run) ───────────────────
# This runs ONCE at startup in a background thread so the model is cached
# before any job arrives. Prevents the job from silently hanging at 5%.
def _prewarm_team_classifier():
    try:
        from sports.common.team import TeamClassifier
        print("[STARTUP] Pre-warming TeamClassifier (DINOv2 download if first run) …", flush=True)
        _tc = TeamClassifier(device=DEVICE)
        print("[STARTUP] TeamClassifier ready.", flush=True)
    except Exception as e:
        print(f"[STARTUP] TeamClassifier pre-warm warning: {e}", flush=True)

_prewarm_thread = threading.Thread(target=_prewarm_team_classifier, daemon=True)
_prewarm_thread.start()

# ── In-memory job store ────────────────────────────────────────────────────────
# jobs[job_id] = {
#   status: "queued" | "preparing_video" | "training_team_classifier" |
#           "processing_frames" | "encoding" | "done" | "error"
#   progress: int 0-100
#   stage: same as status
#   processed_frames: int
#   total_frames: int
#   error: str | None
#   output_path: str | None
#   analyzer: FootballAnalyzer | None   ← kept alive for heatmap requests
#   player_stats: dict
# }
jobs: dict = {}
jobs_lock = threading.Lock()

# ── Helper: pick the best available MP4 fourcc ────────────────────────────────
def _get_fourcc():
    # avc1 requires libopenh264 which has version issues on this system.
    # We write with mp4v then re-encode to H.264 with ffmpeg (see _reencode_h264).
    for code in ("mp4v", "XVID", "MJPG"):
        fcc = cv2.VideoWriter_fourcc(*code)
        if fcc != -1:
            return fcc, code
    return cv2.VideoWriter_fourcc(*"mp4v"), "mp4v"


# ── Helper: re-encode mp4v → H.264 using bundled imageio-ffmpeg ───────────────
def _reencode_h264(src_path: str, dst_path: str) -> bool:
    """Convert src (mp4v) → dst (H.264/aac) so browsers can play the result.
    Returns True on success, False if ffmpeg unavailable or conversion failed."""
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return False

    try:
        result = subprocess.run(
            [ffmpeg_exe, "-y", "-i", src_path,
             "-vcodec", "libx264", "-preset", "fast", "-crf", "23",
             "-movflags", "+faststart",   # enables streaming / progressive play
             dst_path],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            print(f"[FFMPEG] Re-encode failed:\n{result.stderr}", flush=True)
            return False
        return True
    except Exception as e:
        print(f"[FFMPEG] Exception during re-encode: {e}", flush=True)
        return False


# ── Helper: attribute a ball action to the nearest tracked player's team ───────
def _attribute_to_team(bx: float, by: float, analyzer, frame_idx: int) -> str:
    """Given the (bx, by) centre of a ball-action detection, find the nearest
    tracked player and return 'team_1' or 'team_2' based on their team id."""
    best_dist = float("inf")
    best_team = None

    # analyzer.heatmap_coordinates maps tracker_id → deque of (x, y)
    for tracker_id, coords_deque in analyzer.heatmap_coordinates.items():
        if not coords_deque:
            continue
        # Use the latest known position of the player
        px, py = coords_deque[-1]
        dist = float(np.hypot(bx - px, by - py))
        if dist < best_dist:
            best_dist = dist
            team_history = list(analyzer.player_team_history.get(tracker_id, []))
            if team_history:
                best_team = max(set(team_history), key=team_history.count)
            else:
                best_team = None

    if best_team is not None:
        return "team_1" if int(best_team) == 0 else "team_2"

    # Fallback: alternate between teams
    return "team_1" if frame_idx % 2 == 0 else "team_2"


def _empty_ball_action_stats() -> dict:
    names = ["throw_in", "out", "high_pass", "header"]
    return {
        "team_1": {name: 0 for name in names},
        "team_2": {name: 0 for name in names},
    }


def _split_ball_action_class(class_name: str) -> tuple[str, str] | tuple[None, None]:
    if "_" not in class_name:
        return None, None
    label, team = class_name.rsplit("_", 1)
    return label.strip().upper(), team.strip().lower()


def _ball_action_stats_key(label: str) -> str | None:
    key = label.strip().lower().replace(" ", "_").replace("-", "_")
    return key if key in {"throw_in", "out", "high_pass", "header"} else None


def _format_game_time(half: int, second: int) -> str:
    minutes = max(0, int(second)) // 60
    seconds = max(0, int(second)) % 60
    return f"{int(half)} - {minutes:02d}:{seconds:02d}"


def _read_ball_action_frame_gray(cap, frame_index: int, total_frames: int,
                                 image_width: int, image_height: int) -> np.ndarray:
    frame_index = max(0, min(int(frame_index), total_frames - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    if not ret:
        raise RuntimeError(f"Could not read frame {frame_index} for ball action spotting.")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (image_width, image_height))


def _read_ball_action_clip_from_video(cap, center_frame: int, total_frames: int):
    input_cfg = BALL_ACTION_CONFIG.get("input", {})
    num_frames = int(input_cfg.get("num_frames", 15))
    frame_step = int(input_cfg.get("frame_step", 2))
    image_height = int(input_cfg.get("image_height", 736))
    image_width = int(input_cfg.get("image_width", 1280))
    center_frame = max(0, min(int(center_frame), total_frames - 1))
    mid = num_frames // 2

    frames = []
    for idx in range(num_frames):
        offset = (idx - mid) * frame_step
        frame_index = max(0, min(center_frame + offset, total_frames - 1))
        frames.append(
            _read_ball_action_frame_gray(
                cap,
                frame_index,
                total_frames,
                image_width,
                image_height,
            )
        )

    clip = np.stack(frames).astype(np.float32) / 255.0
    clip = clip[:, None, :, :]
    return torch.from_numpy(clip)


def _predict_ball_action_batch(clips: list) -> np.ndarray:
    batch = torch.stack(clips, dim=0)
    if batch.ndim == 4:
        batch = batch.unsqueeze(2)
    batch = batch.to(DEVICE, non_blocking=True)
    with torch.no_grad():
        with BALL_ACTION_MODEL_LOCK:
            output = BALL_ACTION_MODEL(batch)
            classifier = getattr(BALL_ACTION_MODEL, "classifier", None)
            if classifier is not None and output.shape[-1] == classifier.in_features:
                output = classifier(output)
            return torch.sigmoid(output).detach().float().cpu().numpy()


def _predict_ball_action_video_score_points(
    video_path: str,
    total_frames: int,
    progress_callback=None,
) -> list[dict]:
    if BALL_ACTION_MODEL is None or torch is None or total_frames <= 0:
        return []

    input_cfg = BALL_ACTION_CONFIG.get("input", {})
    predict_stride = max(1, int(input_cfg.get("predict_stride_frames", 1)))
    batch_size = max(1, int(input_cfg.get("batch_size", 4)))

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not reopen video for ball action spotting: {video_path}")

    score_points = []
    batch_clips = []
    batch_indexes = []
    try:
        for frame_index in range(0, total_frames, predict_stride):
            batch_clips.append(_read_ball_action_clip_from_video(cap, frame_index, total_frames))
            batch_indexes.append(frame_index)

            if len(batch_clips) == batch_size:
                probabilities = _predict_ball_action_batch(batch_clips)
                for idx, scores in zip(batch_indexes, probabilities):
                    score_points.append({"frame": int(idx), "scores": scores})
                if progress_callback is not None:
                    progress_callback(batch_indexes[-1] + 1, total_frames)
                batch_clips = []
                batch_indexes = []

        if batch_clips:
            probabilities = _predict_ball_action_batch(batch_clips)
            for idx, scores in zip(batch_indexes, probabilities):
                score_points.append({"frame": int(idx), "scores": scores})
            if progress_callback is not None:
                progress_callback(batch_indexes[-1] + 1, total_frames)
    finally:
        cap.release()

    return score_points


def _smooth_scores(scores: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0 or len(scores) < 3:
        return scores
    try:
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(scores, sigma=sigma)
    except Exception:
        radius = max(1, int(round(sigma * 3)))
        xs = np.arange(-radius, radius + 1, dtype=np.float32)
        kernel = np.exp(-(xs ** 2) / (2 * sigma ** 2))
        kernel = kernel / kernel.sum()
        padded = np.pad(scores, (radius, radius), mode="edge")
        return np.convolve(padded, kernel, mode="valid")


def _find_score_peaks(scores: np.ndarray, height: float, min_distance: int) -> list[int]:
    if len(scores) == 0:
        return []

    try:
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(scores, height=height, distance=max(1, int(min_distance)))
        return [int(peak) for peak in peaks]
    except Exception:
        pass

    candidates = []
    for idx, score in enumerate(scores):
        if float(score) < height:
            continue
        left = scores[idx - 1] if idx > 0 else -np.inf
        right = scores[idx + 1] if idx + 1 < len(scores) else -np.inf
        if score >= left and score >= right:
            candidates.append(idx)

    kept = []
    for idx in sorted(candidates, key=lambda i: float(scores[i]), reverse=True):
        if all(abs(idx - other) >= min_distance for other in kept):
            kept.append(idx)
    return sorted(kept)


def _build_ball_action_predictions(score_points: list[dict], fps: float) -> list[dict]:
    if not score_points:
        return []

    post_cfg = BALL_ACTION_CONFIG.get("postprocess", {})
    input_cfg = BALL_ACTION_CONFIG.get("input", {})
    stride_frames = max(1, int(input_cfg.get("predict_stride_frames", 1)))
    sigma_frames = float(post_cfg.get("gauss_sigma", 3.0))
    sigma_samples = sigma_frames / stride_frames
    height = float(post_cfg.get("height", 0.2))
    min_distance_frames = max(1, int(post_cfg.get("distance_frames", 15)))
    min_distance_samples = max(1, int(round(min_distance_frames / stride_frames)))

    class_names = BALL_ACTION_CONFIG.get("classes", [])
    score_matrix = np.array([point["scores"] for point in score_points], dtype=np.float32)
    predictions = []

    for class_idx, class_name in enumerate(class_names):
        if class_idx >= score_matrix.shape[1]:
            break
        label, team = _split_ball_action_class(class_name)
        if not label or not team:
            continue

        smoothed = _smooth_scores(score_matrix[:, class_idx], sigma_samples)
        for point_idx in _find_score_peaks(smoothed, height, min_distance_samples):
            point = score_points[point_idx]
            frame = int(point["frame"])
            second = int(frame / fps) if fps > 0 else int(point_idx)
            position_ms = int((frame / fps) * 1000) if fps > 0 else 0
            confidence = float(smoothed[point_idx])
            predictions.append({
                "gameTime": _format_game_time(1, second),
                "label": label,
                "team": team,
                "position": str(position_ms),
                "half": "1",
                "confidence": str(confidence),
                "frame": frame,
                "class_name": class_name,
                "second": second,
            })

    return _filter_ball_action_predictions(predictions)


def _filter_ball_action_predictions(predictions: list[dict]) -> list[dict]:
    best_by_second = {}
    for prediction in predictions:
        half = str(prediction.get("half", "1"))
        position_ms = int(prediction.get("position", 0) or 0)
        second = position_ms // 1000
        key = (half, second)
        confidence = float(prediction.get("confidence", 0) or 0)
        current = best_by_second.get(key)
        old_confidence = float(current.get("confidence", 0) or 0) if current else -1.0
        if current is None or confidence > old_confidence:
            best_by_second[key] = prediction

    return sorted(
        best_by_second.values(),
        key=lambda item: (int(item.get("half", 1)), int(item.get("position", 0) or 0)),
    )


def _stats_from_ball_action_predictions(predictions: list[dict]) -> dict:
    stats = _empty_ball_action_stats()
    for prediction in predictions:
        stats_key = _ball_action_stats_key(str(prediction.get("label", "")))
        if not stats_key:
            continue
        team_key = "team_1" if str(prediction.get("team", "")).lower() == "left" else "team_2"
        stats[team_key][stats_key] += 1
    return stats


def _write_ball_action_predictions(job_id: str, predictions: list[dict],
                                   total_frames: int, fps: float) -> tuple[str, dict]:
    end_ms = int((total_frames / fps) * 1000) if fps > 0 else 0
    payload = {
        "UrlLocal": BALL_ACTION_CONFIG.get("UrlLocal", "match"),
        "range": {
            "halves": BALL_ACTION_CONFIG.get("range", {}).get("halves", [1]),
            "start_ms": 0,
            "end_ms": end_ms,
            "start_frame": 0,
            "end_frame": int(total_frames),
        },
        "classes": BALL_ACTION_CONFIG.get("classes", []),
        "postprocess": BALL_ACTION_CONFIG.get("postprocess", {}),
        "rule": BALL_ACTION_CONFIG.get("rule"),
        "predictions": predictions,
    }

    path = os.path.join(OUTPUT_DIR, f"{job_id}_ball_action_predictions.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path, payload


def _write_ball_action_event_log(job_id: str, predictions: list[dict],
                                 error: str | None = None) -> str:
    path = os.path.join(OUTPUT_DIR, f"{job_id}_ball_action_events.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        if error:
            f.write(json.dumps({
                "type": "error",
                "error": str(error),
            }) + "\n")
            return path

        for index, prediction in enumerate(predictions, start=1):
            f.write(json.dumps({
                "type": "event",
                "index": index,
                "gameTime": prediction.get("gameTime"),
                "label": prediction.get("label"),
                "team": prediction.get("team"),
                "position": prediction.get("position"),
                "half": prediction.get("half"),
                "confidence": prediction.get("confidence"),
                "frame": prediction.get("frame"),
                "class_name": prediction.get("class_name"),
                "second": prediction.get("second"),
            }) + "\n")
            f.flush()
    return path


def _write_ball_action_error_predictions(job_id: str, error: str,
                                         total_frames: int = 0,
                                         fps: float = 0.0) -> tuple[str, dict]:
    end_ms = int((total_frames / fps) * 1000) if fps > 0 else 0
    payload = {
        "UrlLocal": BALL_ACTION_CONFIG.get("UrlLocal", "match"),
        "range": {
            "halves": BALL_ACTION_CONFIG.get("range", {}).get("halves", [1]),
            "start_ms": 0,
            "end_ms": end_ms,
            "start_frame": 0,
            "end_frame": int(total_frames),
        },
        "classes": BALL_ACTION_CONFIG.get("classes", []),
        "postprocess": BALL_ACTION_CONFIG.get("postprocess", {}),
        "rule": BALL_ACTION_CONFIG.get("rule"),
        "error": str(error),
        "predictions": [],
    }

    path = os.path.join(OUTPUT_DIR, f"{job_id}_ball_action_predictions.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path, payload


def _post_ai_job_statistics(job_id: str, job_data: dict, job_type: str, statistics: list[dict],
                            status: str = "Completed", error: str | None = None) -> tuple[bool, str | None]:
    """Persist finished AI stats into the ASP.NET Core database through the API."""
    auth_header = job_data.get("auth_header")
    if not auth_header:
        return False, "Missing authorization header, so the completed job could not be saved to history."
    if not statistics:
        return False, "No statistics were produced, so the completed job could not be saved to history."

    def guess_mime(path: str | None, key: str = "") -> str | None:
        value = (path or key or "").lower()
        if value.endswith(".csv"):
            return "text/csv"
        if value.endswith(".json"):
            return "application/json"
        if value.endswith(".mp4"):
            return "video/mp4"
        if value.endswith(".png"):
            return "image/png"
        return None

    result_files = []
    output_path = job_data.get("output_path")
    if output_path:
        result_files.append({
            "fileType": "video",
            "fileKey": "processed_video",
            "storagePath": output_path,
            "mimeType": guess_mime(output_path),
        })

    for key, path in (job_data.get("csv_files") or {}).items():
        result_files.append({
            "fileType": "csv",
            "fileKey": str(key),
            "storagePath": path,
            "mimeType": guess_mime(path, str(key)),
        })

    predictions_path = job_data.get("ball_action_predictions_path")
    if predictions_path:
        result_files.append({
            "fileType": "json",
            "fileKey": "ball_action_predictions",
            "storagePath": predictions_path,
            "mimeType": "application/json",
        })

    events_path = job_data.get("ball_action_events_path")
    if events_path:
        result_files.append({
            "fileType": "jsonl",
            "fileKey": "ball_action_events",
            "storagePath": events_path,
            "mimeType": "application/x-ndjson",
        })

    def parse_optional_int(value):
        try:
            if value is None or value == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def parse_optional_decimal(value):
        try:
            if value is None or value == "":
                return 0
            return float(value)
        except (TypeError, ValueError):
            return 0

    action_predictions = []
    for prediction in job_data.get("ball_action_predictions") or []:
        action_predictions.append({
            "gameTime": str(prediction.get("gameTime") or ""),
            "label": str(prediction.get("label") or ""),
            "team": prediction.get("team"),
            "position": prediction.get("position"),
            "half": parse_optional_int(prediction.get("half")),
            "confidence": parse_optional_decimal(prediction.get("confidence")),
            "frame": parse_optional_int(prediction.get("frame")),
            "className": prediction.get("class_name") or prediction.get("className"),
            "second": parse_optional_int(prediction.get("second")) or 0,
        })

    payload = {
        "jobId": job_id,
        "projectName": job_data.get("project_name") or job_data.get("title"),
        "originalFilename": job_data.get("original_filename") or f"{job_id}.mp4",
        "title": job_data.get("title") or job_data.get("original_filename") or f"AI job {job_id[:8]}",
        "inputPath": job_data.get("input_path") or "",
        "outputPath": job_data.get("output_path"),
        "csvDir": job_data.get("csv_dir"),
        "jobType": job_type,
        "status": status,
        "modelName": job_data.get("model_name"),
        "frameCount": job_data.get("processed_frames") or job_data.get("total_frames"),
        "objectCount": job_data.get("object_count"),
        "errorMessage": error,
        "uploadBatchId": job_data.get("upload_batch_id"),
        "uploadBatchTitle": job_data.get("upload_batch_title"),
        "uploadBatchVideoCount": job_data.get("upload_batch_video_count"),
        "uploadBatchIndex": job_data.get("upload_batch_index"),
        "playerName": job_data.get("player_name"),
        "statistics": statistics,
        "resultFiles": result_files,
        "actionPredictions": action_predictions,
    }

    request_data = json.dumps(payload).encode("utf-8")
    request_obj = urllib.request.Request(
        f"{DOTNET_API_BASE}/api/ai/job-statistics/ingest",
        data=request_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
        },
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=10) as response:
            response.read()
        print(f"[JOB {job_id[:8]}] Persisted AI statistics to ASP.NET API.", flush=True)
        return True, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        message = f"Failed to persist AI statistics ({exc.code}): {body}"
        print(f"[JOB {job_id[:8]}] {message}", flush=True)
        return False, message
    except Exception as exc:
        message = f"Failed to persist AI statistics: {exc}"
        print(f"[JOB {job_id[:8]}] {message}", flush=True)
        return False, message


def _post_heatmap_record(job_id: str, job_data: dict, target_type: str, target_id: str, image_path: str):
    """Persist generated heatmap metadata into the ASP.NET Core database."""
    auth_header = job_data.get("auth_header")
    if not auth_header:
        return

    payload = {
        "processingJobId": job_id,
        "targetType": target_type,
        "targetId": str(target_id),
        "imagePath": image_path,
    }
    request_data = json.dumps(payload).encode("utf-8")
    request_obj = urllib.request.Request(
        f"{DOTNET_API_BASE}/api/heatmaps/ingest",
        data=request_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
        },
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=10) as response:
            response.read()
        print(
            f"[JOB {job_id[:8]}] Persisted {target_type} heatmap metadata to ASP.NET API.",
            flush=True,
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        print(f"[JOB {job_id[:8]}] Failed to persist heatmap ({exc.code}): {body}", flush=True)
    except Exception as exc:
        print(f"[JOB {job_id[:8]}] Failed to persist heatmap: {exc}", flush=True)


def _get_persisted_csv_files(job_id: str, auth_header: str | None) -> dict:
    """Load saved CSV paths for a completed job from ASP.NET if Flask memory is gone."""
    if not auth_header:
        return {}

    query = urllib.parse.urlencode({
        "page": 1,
        "pageSize": 1,
        "processingJobId": job_id,
        "statType": "csv_paths",
    })
    request_obj = urllib.request.Request(
        f"{DOTNET_API_BASE}/api/job-statistics?{query}",
        method="GET",
        headers={"Authorization": auth_header},
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        items = payload.get("items") or []
        if not items:
            return {}
        stats_json = items[0].get("statsJson") or "{}"
        stats = json.loads(stats_json)
        return stats.get("csv_files") or {}
    except Exception as exc:
        print(f"[JOB {job_id[:8]}] Could not load persisted CSV paths: {exc}", flush=True)
        return {}


def _csv_files_for_job(job_id: str, job_data: dict | None = None) -> dict:
    csv_files = dict((job_data or {}).get("csv_files") or {})
    if csv_files:
        return csv_files

    csv_files = _get_persisted_csv_files(job_id, request.headers.get("Authorization"))
    if csv_files:
        return csv_files

    guessed_dir = os.path.join(OUTPUT_DIR, f"{job_id}_csv")
    guessed_player_positions = os.path.join(guessed_dir, "player_positions.csv")
    if os.path.exists(guessed_player_positions):
        return {"player_positions": guessed_player_positions}

    return {}


def _load_player_positions_csv(job_id: str, job_data: dict | None = None):
    import pandas as pd

    csv_files = _csv_files_for_job(job_id, job_data)
    player_positions_path = csv_files.get("player_positions")
    if not player_positions_path or not os.path.exists(player_positions_path):
        return None

    df = pd.read_csv(player_positions_path)
    required = {"tracker_id", "team_id", "x", "y"}
    if df.empty or not required.issubset(df.columns):
        return None

    df = df.copy()
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df["team_id"] = pd.to_numeric(df["team_id"], errors="coerce")
    df = df.dropna(subset=["tracker_id", "team_id", "x", "y"])
    return df


def _player_stats_from_positions(df) -> dict:
    stats = {}
    if df is None or df.empty:
        return stats

    for tracker_id, group in df.groupby("tracker_id"):
        tracker_value = str(tracker_id)
        numeric_id = int(float(tracker_value)) if tracker_value.replace(".", "", 1).isdigit() else tracker_value
        ordered = group.sort_values("frame") if "frame" in group.columns else group
        coords = ordered[["x", "y"]].to_numpy(dtype=float)
        distance_m = 0.0
        if len(coords) > 1:
            deltas = np.diff(coords, axis=0)
            distance_m = float(np.linalg.norm(deltas, axis=1).sum())
        team_id = int(group["team_id"].mode().iloc[0]) if not group["team_id"].mode().empty else 0
        stats[str(numeric_id)] = {
            "player_id": numeric_id,
            "team_id": team_id,
            "frame_count": int(len(group)),
            "distance_km": round(distance_m / 1000.0, 4),
        }

    return stats


def _draw_pitch(width: int = 1050, height: int = 680) -> np.ndarray:
    img = np.full((height, width, 3), (34, 92, 54), dtype=np.uint8)
    line = (235, 245, 240)
    cv2.rectangle(img, (20, 20), (width - 20, height - 20), line, 3)
    cv2.line(img, (width // 2, 20), (width // 2, height - 20), line, 2)
    cv2.circle(img, (width // 2, height // 2), 85, line, 2)
    cv2.rectangle(img, (20, height // 2 - 160), (150, height // 2 + 160), line, 2)
    cv2.rectangle(img, (width - 150, height // 2 - 160), (width - 20, height // 2 + 160), line, 2)
    cv2.rectangle(img, (20, height // 2 - 70), (70, height // 2 + 70), line, 2)
    cv2.rectangle(img, (width - 70, height // 2 - 70), (width - 20, height // 2 + 70), line, 2)
    return img


def _render_heatmap_from_positions(df, target_type: str, target_id: str) -> np.ndarray | None:
    import pandas as pd

    if df is None or df.empty:
        return None

    filtered = df.copy()
    if target_type == "player":
        filtered = filtered[filtered["tracker_id"].astype(str) == str(target_id)]
    elif target_type == "team":
        filtered = filtered[pd.to_numeric(filtered["team_id"], errors="coerce") == int(target_id)]

    if filtered.empty:
        return None

    width, height = 1050, 680
    pitch = _draw_pitch(width, height)
    xs = np.clip(filtered["x"].to_numpy(dtype=float), 0, 105)
    ys = np.clip(filtered["y"].to_numpy(dtype=float), 0, 68)
    px = (xs / 105.0 * (width - 40) + 20).astype(np.int32)
    py = (ys / 68.0 * (height - 40) + 20).astype(np.int32)

    heat = np.zeros((height, width), dtype=np.float32)
    for x, y in zip(px, py):
        cv2.circle(heat, (int(x), int(y)), 18, 1.0, -1)

    heat = cv2.GaussianBlur(heat, (0, 0), 22)
    if float(heat.max()) > 0:
        heat = heat / float(heat.max())

    colored = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_JET)
    mask = (heat > 0.05).astype(np.float32)[..., None]
    overlay = cv2.addWeighted(pitch, 0.68, colored, 0.58, 0)
    return (pitch * (1 - mask * 0.75) + overlay * (mask * 0.75)).astype(np.uint8)


def _encode_and_persist_heatmap(job_id: str, job_data: dict, target_type: str, target_id: str, img: np.ndarray):
    success, buf = cv2.imencode(".png", img)
    if not success:
        return None

    heatmap_path = os.path.join(
        OUTPUT_DIR,
        f"{job_id}_heatmap_{target_type}_{target_id}_{int(time.time() * 1000)}.png",
    )
    cv2.imwrite(heatmap_path, img)
    _post_heatmap_record(job_id, job_data, target_type, str(target_id), heatmap_path)
    return buf


# ── Background processing function ────────────────────────────────────────────
def _save_analyzer_csv_outputs(job_id: str, analyzer) -> tuple[str, dict, dict]:
    csv_dir = os.path.join(OUTPUT_DIR, f"{job_id}_csv")
    os.makedirs(csv_dir, exist_ok=True)

    csv_files = {}
    csv_errors = {}
    skip_full_event_csv = os.getenv("SKIP_FULL_EVENT_CSV", "").strip().lower() in {"1", "true", "yes", "on"}
    enable_full_event_csv = os.getenv("ENABLE_FULL_EVENT_CSV", "").strip().lower() in {"1", "true", "yes", "on"}
    write_full_event_csv = enable_full_event_csv and not skip_full_event_csv

    def save_one(key: str, filename: str, writer):
        path = os.path.join(csv_dir, filename)
        try:
            writer(path)
            csv_files[key] = path
        except Exception as exc:
            csv_errors[key] = str(exc)
            print(f"[JOB {job_id[:8]}] CSV export warning ({key}): {exc}", flush=True)

    save_one("detections", "detections.csv", analyzer.save_detections_csv)
    save_one("ball_positions", "ball_positions.csv", analyzer.save_ball_positions_csv)
    save_one("frame_states", "frame_states.csv", analyzer.save_frame_states_csv)
    save_one("player_positions", "player_positions.csv", analyzer.save_player_positions_csv)

    try:
        control_path = os.path.join(csv_dir, "possession_control.csv")
        gains_path = os.path.join(csv_dir, "possession_gains.csv")
        losses_path = os.path.join(csv_dir, "possession_losses.csv")
        control_df = getattr(analyzer, "possession_control_df", None)
        gains_df = getattr(analyzer, "possession_gains_df", None)
        losses_df = getattr(analyzer, "possession_losses_df", None)
        has_cached_possession = (
            control_df is not None
            and gains_df is not None
            and losses_df is not None
            and not getattr(control_df, "empty", True)
        )
        if has_cached_possession or write_full_event_csv:
            analyzer.save_possession_outputs(control_path, gains_path, losses_path)
            csv_files["possession_control"] = control_path
            csv_files["possession_gains"] = gains_path
            csv_files["possession_losses"] = losses_path
        else:
            csv_errors["possession"] = "Skipped full possession CSV export; pass totals use frame_states.csv and ball action fallbacks."
    except Exception as exc:
        csv_errors["possession"] = str(exc)
        print(f"[JOB {job_id[:8]}] CSV export warning (possession): {exc}", flush=True)

    try:
        events_path = os.path.join(csv_dir, "events.csv")
        dead_ball_path = os.path.join(csv_dir, "dead_ball_intervals.csv")
        transitions_path = os.path.join(csv_dir, "event_transitions.csv")
        events_df = getattr(analyzer, "events_df", None)
        has_cached_events = events_df is not None and not getattr(events_df, "empty", True)
        if has_cached_events or write_full_event_csv:
            if getattr(analyzer, "events_df", None) is None and hasattr(analyzer, "compute_events"):
                analyzer.compute_events()
            analyzer.save_event_outputs(events_path, dead_ball_path, transitions_path)
            csv_files["events"] = events_path
            csv_files["dead_ball_intervals"] = dead_ball_path
            csv_files["event_transitions"] = transitions_path
        else:
            csv_errors["events"] = "Skipped full event CSV export; pass totals use frame_states.csv and ball action fallbacks."
    except Exception as exc:
        csv_errors["events"] = str(exc)
        print(f"[JOB {job_id[:8]}] CSV export warning (events): {exc}", flush=True)

    return csv_dir, csv_files, csv_errors


def _calculate_csv_derived_stats(
    job_id: str,
    csv_dir: str,
    csv_files: dict,
    ball_action_predictions: list[dict] | None = None,
) -> tuple[dict, dict, dict]:
    import pandas as pd

    derived_files = {}
    derived_errors = {}
    stats = {
        "pass_totals": {},
        "positioning": {
            "teams": {},
            "players": [],
        },
    }

    def to_bool_series(series):
        return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})

    def clean_number(value, digits=3):
        if value is None or pd.isna(value):
            return None
        return round(float(value), digits)

    def team_key(team_id):
        return f"team_{int(team_id)}"

    def write_rows(key: str, filename: str, rows: list[dict], columns: list[str]):
        path = os.path.join(csv_dir, filename)
        pd.DataFrame(rows, columns=columns).to_csv(path, index=False)
        derived_files[key] = path

    pass_columns = [
        "team_id",
        "team_key",
        "total_passes",
        "successful_passes",
        "unsuccessful_passes",
        "completion_rate",
        "completion_pct",
        "crosses",
        "interceptions",
        "avg_distance_m",
        "total_distance_m",
    ]

    def pass_rows_from_passes(passes: "pd.DataFrame") -> list[dict]:
        passes = passes.copy()
        passes["team_id"] = pd.to_numeric(passes["team_id"], errors="coerce")
        passes = passes.dropna(subset=["team_id"])

        if passes.empty:
            return []

        if "successful" in passes.columns:
            passes["_successful"] = to_bool_series(passes["successful"])
        else:
            passes["_successful"] = True

        if "interception" in passes.columns:
            passes["_interception"] = to_bool_series(passes["interception"])
        else:
            passes["_interception"] = False

        if "distance" in passes.columns:
            passes["_distance"] = pd.to_numeric(passes["distance"], errors="coerce")
        elif {"start_x", "start_y", "end_x", "end_y"}.issubset(passes.columns):
            sx = pd.to_numeric(passes["start_x"], errors="coerce")
            sy = pd.to_numeric(passes["start_y"], errors="coerce")
            ex = pd.to_numeric(passes["end_x"], errors="coerce")
            ey = pd.to_numeric(passes["end_y"], errors="coerce")
            passes["_distance"] = np.hypot(ex - sx, ey - sy)
        else:
            passes["_distance"] = np.nan

        pass_rows = []
        for team_id, group in passes.groupby("team_id"):
            total = int(len(group))
            successful = int(group["_successful"].sum())
            interceptions = int(group["_interception"].sum())
            cross_count = int(group["event_name"].astype(str).str.lower().eq("cross").sum()) if "event_name" in group.columns else 0
            completion_rate = successful / total if total else 0.0
            avg_distance = group["_distance"].mean()
            total_distance = group["_distance"].sum(min_count=1)

            row = {
                "team_id": int(team_id),
                "team_key": team_key(team_id),
                "total_passes": total,
                "successful_passes": successful,
                "unsuccessful_passes": total - successful,
                "completion_rate": clean_number(completion_rate, 4),
                "completion_pct": clean_number(completion_rate * 100, 2),
                "crosses": cross_count,
                "interceptions": interceptions,
                "avg_distance_m": clean_number(avg_distance),
                "total_distance_m": clean_number(total_distance),
            }
            pass_rows.append(row)
            stats["pass_totals"][row["team_key"]] = row

        return pass_rows

    def fallback_pass_rows_from_frame_states() -> list[dict]:
        frame_states_path = csv_files.get("frame_states")
        if not frame_states_path or not os.path.exists(frame_states_path):
            return []

        frames = pd.read_csv(frame_states_path)
        required = {"frame", "ball_control", "controller_id", "controller_team"}
        if frames.empty or not required.issubset(frames.columns):
            return []

        frames = frames.sort_values("frame").copy()
        frames["frame"] = pd.to_numeric(frames["frame"], errors="coerce")
        frames["controller_team"] = pd.to_numeric(frames["controller_team"], errors="coerce")
        frames = frames[
            frames["ball_control"].astype(str).str.lower().eq("possession")
            & frames["frame"].notna()
            & frames["controller_team"].notna()
            & frames["controller_id"].notna()
        ]

        if frames.empty:
            return []

        frames["_controller_id"] = frames["controller_id"].astype(str)
        changed = (
            frames["_controller_id"].ne(frames["_controller_id"].shift())
            | frames["controller_team"].ne(frames["controller_team"].shift())
            | frames["frame"].sub(frames["frame"].shift()).gt(15)
        )
        frames["_segment"] = changed.cumsum()

        segments = []
        for _, group in frames.groupby("_segment"):
            first = group.iloc[0]
            last = group.iloc[-1]
            segments.append({
                "team_id": int(first["controller_team"]),
                "controller_id": str(first["_controller_id"]),
                "start_frame": float(first["frame"]),
                "end_frame": float(last["frame"]),
                "start_x": pd.to_numeric(first.get("ball_x_smooth", first.get("ball_x", np.nan)), errors="coerce"),
                "start_y": pd.to_numeric(first.get("ball_y_smooth", first.get("ball_y", np.nan)), errors="coerce"),
                "end_x": pd.to_numeric(last.get("ball_x_smooth", last.get("ball_x", np.nan)), errors="coerce"),
                "end_y": pd.to_numeric(last.get("ball_y_smooth", last.get("ball_y", np.nan)), errors="coerce"),
            })

        fallback_rows = []
        for previous, current in zip(segments, segments[1:]):
            if previous["team_id"] != current["team_id"]:
                continue
            if previous["controller_id"] == current["controller_id"]:
                continue

            fallback_rows.append({
                "team_id": previous["team_id"],
                "event_name": "pass",
                "successful": True,
                "interception": False,
                "start_x": previous["end_x"],
                "start_y": previous["end_y"],
                "end_x": current["start_x"],
                "end_y": current["start_y"],
            })

        if fallback_rows:
            print(
                f"[JOB {job_id[:8]}] Generated pass totals from frame_states fallback ({len(fallback_rows)} passes).",
                flush=True,
            )

        return pass_rows_from_passes(pd.DataFrame(fallback_rows))

    def pass_rows_from_ball_action_predictions() -> list[dict]:
        predictions = ball_action_predictions or []
        pass_events = []

        for prediction in predictions:
            label = str(prediction.get("label", "")).strip().upper()
            if label not in {"PASS", "HIGH PASS"}:
                continue

            team_name = str(prediction.get("team", "")).strip().lower()
            if team_name == "left":
                team_id = 0
            elif team_name == "right":
                team_id = 1
            else:
                continue

            pass_events.append({
                "team_id": team_id,
                "event_name": "long_pass" if label == "HIGH PASS" else "pass",
                "successful": True,
                "interception": False,
            })

        if pass_events:
            print(
                f"[JOB {job_id[:8]}] Generated pass totals from ball action predictions "
                f"({len(pass_events)} passes).",
                flush=True,
            )

        return pass_rows_from_passes(pd.DataFrame(pass_events))

    def zero_pass_rows() -> list[dict]:
        team_ids = set()
        player_positions_path = csv_files.get("player_positions")
        if player_positions_path and os.path.exists(player_positions_path):
            try:
                players = pd.read_csv(player_positions_path, usecols=lambda col: col == "team_id")
                if "team_id" in players.columns:
                    teams = pd.to_numeric(players["team_id"], errors="coerce").dropna().unique()
                    team_ids.update(int(team_id) for team_id in teams)
            except Exception:
                pass

        if not team_ids:
            team_ids.update([0, 1])

        rows = []
        for team_id in sorted(team_ids):
            row = {
                "team_id": int(team_id),
                "team_key": team_key(team_id),
                "total_passes": 0,
                "successful_passes": 0,
                "unsuccessful_passes": 0,
                "completion_rate": 0,
                "completion_pct": 0,
                "crosses": 0,
                "interceptions": 0,
                "avg_distance_m": None,
                "total_distance_m": None,
            }
            rows.append(row)
            stats["pass_totals"][row["team_key"]] = row

        return rows

    try:
        events_path = csv_files.get("events")
        pass_rows = []
        if events_path and os.path.exists(events_path):
            events = pd.read_csv(events_path)
            if not events.empty and "team_id" in events.columns:
                event_names = events.get("event_name", pd.Series("", index=events.index)).astype(str).str.lower()
                pass_mask = event_names.isin({"pass", "cross", "long_pass"})

                if "is_pass" in events.columns:
                    pass_mask = pass_mask | to_bool_series(events["is_pass"])

                passes = events[pass_mask].copy()
                if not passes.empty:
                    pass_rows = pass_rows_from_passes(passes)

        if not pass_rows:
            pass_rows = fallback_pass_rows_from_frame_states()

        if not pass_rows:
            pass_rows = pass_rows_from_ball_action_predictions()

        if not pass_rows:
            pass_rows = zero_pass_rows()
            derived_errors["passes"] = "No pass events were detected; showing zero pass totals."

        write_rows("team_pass_totals", "team_pass_totals.csv", pass_rows, pass_columns)
    except Exception as exc:
        derived_errors["passes"] = str(exc)
        print(f"[JOB {job_id[:8]}] Derived stats warning (passes): {exc}", flush=True)

    team_positioning_columns = [
        "team_id",
        "team_key",
        "avg_x",
        "avg_y",
        "avg_width_m",
        "avg_depth_m",
        "avg_compactness_m",
        "avg_players_visible",
        "samples",
        "first_frame",
        "last_frame",
    ]
    player_positioning_columns = [
        "tracker_id",
        "team_id",
        "team_key",
        "avg_x",
        "avg_y",
        "min_x",
        "max_x",
        "min_y",
        "max_y",
        "samples",
        "first_frame",
        "last_frame",
        "is_goalkeeper",
    ]

    try:
        positions_path = csv_files.get("player_positions")
        if positions_path and os.path.exists(positions_path):
            positions = pd.read_csv(positions_path)
            required_cols = {"frame", "tracker_id", "team_id", "x", "y"}
            if not positions.empty and required_cols.issubset(positions.columns):
                positions["frame"] = pd.to_numeric(positions["frame"], errors="coerce")
                positions["team_id"] = pd.to_numeric(positions["team_id"], errors="coerce")
                positions["x"] = pd.to_numeric(positions["x"], errors="coerce")
                positions["y"] = pd.to_numeric(positions["y"], errors="coerce")
                positions = positions.dropna(subset=["frame", "team_id", "x", "y"])
                positions["team_id"] = positions["team_id"].astype(int)

                if "is_goalkeeper" in positions.columns:
                    positions["_is_goalkeeper"] = to_bool_series(positions["is_goalkeeper"])
                else:
                    positions["_is_goalkeeper"] = positions["tracker_id"].astype(str).str.startswith("GK_")

                team_rows = []
                for team_id, group in positions.groupby("team_id"):
                    shape_group = group[~group["_is_goalkeeper"]]
                    if shape_group.empty:
                        shape_group = group

                    frame_rows = []
                    for frame, frame_group in shape_group.groupby("frame"):
                        width = frame_group["y"].max() - frame_group["y"].min()
                        depth = frame_group["x"].max() - frame_group["x"].min()
                        centroid_x = frame_group["x"].mean()
                        centroid_y = frame_group["y"].mean()
                        compactness = np.hypot(
                            frame_group["x"] - centroid_x,
                            frame_group["y"] - centroid_y,
                        ).mean()
                        frame_rows.append({
                            "width": width,
                            "depth": depth,
                            "compactness": compactness,
                            "players_visible": frame_group["tracker_id"].nunique(),
                        })

                    frame_metrics = pd.DataFrame(frame_rows)
                    row = {
                        "team_id": int(team_id),
                        "team_key": team_key(team_id),
                        "avg_x": clean_number(shape_group["x"].mean()),
                        "avg_y": clean_number(shape_group["y"].mean()),
                        "avg_width_m": clean_number(frame_metrics["width"].mean() if not frame_metrics.empty else None),
                        "avg_depth_m": clean_number(frame_metrics["depth"].mean() if not frame_metrics.empty else None),
                        "avg_compactness_m": clean_number(frame_metrics["compactness"].mean() if not frame_metrics.empty else None),
                        "avg_players_visible": clean_number(frame_metrics["players_visible"].mean() if not frame_metrics.empty else None, 2),
                        "samples": int(len(shape_group)),
                        "first_frame": int(shape_group["frame"].min()),
                        "last_frame": int(shape_group["frame"].max()),
                    }
                    team_rows.append(row)
                    stats["positioning"]["teams"][row["team_key"]] = row

                player_rows = []
                for tracker_id, group in positions.groupby("tracker_id"):
                    team_id = int(group["team_id"].mode().iloc[0]) if not group["team_id"].mode().empty else int(group["team_id"].iloc[0])
                    is_goalkeeper = bool(group["_is_goalkeeper"].mode().iloc[0]) if not group["_is_goalkeeper"].mode().empty else False
                    row = {
                        "tracker_id": str(tracker_id),
                        "team_id": team_id,
                        "team_key": team_key(team_id),
                        "avg_x": clean_number(group["x"].mean()),
                        "avg_y": clean_number(group["y"].mean()),
                        "min_x": clean_number(group["x"].min()),
                        "max_x": clean_number(group["x"].max()),
                        "min_y": clean_number(group["y"].min()),
                        "max_y": clean_number(group["y"].max()),
                        "samples": int(len(group)),
                        "first_frame": int(group["frame"].min()),
                        "last_frame": int(group["frame"].max()),
                        "is_goalkeeper": is_goalkeeper,
                    }
                    player_rows.append(row)

                player_rows.sort(key=lambda row: (row["team_id"], row["is_goalkeeper"], row["tracker_id"]))
                stats["positioning"]["players"] = player_rows

                write_rows("team_positioning", "team_positioning.csv", team_rows, team_positioning_columns)
                write_rows("player_positioning", "player_positioning.csv", player_rows, player_positioning_columns)
            else:
                write_rows("team_positioning", "team_positioning.csv", [], team_positioning_columns)
                write_rows("player_positioning", "player_positioning.csv", [], player_positioning_columns)
        else:
            derived_errors["positioning"] = "player_positions.csv was not generated."
    except Exception as exc:
        derived_errors["positioning"] = str(exc)
        print(f"[JOB {job_id[:8]}] Derived stats warning (positioning): {exc}", flush=True)

    return stats, derived_files, derived_errors


def _try_finalize_from_fast_csv_outputs(job_id: str, job: dict) -> bool:
    """Recover jobs that wrote the output video and fast CSVs but stalled in optional exports."""
    output_path = job.get("output_path")
    if not output_path or not os.path.exists(output_path):
        return False

    csv_dir = job.get("csv_dir") or os.path.join(OUTPUT_DIR, f"{job_id}_csv")
    fast_csv_files = {
        "detections": os.path.join(csv_dir, "detections.csv"),
        "ball_positions": os.path.join(csv_dir, "ball_positions.csv"),
        "frame_states": os.path.join(csv_dir, "frame_states.csv"),
        "player_positions": os.path.join(csv_dir, "player_positions.csv"),
    }
    if not all(os.path.exists(path) for path in fast_csv_files.values()):
        return False

    try:
        csv_derived_stats, derived_csv_files, derived_csv_errors = _calculate_csv_derived_stats(
            job_id,
            csv_dir,
            dict(fast_csv_files),
            job.get("ball_action_predictions", []),
        )
    except Exception as exc:
        print(f"[JOB {job_id[:8]}] Finalization recovery warning: {exc}", flush=True)
        return False

    csv_files = dict(fast_csv_files)
    csv_files.update(derived_csv_files)
    csv_errors = dict(job.get("csv_errors", {}))
    csv_errors.update(derived_csv_errors)
    csv_errors.setdefault(
        "full_exports",
        "Skipped slow possession/event exports while recovering final job status.",
    )

    job.update({
        "status": "done",
        "stage": "done",
        "progress": 100,
        "csv_dir": csv_dir,
        "csv_files": csv_files,
        "csv_errors": csv_errors,
        "csv_derived_stats": csv_derived_stats,
        "video_url": f"/video/{job_id}" if job.get("return_video", True) else None,
    })
    print(f"[JOB {job_id[:8]}] Recovered final status from fast CSV outputs.", flush=True)
    return True


def _process_ball_action_video(job_id: str, video_path: str):
    """Runs only the match event spotting model, without FootballAnalyzer."""

    total_frames = 0
    fps = 0.0
    ball_action_json_path = None
    ball_action_payload = None
    ball_action_events_path = None

    def _update(status=None, progress=None, stage=None,
                processed_frames=None, total_frames=None, error=None):
        with jobs_lock:
            j = jobs[job_id]
            if status is not None:           j["status"]           = status
            if progress is not None:         j["progress"]         = progress
            if stage is not None:            j["stage"]            = stage
            if processed_frames is not None: j["processed_frames"] = processed_frames
            if total_frames is not None:     j["total_frames"]     = total_frames
            if error is not None:            j["error"]            = error

    try:
        if BALL_ACTION_MODEL is None:
            raise RuntimeError(
                "Action spotting model is not loaded. "
                f"{BALL_ACTION_MODEL_ERROR or 'Check ball_model_FULL_OBJECT.pt.'}"
            )

        print(f"[BALL {job_id[:8]}] Preparing video for match event spotting ...", flush=True)
        _update(status="preparing_video", stage="preparing_video", progress=3)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        print(
            f"[BALL {job_id[:8]}] Video: {width}x{height} @ {fps:.1f}fps, "
            f"{total_frames} frames",
            flush=True,
        )
        _update(
            status="spotting_events",
            stage="spotting_events",
            progress=5,
            processed_frames=0,
            total_frames=total_frames,
        )

        last_reported_pct = {"value": 4}

        def _on_spotting_progress(processed: int, total: int):
            total = max(1, int(total))
            pct = 5 + int(88 * min(processed, total) / total)
            if pct > last_reported_pct["value"]:
                last_reported_pct["value"] = pct
                _update(
                    progress=pct,
                    processed_frames=min(int(processed), total),
                    total_frames=total,
                )
                if pct % 5 == 0 or processed >= total:
                    print(
                        f"[BALL {job_id[:8]}] Event spotting "
                        f"{min(int(processed), total)}/{total} frames ({pct}%)",
                        flush=True,
                    )

        ball_action_score_points = _predict_ball_action_video_score_points(
            video_path,
            total_frames,
            progress_callback=_on_spotting_progress,
        )

        _update(status="post_processing", stage="post_processing", progress=94)
        ball_action_predictions = _build_ball_action_predictions(ball_action_score_points, fps)
        ball_action_events_path = _write_ball_action_event_log(job_id, ball_action_predictions)
        with jobs_lock:
            jobs[job_id]["ball_action_events_path"] = ball_action_events_path
            jobs[job_id]["ball_action_predictions"] = ball_action_predictions

        ball_action_stats = _stats_from_ball_action_predictions(ball_action_predictions)
        ball_action_json_path, ball_action_payload = _write_ball_action_predictions(
            job_id,
            ball_action_predictions,
            total_frames,
            fps,
        )

        print(
            f"[BALL {job_id[:8]}] Ball action predictions: "
            f"{len(ball_action_predictions)} after same-second filtering",
            flush=True,
        )
        print(f"[BALL {job_id[:8]}] Ball action stats: {json.dumps(ball_action_stats)}", flush=True)

        with jobs_lock:
            jobs[job_id].update({
                "status": "persisting_results",
                "stage": "persisting_results",
                "progress": 99,
                "processed_frames": total_frames,
                "total_frames": total_frames,
                "output_path": None,
                "analyzer": None,
                "player_stats": {},
                "ball_action_stats": ball_action_stats,
                "ball_action_predictions": ball_action_predictions,
                "ball_action_predictions_path": ball_action_json_path,
                "ball_action_predictions_payload": ball_action_payload,
                "ball_action_events_path": ball_action_events_path,
                "csv_dir": None,
                "csv_files": {},
                "csv_errors": {},
                "csv_derived_stats": {},
                "video_url": None,
                "model_name": "ball_model_FULL_OBJECT.pt",
            })
            job_snapshot = dict(jobs[job_id])

        stat_rows = [
            {
                "moduleName": "ball_action_model",
                "modelName": "ball_model_FULL_OBJECT.pt",
                "statType": "ball_action_stats",
                "statsJson": json.dumps(ball_action_stats),
            },
            {
                "moduleName": "ball_action_model",
                "modelName": "ball_model_FULL_OBJECT.pt",
                "statType": "ball_action_predictions",
                "statsJson": json.dumps(ball_action_payload or {}),
            },
        ]

        persisted, persist_error = _post_ai_job_statistics(
            job_id=job_id,
            job_data=job_snapshot,
            job_type="BallActionAnalysis",
            statistics=stat_rows,
        )

        if not persisted:
            message = (
                "Analysis finished, but the result was not saved to history. "
                f"{persist_error or 'Check the ASP.NET API and authentication token.'}"
            )
            with jobs_lock:
                jobs[job_id].update({
                    "status": "error",
                    "stage": "persistence_failed",
                    "progress": 99,
                    "error": message,
                })
            print(f"[BALL {job_id[:8]}] {message}", flush=True)
            return

        with jobs_lock:
            jobs[job_id].update({
                "status": "done",
                "stage": "done",
                "progress": 100,
            })

        print(f"[BALL {job_id[:8]}] Done - {total_frames} frames processed.", flush=True)

    except Exception as exc:
        import traceback
        traceback.print_exc()
        try:
            if ball_action_events_path is None:
                ball_action_events_path = _write_ball_action_event_log(
                    job_id,
                    [],
                    error=str(exc),
                )
            if ball_action_json_path is None:
                ball_action_json_path, ball_action_payload = _write_ball_action_error_predictions(
                    job_id,
                    str(exc),
                    total_frames,
                    fps,
                )
            with jobs_lock:
                jobs[job_id].update({
                    "ball_action_predictions_path": ball_action_json_path,
                    "ball_action_predictions_payload": ball_action_payload,
                    "ball_action_events_path": ball_action_events_path,
                    "ball_action_predictions": [],
                })
        except Exception as write_exc:
            print(
                f"[BALL {job_id[:8]}] Failed to write error prediction JSON: {write_exc}",
                flush=True,
            )
        _update(status="error", stage="error", error=str(exc))
        print(f"[BALL {job_id[:8]}] ERROR: {exc}", flush=True)
    finally:
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except OSError:
            pass


def _process_video(job_id: str, video_path: str, run_ball_model: bool = False, return_video: bool = True):
    """Runs in a daemon thread. Updates jobs[job_id] as it progresses."""

    def _update(status=None, progress=None, stage=None,
                processed_frames=None, total_frames=None, error=None):
        with jobs_lock:
            j = jobs[job_id]
            if status is not None:           j["status"]           = status
            if progress is not None:         j["progress"]         = progress
            if stage is not None:            j["stage"]            = stage
            if processed_frames is not None: j["processed_frames"] = processed_frames
            if total_frames is not None:     j["total_frames"]     = total_frames
            if error is not None:            j["error"]            = error

    def _heartbeat(stage_label: str, start_pct: int, end_pct: int,
                   interval: float, stop_event: threading.Event):
        """Slowly ticks progress from start_pct → end_pct while a long task runs."""
        pct = start_pct
        while not stop_event.is_set():
            time.sleep(interval)
            if pct < end_pct:
                pct += 1
                _update(progress=pct)
                print(f"[JOB {job_id[:8]}] {stage_label} … {pct}%", flush=True)

    try:
        if PLAYER_MODEL is None or FIELD_MODEL is None:
            raise RuntimeError("Models failed to load at startup. Check console.")
        if run_ball_model and BALL_ACTION_MODEL is None:
            raise RuntimeError(
                "Action spotting model is not loaded. "
                f"{BALL_ACTION_MODEL_ERROR or 'Check ball_model_FULL_OBJECT.pt.'}"
            )

        # ── 1. Open video & read metadata ─────────────────────────────────────
        print(f"[JOB {job_id[:8]}] Preparing video …", flush=True)
        _update(status="preparing_video", stage="preparing_video", progress=3)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps          = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        print(f"[JOB {job_id[:8]}] Video: {width}x{height} @ {fps:.1f}fps, {total_frames} frames", flush=True)
        _update(total_frames=total_frames, progress=5)

        # ── 2. Build the analyzer — TeamClassifier may download a model here ──
        print(f"[JOB {job_id[:8]}] Initialising FootballAnalyzer (may download DINOv2 model on first run) …", flush=True)
        _update(status="preparing_video", stage="preparing_video", progress=6)

        stop_init = threading.Event()
        init_hb   = threading.Thread(target=_heartbeat,
                                     args=("Loading classifier model", 6, 14, 3.0, stop_init),
                                     daemon=True)
        init_hb.start()

        analyzer = FootballAnalyzer(model=PLAYER_MODEL, fps=fps, device=DEVICE)
        analyzer.set_field_model(FIELD_MODEL)

        stop_init.set()
        init_hb.join(timeout=1)
        print(f"[JOB {job_id[:8]}] FootballAnalyzer ready.", flush=True)

        # ── 3. Fit team classifier (module method) ────────────────────────────
        print(f"[JOB {job_id[:8]}] Training team classifier (sampling frames) …", flush=True)
        _update(status="training_team_classifier",
                stage="training_team_classifier", progress=15)

        stop_fit = threading.Event()
        fit_hb   = threading.Thread(target=_heartbeat,
                                    args=("Training team classifier", 15, 22, 2.5, stop_fit),
                                    daemon=True)
        fit_hb.start()

        analyzer.fit_team_classifier(video_path)

        stop_fit.set()
        fit_hb.join(timeout=1)
        print(f"[JOB {job_id[:8]}] Team classifier ready.", flush=True)
        _update(progress=23)

        # ── 4. Process frames through the module ──────────────────────────────
        print(f"[JOB {job_id[:8]}] Processing frames …", flush=True)
        _update(status="processing_frames", stage="processing_frames", progress=25)

        output_path     = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
        preview_path    = os.path.join(OUTPUT_DIR, f"{job_id}_latest.jpg")

        # ── Frames folder: outputs/{job_id}_frames/ ───────────────────────────
        frames_dir = os.path.join(OUTPUT_DIR, f"{job_id}_frames")
        os.makedirs(frames_dir, exist_ok=True)
        print(f"[JOB {job_id[:8]}] Saving frames to: {frames_dir}", flush=True)

        fourcc, codec_name = _get_fourcc()
        print(f"[JOB {job_id[:8]}] Using video codec: {codec_name}", flush=True)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not out.isOpened():
            raise RuntimeError(f"VideoWriter failed to open with codec '{codec_name}'. Check OpenCV build.")

        # Live preview update interval (~1 per second of video)
        PREVIEW_EVERY = max(1, int(fps))

        cap = cv2.VideoCapture(video_path)
        frame_idx = 0
        log_every = max(1, total_frames // 20)

        # ── Ball action stats accumulators (Team 1 / Team 2) ──────────────────
        # Tracked classes from ball_model_FULL_OBJECT.pt
        ball_action_stats = _empty_ball_action_stats()
        ball_action_score_points = []
        ball_action_predictions = []
        ball_action_json_path = None
        ball_action_payload = None
        _ball_cooldown = {}

        # Store paths in job dict
        with jobs_lock:
            jobs[job_id]["preview_path"] = preview_path
            jobs[job_id]["frames_dir"]   = frames_dir

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            annotated = analyzer.process_frame(frame, use_tiling=False)

            # ── Run Ball Action model on this frame ───────────────────────────
            if False and BALL_ACTION_MODEL is not None and run_ball_model:
                ball_clip_frames.append(frame.copy())
                try:
                    if len(ball_clip_frames) == ball_clip_frames.maxlen and frame_idx % ball_action_stride == 0:
                        center_frame = max(0, frame_idx - (ball_clip_frames.maxlen // 2))
                        scores = _predict_ball_action_scores(list(ball_clip_frames))
                        if scores is not None:
                            ball_action_score_points.append({
                                "frame": center_frame,
                                "scores": scores,
                            })
                except Exception as ball_err:
                    if frame_idx <= 5:
                        print(f"[JOB {job_id[:8]}] Ball model warning: {ball_err}", flush=True)

            if False and BALL_ACTION_MODEL is not None and run_ball_model:
                try:
                    ball_results = BALL_ACTION_MODEL(frame, verbose=False)
                    for r in ball_results:
                        for box in r.boxes:
                            cls_id = int(box.cls[0])
                            conf = float(box.conf[0])
                            cls_name = BALL_ACTION_CLASSES.get(cls_id, "").lower().strip()

                            # Normalize class name to our expected keys
                            normalised = cls_name.replace(" ", "_").replace("-", "_")
                            if normalised not in _ball_cooldown:
                                # Try partial matching
                                for known in BALL_ACTION_NAMES:
                                    if known in normalised or normalised in known:
                                        normalised = known
                                        break

                            if normalised in _ball_cooldown and conf >= 0.35:
                                if _ball_cooldown[normalised] <= 0:
                                    # Attribute to team based on nearest tracked player
                                    bx = float((box.xyxy[0][0] + box.xyxy[0][2]) / 2)
                                    by = float((box.xyxy[0][1] + box.xyxy[0][3]) / 2)
                                    team_key = _attribute_to_team(
                                        bx, by, analyzer, frame_idx
                                    )
                                    ball_action_stats[team_key][normalised] += 1
                                    _ball_cooldown[normalised] = COOLDOWN_FRAMES
                                    print(f"[JOB {job_id[:8]}] Ball action: {normalised} → {team_key} (conf={conf:.2f})", flush=True)
                except Exception as ball_err:
                    # Don't let ball model errors crash the main pipeline
                    if frame_idx <= 5:
                        print(f"[JOB {job_id[:8]}] Ball model warning: {ball_err}", flush=True)

            # Tick cooldowns
            for k in _ball_cooldown:
                if _ball_cooldown[k] > 0:
                    _ball_cooldown[k] -= 1

            out.write(annotated)
            frame_idx += 1

            # ── Save every frame as a JPEG ────────────────────────────────────
            frame_filename = os.path.join(frames_dir, f"frame_{frame_idx:06d}.jpg")
            cv2.imwrite(frame_filename, annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])

            # ── Also update the single live-preview file ──────────────────────
            if frame_idx % PREVIEW_EVERY == 0:
                cv2.imwrite(preview_path, annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])

            # Update progress (25 → 92 range)
            if total_frames > 0:
                pct = 25 + int(67 * frame_idx / total_frames)
            else:
                pct = min(92, 25 + frame_idx)

            _update(progress=pct, processed_frames=frame_idx)

            if frame_idx % log_every == 0:
                print(f"[JOB {job_id[:8]}] Frame {frame_idx}/{total_frames} ({pct}%) → {frame_filename}", flush=True)

        cap.release()
        out.release()
        if run_ball_model:
            _update(status="spotting_events", stage="spotting_events", progress=92)
            ball_action_score_points = _predict_ball_action_video_score_points(video_path, total_frames)
            ball_action_predictions = _build_ball_action_predictions(ball_action_score_points, fps)
            ball_action_stats = _stats_from_ball_action_predictions(ball_action_predictions)
            ball_action_json_path, ball_action_payload = _write_ball_action_predictions(
                job_id,
                ball_action_predictions,
                total_frames,
                fps,
            )
            print(
                f"[JOB {job_id[:8]}] Ball action predictions: "
                f"{len(ball_action_predictions)} after same-second filtering",
                flush=True,
            )
        print(f"[JOB {job_id[:8]}] All frames saved to: {frames_dir}", flush=True)
        print(f"[JOB {job_id[:8]}] Ball action stats: {json.dumps(ball_action_stats)}", flush=True)

        # ── 5. Re-encode mp4v → H.264 for browser compatibility ──────────────
        _update(status="encoding", stage="encoding", progress=93)
        print(f"[JOB {job_id[:8]}] Re-encoding to H.264 for browser playback …", flush=True)

        h264_path = output_path.replace(".mp4", "_h264.mp4")
        if _reencode_h264(output_path, h264_path):
            os.remove(output_path)           # remove the raw mp4v file
            os.rename(h264_path, output_path)  # replace with H.264 version
            print(f"[JOB {job_id[:8]}] Re-encode complete → {output_path}", flush=True)
        else:
            print(f"[JOB {job_id[:8]}] Re-encode skipped — serving raw mp4v (may not play in browser)", flush=True)

        # ── 6. Build player stats from the module's internal data ─────────────
        _update(progress=97)

        player_stats = {}
        for tracker_id, coords_deque in analyzer.heatmap_coordinates.items():
            coords = list(coords_deque)
            team_history = list(analyzer.player_team_history.get(tracker_id, []))
            stable_team = max(set(team_history), key=team_history.count) if team_history else 0

            distance_m = 0.0
            for i in range(1, len(coords)):
                dx = coords[i][0] - coords[i-1][0]
                dy = coords[i][1] - coords[i-1][1]
                distance_m += float(np.hypot(dx, dy))
            distance_km = distance_m / 1000.0

            player_stats[str(tracker_id)] = {
                "player_id":   int(tracker_id),
                "team_id":     int(stable_team),
                "frame_count": len(coords),
                "distance_km": round(distance_km, 4),
            }

        # ── 6. Mark done ──────────────────────────────────────────────────────
        _update(status="saving_csv_outputs", stage="saving_csv_outputs", progress=98)
        csv_dir, csv_files, csv_errors = _save_analyzer_csv_outputs(job_id, analyzer)
        csv_derived_stats, derived_csv_files, derived_csv_errors = _calculate_csv_derived_stats(
            job_id,
            csv_dir,
            csv_files,
            ball_action_predictions,
        )
        csv_files.update(derived_csv_files)
        csv_errors.update(derived_csv_errors)
        print(f"[JOB {job_id[:8]}] CSV outputs saved to: {csv_dir}", flush=True)

        with jobs_lock:
            jobs[job_id].update({
                "status":          "persisting_results",
                "stage":           "persisting_results",
                "progress":        99,
                "processed_frames": frame_idx,
                "total_frames":     total_frames,
                "output_path":     output_path,
                "analyzer":        analyzer,   # keep alive for heatmaps
                "player_stats":    player_stats,
                "ball_action_stats": ball_action_stats,
                "ball_action_predictions": ball_action_predictions,
                "ball_action_predictions_path": ball_action_json_path,
                "ball_action_predictions_payload": ball_action_payload,
                "csv_dir":         csv_dir,
                "csv_files":       csv_files,
                "csv_errors":      csv_errors,
                "csv_derived_stats": csv_derived_stats,
                "video_url":       f"/video/{job_id}" if return_video else None,
                "model_name":      "best.pt + ball_model_FULL_OBJECT.pt" if run_ball_model and return_video else ("ball_model_FULL_OBJECT.pt" if run_ball_model else "best.pt"),
            })
            job_snapshot = dict(jobs[job_id])

        stat_rows = [
            {
                "moduleName": "football_analyzer",
                "modelName": "best.pt",
                "statType": "player_stats",
                "statsJson": json.dumps(player_stats),
            }
        ]

        stat_rows.append({
            "moduleName": "csv_export",
            "modelName": job_snapshot.get("model_name"),
            "statType": "csv_paths",
            "statsJson": json.dumps({
                "csv_dir": csv_dir,
                "csv_files": csv_files,
                "csv_errors": csv_errors,
            }),
        })

        stat_rows.append({
            "moduleName": "csv_analysis",
            "modelName": job_snapshot.get("model_name"),
            "statType": "passes_and_positioning",
            "statsJson": json.dumps(csv_derived_stats),
        })

        if run_ball_model:
            stat_rows.append({
                "moduleName": "ball_action_model",
                "modelName": "ball_model_FULL_OBJECT.pt",
                "statType": "ball_action_stats",
                "statsJson": json.dumps(ball_action_stats),
            })
            stat_rows.append({
                "moduleName": "ball_action_model",
                "modelName": "ball_model_FULL_OBJECT.pt",
                "statType": "ball_action_predictions",
                "statsJson": json.dumps(ball_action_payload or {}),
            })

        persisted, persist_error = _post_ai_job_statistics(
            job_id=job_id,
            job_data=job_snapshot,
            job_type="BallActionAnalysis" if run_ball_model and not return_video else "VideoDetection",
            statistics=stat_rows,
        )

        if not persisted:
            message = (
                "Analysis finished, but the result was not saved to history. "
                f"{persist_error or 'Check the ASP.NET API and authentication token.'}"
            )
            with jobs_lock:
                jobs[job_id].update({
                    "status":   "error",
                    "stage":    "persistence_failed",
                    "progress": 99,
                    "error":    message,
                })
            print(f"[JOB {job_id[:8]}] {message}", flush=True)
            return

        with jobs_lock:
            jobs[job_id].update({
                "status":   "done",
                "stage":    "done",
                "progress": 100,
            })

        print(f"[JOB {job_id[:8]}] Done — {frame_idx} frames processed.")

    except Exception as exc:
        import traceback
        traceback.print_exc()
        _update(status="error", stage="error", error=str(exc))
        print(f"[JOB {job_id[:8]}] ERROR: {exc}")
    finally:
        # Clean up uploaded source file
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "device": DEVICE,
                    "models_loaded": PLAYER_MODEL is not None,
                    "action_model_loaded": ACTION_MODEL is not None,
                    "ball_action_model_loaded": BALL_ACTION_MODEL is not None,
                    "ball_action_model_error": BALL_ACTION_MODEL_ERROR})


# ── Verify a job still exists (used by frontend on page load) ─────────────────
@app.route("/job_exists/<job_id>", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def job_exists(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        _refresh_job_auth_from_request(job)
        exists = job is not None
    return jsonify({"exists": exists})


# ── Upload video & start a job ─────────────────────────────────────────────────
@app.route("/detect_video", methods=["POST"])
@require_auth(*AUTHENTICATED_ROLES)
def detect_video():
    if "video" not in request.files:
        return jsonify({"error": "No video file in request (field name: 'video')."}), 400

    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    job_id = str(uuid.uuid4())
    upload_path = os.path.join(OUTPUT_DIR, f"{job_id}_input{os.path.splitext(video_file.filename)[1]}")
    video_file.save(upload_path)

    with jobs_lock:
        jobs[job_id] = {
            "status":           "queued",
            "stage":            "queued",
            "progress":         2,
            "processed_frames": 0,
            "total_frames":     0,
            "error":            None,
            "output_path":      None,
            "video_url":        None,
            "analyzer":         None,
            "player_stats":     {},
            "ball_action_stats": {},
            "ball_action_predictions": [],
            "ball_action_predictions_path": None,
            "ball_action_predictions_payload": None,
            "ball_action_events_path": None,
            "csv_dir":          None,
            "csv_files":        {},
            "csv_errors":       {},
            "csv_derived_stats": {},
            "preview_path":     None,
            "auth_header":      request.headers.get("Authorization"),
            "original_filename": video_file.filename,
            "title":            request.form.get("title") or request.form.get("project_name") or video_file.filename,
            "project_name":     request.form.get("project_name") or request.form.get("title") or video_file.filename,
            "input_path":       upload_path,
        }

    t = threading.Thread(target=_process_video, args=(job_id, upload_path, True, True), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "status": "queued", "progress": 2, "stage": "queued"})


# ── Upload video & start a Ball Action job ─────────────────────────────────────
@app.route("/ball_action_video", methods=["POST"])
@require_auth(*AUTHENTICATED_ROLES)
def ball_action_video():
    if BALL_ACTION_MODEL is None:
        return jsonify({
            "error": "Action spotting model is not loaded. "
                     f"{BALL_ACTION_MODEL_ERROR or 'Check ball_model_FULL_OBJECT.pt.'}"
        }), 503

    if "video" not in request.files:
        return jsonify({"error": "No video file in request (field name: 'video')."}), 400

    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    job_id = str(uuid.uuid4())
    upload_path = os.path.join(OUTPUT_DIR, f"{job_id}_input{os.path.splitext(video_file.filename)[1]}")
    video_file.save(upload_path)

    with jobs_lock:
        jobs[job_id] = {
            "status":           "queued",
            "stage":            "queued",
            "progress":         2,
            "processed_frames": 0,
            "total_frames":     0,
            "error":            None,
            "output_path":      None,
            "video_url":        None,
            "analyzer":         None,
            "player_stats":     {},
            "ball_action_stats": {},
            "ball_action_predictions": [],
            "ball_action_predictions_path": None,
            "ball_action_predictions_payload": None,
            "ball_action_events_path": None,
            "csv_dir":          None,
            "csv_files":        {},
            "csv_errors":       {},
            "csv_derived_stats": {},
            "preview_path":     None,
            "auth_header":      request.headers.get("Authorization"),
            "original_filename": video_file.filename,
            "title":            request.form.get("title") or video_file.filename,
            "project_name":     request.form.get("project_name") or request.form.get("title") or video_file.filename,
            "input_path":       upload_path,
        }

    t = threading.Thread(target=_process_ball_action_video, args=(job_id, upload_path), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "status": "queued", "progress": 2, "stage": "queued"})


# ── Poll job status ────────────────────────────────────────────────────────────
@app.route("/job_status/<job_id>", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        _refresh_job_auth_from_request(job)
        status = job.get("status") if job is not None else None
        if (
            job is not None
            and status not in {"done", "saving_csv_outputs", "persisting_results"}
            and int(job.get("progress") or 0) >= 98
        ):
            _try_finalize_from_fast_csv_outputs(job_id, job)

    if job is None:
        return jsonify({"status": "not_found"}), 404

    resp = {
        "status":           job["status"],
        "progress":         job["progress"],
        "stage":            job["stage"],
        "processed_frames": job["processed_frames"],
        "total_frames":     job["total_frames"],
        "error":            job["error"],
        "video_url":        job.get("video_url"),
        "has_preview":      bool(job.get("preview_path") and os.path.exists(job["preview_path"])),
    }
    if job.get("ball_action_predictions_path"):
        resp["ball_action_predictions_url"] = f"/job/{job_id}/ball_action_predictions"
        resp["ball_action_predictions_path"] = job.get("ball_action_predictions_path")
    if job.get("ball_action_events_path"):
        resp["ball_action_events_url"] = f"/job/{job_id}/ball_action_events"
        resp["ball_action_events_path"] = job.get("ball_action_events_path")
    if job["status"] == "done":
        resp["ball_action_stats"] = job.get("ball_action_stats", {})
        resp["ball_action_predictions"] = job.get("ball_action_predictions", [])
        resp["csv_dir"] = job.get("csv_dir")
        resp["csv_files"] = {
            key: {
                "path": path,
                "url": f"/job/{job_id}/csv/{key}",
            }
            for key, path in job.get("csv_files", {}).items()
        }
        resp["csv_errors"] = job.get("csv_errors", {})
        resp["csv_derived_stats"] = job.get("csv_derived_stats", {})
    return jsonify(resp)


# ── Serve processed video ──────────────────────────────────────────────────────
@app.route("/video/<job_id>", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def serve_video(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None or job["status"] != "done":
        abort(404)

    output_path = job["output_path"]
    if not output_path or not os.path.exists(output_path):
        abort(404)

    return send_file(output_path, mimetype="video/mp4",
                     as_attachment=False, download_name=f"result_{job_id[:8]}.mp4")


# ── Serve latest preview frame (JPEG, updates every ~1 sec of video) ──────────
# Serve generated CSV outputs
@app.route("/job/<job_id>/csv/<csv_key>", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def serve_job_csv(job_id: str, csv_key: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None or job["status"] != "done":
        abort(404)

    csv_path = job.get("csv_files", {}).get(csv_key)
    if not csv_path or not os.path.exists(csv_path):
        abort(404)

    return send_file(
        csv_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name=os.path.basename(csv_path),
    )


# Serve latest preview frame (JPEG, updates every ~1 sec of video)
@app.route("/job/<job_id>/latest_frame", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def latest_frame(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None:
        abort(404)

    preview_path = job.get("preview_path")
    if not preview_path or not os.path.exists(preview_path):
        abort(404)

    return send_file(preview_path, mimetype="image/jpeg",
                     download_name="latest_frame.jpg")


# ── List completed jobs (for Heatmap page) ────────────────────────────────────
@app.route("/jobs", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def list_jobs():
    with jobs_lock:
        result = [
            {
                "job_id": jid,
                "status": j["status"],
                "title": j.get("title") or j.get("original_filename") or f"Job {jid[:8]}",
                "original_filename": j.get("original_filename"),
                "model_name": j.get("model_name"),
                "processed_frames": j.get("processed_frames"),
                "total_frames": j.get("total_frames"),
            }
            for jid, j in jobs.items()
            if j["status"] == "done"
        ]
    return jsonify(result)


# ── Player IDs for a job ───────────────────────────────────────────────────────
@app.route("/job/<job_id>/players", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def job_players(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is not None and job["status"] == "done" and job.get("analyzer") is not None:
        analyzer: FootballAnalyzer = job["analyzer"]
        player_ids = []
        for pid in sorted(analyzer.heatmap_coordinates.keys(), key=lambda value: str(value)):
            try:
                player_ids.append(int(pid))
            except (TypeError, ValueError):
                continue
        return jsonify({"player_ids": player_ids})

    positions = _load_player_positions_csv(job_id, job)
    if positions is None:
        return jsonify({"error": "Job not available"}), 404

    player_ids = []
    for value in sorted(positions["tracker_id"].astype(str).unique(), key=lambda item: (not item.isdigit(), item)):
        if value.isdigit():
            player_ids.append(int(value))

    return jsonify({"player_ids": player_ids})


# ── Player stats for a job ────────────────────────────────────────────────────
@app.route("/job/<job_id>/stats", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def job_stats(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is not None and job["status"] == "done" and job.get("player_stats"):
        return jsonify({"stats": job["player_stats"]})

    positions = _load_player_positions_csv(job_id, job)
    if positions is None:
        return jsonify({"error": "Job not available"}), 404

    return jsonify({"stats": _player_stats_from_positions(positions)})


# ── Ball action stats for a job ───────────────────────────────────────────────
@app.route("/job/<job_id>/ball_action_stats", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def job_ball_action_stats(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None:
        return jsonify({"error": "Job not available"}), 404

    return jsonify({"ball_action_stats": job.get("ball_action_stats", {})})


@app.route("/job/<job_id>/ball_action_predictions", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def job_ball_action_predictions(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None:
        return jsonify({"error": "Job not available"}), 404

    predictions_path = job.get("ball_action_predictions_path")
    if predictions_path and os.path.exists(predictions_path):
        return send_file(
            predictions_path,
            mimetype="application/json",
            as_attachment=False,
            download_name=f"ball_action_predictions_{job_id[:8]}.json",
        )

    return jsonify(job.get("ball_action_predictions_payload") or {
        **BALL_ACTION_CONFIG,
        "predictions": job.get("ball_action_predictions", []),
    })

# ── Heatmap: Player (via module method) ───────────────────────────────────────
@app.route("/job/<job_id>/ball_action_events", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def job_ball_action_events(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None:
        return jsonify({"error": "Job not available"}), 404

    events_path = job.get("ball_action_events_path")
    if not events_path or not os.path.exists(events_path):
        return jsonify({"error": "Event log not available yet"}), 404

    return send_file(
        events_path,
        mimetype="application/x-ndjson",
        as_attachment=False,
        download_name=f"ball_action_events_{job_id[:8]}.jsonl",
    )


@app.route("/heatmap/player/<job_id>/<int:player_id>", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def heatmap_player(job_id: str, player_id: int):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is not None and job["status"] == "done" and job.get("analyzer") is not None:
        analyzer: FootballAnalyzer = job["analyzer"]

        # ── Call the module's method — no direct model inference here ────────────
        img = analyzer.generate_player_heatmap(player_id=player_id)
    else:
        job = job or {"auth_header": request.headers.get("Authorization")}
        positions = _load_player_positions_csv(job_id, job)
        img = _render_heatmap_from_positions(positions, "player", str(player_id))
        if img is None:
            return jsonify({"error": "Job not done or heatmap data not found"}), 404

    buf = _encode_and_persist_heatmap(job_id, job, "player", str(player_id), img)
    if buf is None:
        return jsonify({"error": "Failed to encode heatmap image"}), 500

    return send_file(
        io.BytesIO(buf.tobytes()),
        mimetype="image/png",
        download_name=f"heatmap_player_{player_id}.png"
    )


# ── Heatmap: Team (via module method) ─────────────────────────────────────────
@app.route("/heatmap/team/<job_id>/<int:team_id>", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def heatmap_team(job_id: str, team_id: int):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is not None and job["status"] == "done" and job.get("analyzer") is not None:
        analyzer: FootballAnalyzer = job["analyzer"]

        # ── Call the module's method — no direct model inference here ────────────
        img = analyzer.generate_team_heatmap(team_id=team_id)
    else:
        job = job or {"auth_header": request.headers.get("Authorization")}
        positions = _load_player_positions_csv(job_id, job)
        img = _render_heatmap_from_positions(positions, "team", str(team_id))
        if img is None:
            return jsonify({"error": "Job not done or heatmap data not found"}), 404

    buf = _encode_and_persist_heatmap(job_id, job, "team", str(team_id), img)
    if buf is None:
        return jsonify({"error": "Failed to encode heatmap image"}), 500

    return send_file(
        io.BytesIO(buf.tobytes()),
        mimetype="image/png",
        download_name=f"heatmap_team_{team_id}.png"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTION RECOGNITION  (Keras VGG16+GRU model inference)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory job store for action recognition
action_jobs: dict = {}
action_jobs_lock = threading.Lock()

PLAYER_ACTION_CLASSES = [
    "corner",
    "foul",
    "freekick",
    "goalkick",
    "longpass",
    "ontarget",
    "penalty",
    "shortpass",
    "substitution",
    "throw-in",
]


def _count_player_actions(actions: list[dict]) -> dict:
    counts = {name: 0 for name in PLAYER_ACTION_CLASSES}
    for action in actions:
        key = str(action.get("action") or action.get("predicted_action") or "").strip().lower()
        if key in counts:
            counts[key] += 1
    return counts


def _confidence_average(actions: list[dict]) -> float:
    values = []
    for action in actions:
        try:
            value = float(action.get("confidence", 0))
        except (TypeError, ValueError):
            value = 0
        values.append(value / 100 if value > 1 else value)
    return round(sum(values) / len(values), 4) if values else 0


def _build_player_action_review(actions: list[dict]) -> dict:
    action_counts = _count_player_actions(actions)
    total_clips = len(actions)
    average_confidence = _confidence_average(actions)

    short_count = action_counts.get("shortpass", 0)
    long_count = action_counts.get("longpass", 0)
    total_passes = short_count + long_count
    short_ratio = short_count / total_passes if total_passes else 0
    long_ratio = long_count / total_passes if total_passes else 0

    if total_passes == 0:
        passing_profile = "Not enough passing data"
        passing_explanation = "No short pass or long pass clips were detected."
    elif short_ratio >= 0.70:
        passing_profile = "Short-passing oriented"
        passing_explanation = "The player relies more on short passes than long passes."
    elif long_ratio >= 0.45:
        passing_profile = "Direct-passing oriented"
        passing_explanation = "The player uses long passes frequently, suggesting a direct passing style."
    else:
        passing_profile = "Balanced passing profile"
        passing_explanation = "The player shows a balanced use of short and long passes."

    passing_style = {
        "short_pass_count": short_count,
        "long_pass_count": long_count,
        "total_passes": total_passes,
        "short_pass_ratio": round(short_ratio, 3),
        "long_pass_ratio": round(long_ratio, 3),
        "passing_profile": passing_profile,
        "explanation": passing_explanation,
    }

    ontarget = action_counts.get("ontarget", 0)
    penalty = action_counts.get("penalty", 0)
    freekick = action_counts.get("freekick", 0)
    corner = action_counts.get("corner", 0)
    longpass = action_counts.get("longpass", 0)
    attacking_threat = {
        "score": round((ontarget * 4) + (penalty * 5) + (freekick * 2) + (corner * 2) + (longpass * 0.5), 3),
        "components": {
            "ontarget": ontarget,
            "penalty": penalty,
            "freekick": freekick,
            "corner": corner,
            "longpass": longpass,
        },
        "explanation": (
            "The player shows attacking involvement through shots on target, free kicks, "
            "corners, penalties, or long progressive passes. This is an estimated clip-based score only."
        ),
    }

    foul_count = action_counts.get("foul", 0)
    if foul_count <= 10:
        risk_level = "Low"
    elif foul_count <= 15:
        risk_level = "Medium"
    else:
        risk_level = "High"
    discipline_risk = {
        "foul_count": foul_count,
        "discipline_risk_score": foul_count * 2,
        "risk_level": risk_level,
        "warning": (
            "High foul frequency may increase the risk of conceding dangerous free kicks or receiving cards."
            if risk_level == "High" else None
        ),
    }

    throw_in = action_counts.get("throw-in", 0)
    goalkick = action_counts.get("goalkick", 0)
    set_piece_count = corner + freekick + penalty + throw_in + goalkick
    set_piece_summary = {
        "corner": corner,
        "freekick": freekick,
        "penalty": penalty,
        "throw-in": throw_in,
        "goalkick": goalkick,
        "set_piece_count": set_piece_count,
        "set_piece_ratio": round(set_piece_count / total_clips, 3) if total_clips else 0,
        "explanation": "This shows how often the uploaded clips contain set-piece or restart situations.",
    }

    attacking_ratio = (ontarget + penalty + freekick + corner) / total_clips if total_clips else 0
    set_piece_ratio = (freekick + penalty + corner) / total_clips if total_clips else 0
    foul_ratio = foul_count / total_clips if total_clips else 0

    detected_styles = []
    style_reasons = []
    team_styles = []

    if short_ratio >= 0.70:
        detected_styles.append("Possession Player")
        style_reasons.append("The player has a high short pass ratio, showing a tendency to keep possession and connect play.")
        team_styles.extend(["Possession-based teams", "Build-up teams", "Teams that use short passing combinations", "Teams that rely on midfield control"])

    if long_ratio >= 0.45:
        detected_styles.append("Direct Playmaker")
        style_reasons.append("The player uses long passes frequently, which may help progress the ball quickly or switch play.")
        team_styles.extend(["Direct football teams", "Counter-attacking teams", "Fast transition teams", "Teams that use long balls behind defenders"])

    if attacking_ratio >= 0.25:
        detected_styles.append("Attacking Threat Player")
        style_reasons.append("The player appears involved in dangerous attacking situations such as shots on target, penalties, free kicks, or corners.")
        team_styles.extend(["Attacking teams", "High-pressing teams", "Teams that create many final-third chances"])

    if set_piece_ratio >= 0.20:
        detected_styles.append("Set-Piece Specialist")
        style_reasons.append("The player is frequently involved in set-piece execution such as free kicks, penalties, or corners.")
        team_styles.extend(["Teams that rely on set pieces", "Teams with strong aerial players", "Teams that create chances from corners and free kicks", "Teams needing a reliable penalty or free-kick taker"])

    if foul_ratio >= 0.15:
        detected_styles.append("Physical / Aggressive Player")
        style_reasons.append("The player commits fouls frequently, suggesting a more physical or aggressive profile.")
        team_styles.extend(["High-pressing teams", "Defensive teams", "Teams that rely on physical duels", "Teams using aggressive pressing"])

    if not detected_styles:
        detected_styles.append("Balanced Player")
        style_reasons.append("No single action type strongly dominates, so the player appears to contribute across different actions.")
        team_styles.extend(["Flexible tactical systems", "Teams that change style during matches", "Teams needing adaptable players", "Utility roles or flexible midfield roles"])

    if risk_level == "High":
        style_reasons.append("High foul frequency may increase the risk of conceding dangerous free kicks or receiving cards.")

    main_style = detected_styles[0]
    unique_team_styles = list(dict.fromkeys(team_styles))
    limitations_note = (
        "This is an estimated style profile based only on uploaded single-player clips and model predictions. "
        "It does not use full-match tracking, team context, player identity, or timestamps."
    )
    player_profile = {
        "main_style": main_style,
        "secondary_styles": detected_styles[1:],
        "passing_profile": passing_profile,
        "discipline_risk": risk_level,
        "suitable_team_styles": unique_team_styles,
        "explanation": " ".join(style_reasons),
        "limitations_note": limitations_note,
    }

    reasons = {
        "Possession Player": "The player appears to be short-passing oriented and may fit systems that depend on possession and build-up play.",
        "Direct Playmaker": "The player appears comfortable with long passes and may fit direct, counter-attacking, or fast-transition systems.",
        "Attacking Threat Player": "The player appears involved in attacking actions and may fit teams that create frequent final-third chances.",
        "Set-Piece Specialist": "The player appears frequently involved in set pieces and may fit teams that rely on corners, free kicks, or penalties.",
        "Physical / Aggressive Player": "The player appears physically involved and may fit high-pressing or defensive systems, but foul risk should be reviewed.",
        "Balanced Player": "The player appears balanced and may fit flexible tactical systems.",
    }

    if total_clips >= 30 and average_confidence >= 0.85:
        reliability = "High"
    elif total_clips >= 15 and average_confidence >= 0.75:
        reliability = "Medium"
    else:
        reliability = "Low"

    return {
        "action_counter": action_counts,
        "analysis": {
            "passing_style": passing_style,
            "estimated_attacking_threat": attacking_threat,
            "discipline_risk": discipline_risk,
            "set_piece_summary": set_piece_summary,
            "estimated_player_playing_style_profile": player_profile,
            "suitable_team_styles": {
                "recommended_team_styles": unique_team_styles,
                "reason": reasons.get(main_style, reasons["Balanced Player"]),
            },
            "profile_reliability": {
                "profile_reliability": reliability,
                "reason": f"The profile is based on {total_clips} analyzed clips with {round(average_confidence * 100, 2)}% average confidence.",
            },
        },
    }


def _process_action_recognition(job_id: str, video_path: str):
    """Background thread for action recognition using the Keras model."""

    def _update(**kwargs):
        with action_jobs_lock:
            j = action_jobs[job_id]
            for k, v in kwargs.items():
                j[k] = v

    try:
        if ACTION_MODEL is None:
            raise RuntimeError(
                "Action recognition model failed to load at startup. "
                "Check that sen_best_model_4.keras exists and keras is installed."
            )

        # ── 1. Read video metadata ────────────────────────────────────────
        _update(status="extracting", stage="extracting", progress=5)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()

        print(f"[ACTION {job_id[:8]}] Video: {width}x{height} @ {fps:.1f}fps, "
              f"{total_frames} frames, {duration:.1f}s", flush=True)
        _update(progress=10, total_frames=total_frames)

        # ── 2. Run Keras model inference (sliding window) ─────────────────
        _update(status="analyzing", stage="model_inference", progress=15)
        print(f"[ACTION {job_id[:8]}] Running Keras VGG16+GRU inference …", flush=True)

        def _on_progress(model_pct: int):
            # Map model progress (0-100) → job progress (15-90)
            pct = 15 + int(75 * model_pct / 100)
            _update(progress=pct, processed_frames=int(total_frames * model_pct / 100))

        actions = ACTION_MODEL.predict_video(
            video_path=video_path,
            fps=fps,
            confidence_threshold=0.35,
            progress_callback=_on_progress,
        )

        _update(status="post_processing", stage="post_processing", progress=92)
        print(f"[ACTION {job_id[:8]}] Found {len(actions)} action segments.", flush=True)
        player_action_review = _build_player_action_review(actions)

        # ── 3. Done ───────────────────────────────────────────────────────
        with action_jobs_lock:
            action_jobs[job_id].update({
                "status": "done",
                "stage": "done",
                "progress": 100,
                "processed_frames": total_frames,
                "actions": actions,
                "player_action_review": player_action_review,
                "total_actions": len(actions),
                "video_duration": round(duration, 2),
            })
            job_snapshot = dict(action_jobs[job_id])

        _post_ai_job_statistics(
            job_id=job_id,
            job_data=job_snapshot,
            job_type="ActionRecognition",
            statistics=[
                {
                    "moduleName": "action_recognition",
                    "modelName": "sen_best_model_4.keras",
                    "statType": "action_segments",
                    "statsJson": json.dumps({
                        "actions": actions,
                        "total_actions": len(actions),
                        "video_duration": round(duration, 2),
                    }),
                },
                {
                    "moduleName": "review_player",
                    "modelName": "sen_best_model_4.keras",
                    "statType": "player_action_review",
                    "statsJson": json.dumps(player_action_review),
                }
            ],
        )
        print(f"[ACTION {job_id[:8]}] Done — {len(actions)} actions.", flush=True)

    except Exception as exc:
        import traceback
        traceback.print_exc()
        _update(status="error", stage="error", error=str(exc))
        print(f"[ACTION {job_id[:8]}] ERROR: {exc}", flush=True)
    finally:
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except OSError:
            pass


# ── Upload video for action recognition ───────────────────────────────────
@app.route("/recognize_action", methods=["POST"])
@require_auth(*AUTHENTICATED_ROLES)
def recognize_action():
    if "video" not in request.files:
        return jsonify({"error": "No video file in request (field name: 'video')."}), 400

    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    job_id = str(uuid.uuid4())
    ext = os.path.splitext(video_file.filename)[1]
    upload_path = os.path.join(OUTPUT_DIR, f"{job_id}_action_input{ext}")
    video_file.save(upload_path)

    with action_jobs_lock:
        action_jobs[job_id] = {
            "status": "queued",
            "stage": "queued",
            "progress": 2,
            "processed_frames": 0,
            "total_frames": 0,
            "error": None,
            "actions": [],
            "total_actions": 0,
            "video_duration": 0,
            "auth_header": request.headers.get("Authorization"),
            "original_filename": video_file.filename,
            "title": request.form.get("title") or video_file.filename,
            "input_path": upload_path,
            "model_name": "sen_best_model_4.keras",
            "upload_batch_id": request.form.get("upload_batch_id"),
            "upload_batch_title": request.form.get("upload_batch_title"),
            "upload_batch_video_count": request.form.get("upload_batch_video_count"),
            "upload_batch_index": request.form.get("upload_batch_index"),
            "player_name": request.form.get("player_name"),
        }

    t = threading.Thread(target=_process_action_recognition, args=(job_id, upload_path), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "status": "queued", "progress": 2})


# ── Poll action recognition job status ────────────────────────────────────
@app.route("/action_job_status/<job_id>", methods=["GET"])
@require_auth(*AUTHENTICATED_ROLES)
def action_job_status(job_id: str):
    with action_jobs_lock:
        job = action_jobs.get(job_id)

    if job is None:
        return jsonify({"status": "not_found"}), 404

    resp = {
        "status": job["status"],
        "progress": job["progress"],
        "stage": job["stage"],
        "processed_frames": job["processed_frames"],
        "total_frames": job["total_frames"],
        "error": job["error"],
    }

    if job["status"] == "done":
        resp["actions"] = job["actions"]
        resp["player_action_review"] = job.get("player_action_review")
        resp["total_actions"] = job["total_actions"]
        resp["video_duration"] = job["video_duration"]

    return jsonify(resp)


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
