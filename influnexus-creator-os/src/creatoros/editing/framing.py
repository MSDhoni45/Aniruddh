"""Choose the 9:16 crop. Horizontal footage is cropped around the speaker's face when one is found."""
from __future__ import annotations

from pathlib import Path

import numpy as np


def face_center_x(src: Path, samples: int = 9) -> float | None:
    """Median horizontal face position as a 0..1 fraction of the displayed frame, or None."""
    try:
        import cv2
        det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    except (ImportError, AttributeError):      # OpenCV missing or built without the cascade detector: centre crop
        return None
    cap = cv2.VideoCapture(str(src))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        return None
    xs = []
    for k in range(samples):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (k + 0.5) / samples))
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale = 640 / gray.shape[1]
        gray = cv2.resize(gray, None, fx=scale, fy=scale)
        faces = det.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            xs.append((x + w / 2) / gray.shape[1])
    cap.release()
    return float(np.median(xs)) if len(xs) >= max(2, samples // 3) else None


def crop_x(src_w: int, src_h: int, out_w: int, out_h: int, face_x: float | None) -> int:
    """Left edge of the crop window after the frame is scaled to cover the output."""
    scale = max(out_w / src_w, out_h / src_h)
    scaled_w = int(round(src_w * scale))
    centre = (face_x if face_x is not None else 0.5) * scaled_w
    return int(min(max(centre - out_w / 2, 0), max(scaled_w - out_w, 0)))
