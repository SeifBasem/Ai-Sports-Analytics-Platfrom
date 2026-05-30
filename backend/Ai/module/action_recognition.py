"""
action_recognition.py – Keras VGG16+GRU Action Recognition
-----------------------------------------------------------
Loads `sen_best_model_4.keras` and provides sliding-window inference
over a video file.  Each window is 10 frames resized to 150×150 RGB.
The model outputs one of 10 football action classes.

The model was saved with TF-Keras 2.x. Since standalone Keras 3 cannot
deserialize the legacy config, we reconstruct the architecture and
load weights via an explicit name mapping from the .keras h5 archive.

Usage (from app.py):
    from module.action_recognition import ActionRecognitionModel
    arm = ActionRecognitionModel()                   # loads model once
    actions = arm.predict_video(video_path, fps=25)  # returns list[dict]
"""

import os
import sys
import io
import shutil
import tempfile
import zipfile
import re
import cv2
import numpy as np
import h5py

# ── Keras backend (numpy – no TensorFlow needed) ─────────────────────────────
os.environ.setdefault("KERAS_BACKEND", "numpy")

import keras
from keras import layers

# ── Constants ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "sen_best_model_4.keras")

SEQUENCE_LENGTH = 10
IMG_HEIGHT      = 150
IMG_WIDTH       = 150
NUM_CLASSES     = 10

# Correct class labels from the training code
CLASS_LABELS = [
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

DEFAULT_CONFIDENCE_THRESHOLD = 0.35

# ── VGG16 preprocessing (matches training) ───────────────────────────────────
# VGG16 preprocess_input converts RGB→BGR and subtracts ImageNet means.
# We replicate it without needing TensorFlow.
_IMAGENET_MEAN_BGR = np.array([103.939, 116.779, 123.68], dtype=np.float32)


def _vgg16_preprocess(frame_rgb: np.ndarray) -> np.ndarray:
    """Apply VGG16 preprocessing: RGB→BGR, subtract ImageNet mean."""
    bgr = frame_rgb[..., ::-1].astype(np.float32)   # RGB → BGR
    bgr -= _IMAGENET_MEAN_BGR
    return bgr


# ── Architecture reconstruction ─────────────────────────────────────────────
def _build_model() -> keras.Model:
    """
    Reconstruct the exact VGG16 + GRU architecture from the training code.
    """
    # Suppress Keras's verbose output during VGG16 init
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        vgg_base = keras.applications.VGG16(
            include_top=False,
            weights=None,
            input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
        )
    finally:
        sys.stdout = old_stdout

    video_input = layers.Input(shape=(SEQUENCE_LENGTH, IMG_HEIGHT, IMG_WIDTH, 3))
    x = layers.TimeDistributed(vgg_base)(video_input)
    x = layers.TimeDistributed(layers.GlobalAveragePooling2D())(x)
    x = layers.TimeDistributed(layers.Dense(512, activation="relu"))(x)
    x = layers.GRU(64)(x)
    x = layers.Dropout(0.5)(x)
    output = layers.Dense(NUM_CLASSES, activation="softmax")(x)

    return keras.Model(inputs=video_input, outputs=output, name="action_recognition")


# ── Weight loading ───────────────────────────────────────────────────────────

# Explicit mapping: h5 conv2d_N → Keras 3 VGG16 layer names
_H5_TO_MODEL_CONV = {
    "conv2d":    "block1_conv1",
    "conv2d_1":  "block1_conv2",
    "conv2d_2":  "block2_conv1",
    "conv2d_3":  "block2_conv2",
    "conv2d_4":  "block3_conv1",
    "conv2d_5":  "block3_conv2",
    "conv2d_6":  "block3_conv3",
    "conv2d_7":  "block4_conv1",
    "conv2d_8":  "block4_conv2",
    "conv2d_9":  "block4_conv3",
    "conv2d_10": "block5_conv1",
    "conv2d_11": "block5_conv2",
    "conv2d_12": "block5_conv3",
}


def _h5_path_to_model_path(h5_path: str) -> str | None:
    """
    Convert an h5 dataset path to the corresponding Keras 3 model
    variable path.  Returns None if the path is not a layer weight.

    Examples:
        layers/time_distributed/layer/layers/conv2d/vars/0
            → block1_conv1/kernel
        layers/time_distributed/layer/layers/conv2d/vars/1
            → block1_conv1/bias
        layers/time_distributed_2/layer/vars/0
            → time_distributed_2/dense/kernel
        layers/gru/cell/vars/0
            → gru/gru_cell/kernel
        layers/dense/vars/0
            → dense_1/kernel
    """
    # Normalise Windows backslash paths
    h5_path = h5_path.replace("\\", "/")

    # ── VGG16 conv layers ────────────────────────────────────────────
    m = re.match(
        r"layers/time_distributed/layer/layers/(conv2d(?:_\d+)?)/vars/(\d+)",
        h5_path,
    )
    if m:
        h5_layer = m.group(1)
        var_idx  = int(m.group(2))
        model_layer = _H5_TO_MODEL_CONV.get(h5_layer)
        if model_layer is None:
            return None
        suffix = "kernel" if var_idx == 0 else "bias"
        return f"{model_layer}/{suffix}"

    # ── Dense(512) inside TimeDistributed ─────────────────────────────
    m = re.match(r"layers/time_distributed_2/layer/vars/(\d+)", h5_path)
    if m:
        var_idx = int(m.group(1))
        suffix = "kernel" if var_idx == 0 else "bias"
        return f"time_distributed_2/dense/{suffix}"

    # ── GRU ───────────────────────────────────────────────────────────
    m = re.match(r"layers/gru/cell/vars/(\d+)", h5_path)
    if m:
        var_idx = int(m.group(1))
        names = ["kernel", "recurrent_kernel", "bias"]
        suffix = names[var_idx] if var_idx < len(names) else f"var_{var_idx}"
        return f"gru/gru_cell/{suffix}"

    # ── Output Dense(10) ──────────────────────────────────────────────
    m = re.match(r"layers/dense/vars/(\d+)", h5_path)
    if m:
        var_idx = int(m.group(1))
        suffix = "kernel" if var_idx == 0 else "bias"
        return f"dense_1/{suffix}"

    return None  # skip optimizer / metrics entries


def _load_weights_from_keras_archive(model: keras.Model, archive_path: str):
    """Extract weights from .keras zip and assign by name mapping."""
    tmp_dir = tempfile.mkdtemp(prefix="keras_weights_")
    try:
        # Extract h5 file from the .keras archive
        with zipfile.ZipFile(archive_path, "r") as zf:
            weight_file = None
            for name in zf.namelist():
                if name.endswith(".h5"):
                    weight_file = name
                    break
            if weight_file is None:
                raise RuntimeError(f"No .h5 weight file in {archive_path}")
            extracted = zf.extract(weight_file, tmp_dir)

        # Build a name → array dict from h5
        h5_weights: dict[str, np.ndarray] = {}
        def _collect(name, obj):
            if isinstance(obj, h5py.Dataset):
                model_path = _h5_path_to_model_path(name)
                if model_path is not None:
                    h5_weights[model_path] = np.array(obj)
        with h5py.File(extracted, "r") as f:
            f.visititems(_collect)

        # Build a name → variable dict from model
        model_vars = {v.path: v for v in model.weights}

        # Assign
        assigned = 0
        for var_path, var in model_vars.items():
            if var_path in h5_weights:
                arr = h5_weights[var_path]
                if tuple(var.shape) == arr.shape:
                    var.assign(arr)
                    assigned += 1
                else:
                    print(f"[ACTION-MODEL] Shape mismatch: {var_path} "
                          f"model={var.shape} h5={arr.shape}", flush=True)
            else:
                print(f"[ACTION-MODEL] Missing h5 weight for: {var_path}", flush=True)

        print(f"[ACTION-MODEL] Assigned {assigned}/{len(model_vars)} weight tensors.",
              flush=True)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Main class ───────────────────────────────────────────────────────────────
class ActionRecognitionModel:
    """Wraps the Keras VGG16+GRU model for football action recognition."""

    def __init__(self, model_path: str | None = None):
        path = model_path or DEFAULT_MODEL_PATH
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Action recognition model not found: {path}")

        print(f"[ACTION-MODEL] Loading model from {path} …", flush=True)
        print("[ACTION-MODEL] Rebuilding VGG16+GRU architecture …", flush=True)
        self.model = _build_model()

        print("[ACTION-MODEL] Loading trained weights …", flush=True)
        _load_weights_from_keras_archive(self.model, path)

        print("[ACTION-MODEL] Model ready.", flush=True)
        print(f"[ACTION-MODEL] Input: {self.model.input_shape}  "
              f"Output: {self.model.output_shape}", flush=True)

    # ── Preprocessing (matches training code) ────────────────────────────────
    @staticmethod
    def _preprocess_frame(frame_bgr: np.ndarray) -> np.ndarray:
        """Resize, convert BGR→RGB, then apply VGG16 preprocessing."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (IMG_WIDTH, IMG_HEIGHT))
        return _vgg16_preprocess(resized)

    @staticmethod
    def _sample_clip_frames(frames: list[np.ndarray]) -> np.ndarray:
        """
        Sample exactly SEQUENCE_LENGTH frames evenly from a list of frames,
        matching the training code's np.linspace approach.
        """
        n = len(frames)
        if n == 0:
            blank = _vgg16_preprocess(np.zeros((IMG_HEIGHT, IMG_WIDTH, 3), dtype=np.float32))
            return np.array([blank] * SEQUENCE_LENGTH, dtype=np.float32)

        indices = np.linspace(0, n - 1, SEQUENCE_LENGTH, dtype=int)
        return np.array([
            ActionRecognitionModel._preprocess_frame(frames[i]) for i in indices
        ], dtype=np.float32)

    # ── Full-video prediction ────────────────────────────────────────────────
    def predict_video(
        self,
        video_path: str,
        fps: float = 25.0,
        stride: int | None = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        progress_callback=None,
    ) -> list[dict]:
        """
        Run sliding-window inference over *video_path*.

        For each window of ~2 seconds, sample SEQUENCE_LENGTH frames evenly
        (matching training preprocessing) and classify.
        """
        if stride is None:
            stride = max(1, SEQUENCE_LENGTH // 2)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        # Read all frames
        frames: list[np.ndarray] = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()

        if not frames:
            return []

        # Determine window size in frames (~2 seconds)
        window_frames = max(SEQUENCE_LENGTH, int(fps * 2))
        frame_stride  = max(1, window_frames // 2)

        raw_actions: list[dict] = []
        total_windows = max(1, (len(frames) - window_frames) // frame_stride + 1)

        for win_idx in range(total_windows):
            start = win_idx * frame_stride
            end   = min(start + window_frames, len(frames))
            if end - start < SEQUENCE_LENGTH:
                break

            window = frames[start:end]

            # Sample SEQUENCE_LENGTH frames evenly from this window
            clip = self._sample_clip_frames(window)
            clip = np.expand_dims(clip, axis=0)  # (1, 10, 150, 150, 3)

            preds = self.model.predict(clip, verbose=0)[0]
            class_idx  = int(np.argmax(preds))
            confidence = float(preds[class_idx])

            if confidence >= confidence_threshold:
                label = (CLASS_LABELS[class_idx]
                         if class_idx < len(CLASS_LABELS)
                         else f"class_{class_idx}")
                raw_actions.append({
                    "action":      label,
                    "confidence":  round(confidence, 4),
                    "start_frame": start + 1,
                    "end_frame":   end,
                    "start_time":  round(start / fps, 2),
                    "end_time":    round(end   / fps, 2),
                })

            if progress_callback is not None:
                pct = int(100 * (win_idx + 1) / total_windows)
                progress_callback(pct)

        return self._merge_adjacent(raw_actions)

    # ── Merge helper ─────────────────────────────────────────────────────────
    @staticmethod
    def _merge_adjacent(actions: list[dict], gap_sec: float = 1.0) -> list[dict]:
        """Merge consecutive windows that predicted the same action."""
        if not actions:
            return []

        actions.sort(key=lambda a: (a["action"], a["start_time"]))
        merged: list[dict] = []

        for act in actions:
            if (
                merged
                and merged[-1]["action"] == act["action"]
                and act["start_time"] - merged[-1]["end_time"] < gap_sec
            ):
                merged[-1]["end_frame"] = act["end_frame"]
                merged[-1]["end_time"]  = act["end_time"]
                merged[-1]["confidence"] = round(
                    max(merged[-1]["confidence"], act["confidence"]), 4
                )
            else:
                merged.append(dict(act))

        merged.sort(key=lambda a: a["start_time"])
        return merged
