#!/usr/bin/env python3
"""Build SYNTHETIC test footage: a Hindi text-to-speech voice reading the sample script with a false
start, an aside, a bad take and a long pause, over generated video. It exercises the pipeline; it is
not real camera footage and says so on screen.

Usage: tools/make_test_footage.py OUT_DIR   (needs piper-tts and the Hindi voice from tools/setup_models.sh)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

PARTS = [  # (spoken text, pause after, label)
    ("एक एआई ने जावा में एक क्रिटिकल", 0.9, "false_start"),
    ("सॉरी, फिर से।", 0.8, "aside"),
    ("एक एआई ने जावा में एक क्रिटिकल बग सिर्फ एक घंटे में ढूंढ लिया।", 0.35, "s0"),
    ("खर्चा? दो सौ डॉलर से कम।", 0.5, "s1"),
    ("यह क्लेम है सिक्योरिटी स्टार्टअप कैलिफ का।", 0.3, "s2"),
    ("बग का नाम जावा फॉर शेल।", 0.4, "s3"),
    ("जावा पर बैंक्स, एयरलाइंस, और शायद आपकी कंपनी का बैकएंड चलता है।", 2.4, "s4_then_long_pause"),
    ("ओरेकल का पैच आ गया", 0.7, "s5_bad_take"),
    ("ओरेकल का पैच आ चुका है।", 0.45, "s5"),
    ("लेकिन पैनिक नहीं।", 0.3, "s6"),
    ("ओरेकल खुद कहता है एक्सप्लॉइट करना मुश्किल है, और अभी तक कोई रियल अटैक कन्फर्म नहीं।", 0.5, "s7"),
    ("असली सबक: बग ढूंढना अब सस्ता हो गया है।", 0.3, "s8"),
    ("पैच लेट करना महंगा।", 0.5, "s9"),
    ("डेवलपर हो? आज ही जावा अपडेट करो।", 1.2, "s10_s11"),
]


def narration(out: Path, models: Path) -> float:
    from piper import PiperVoice
    voice = PiperVoice.load(str(models / "vits-piper-hi_IN-pratham-medium" / "hi_IN-pratham-medium.onnx"))
    sr, t, chunks, marks = 22050, 0.8, [np.zeros(int(0.8 * 22050), dtype=np.float32)], []
    for text, pause, label in PARTS:
        s = np.concatenate([c.audio_float_array for c in voice.synthesize(text)]).astype(np.float32)
        marks.append({"label": label, "start": round(t, 3), "end": round(t + len(s) / sr, 3), "text": text})
        chunks += [s, np.zeros(int(pause * sr), dtype=np.float32)]
        t += len(s) / sr + pause
    x = np.concatenate(chunks) * 0.7
    x = x + np.random.default_rng(7).normal(0, 0.004, len(x)).astype(np.float32)   # room noise
    sf.write(str(out / "narration.wav"), x, sr)
    (out / "truth.json").write_text(json.dumps(marks, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(x) / sr


def video(out: Path, dur: float) -> None:
    font = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
    def run(*a):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)
    label = "drawtext=fontfile={f}:text='SYNTHETIC TEST FOOTAGE  %{{pts\\:hms}}':x=(w-tw)/2:y={y}:fontsize=40:fontcolor=white:box=1:boxcolor=black@0.5"
    # A: iPhone-style vertical clip: HEVC in MOV, 60 fps, stored landscape with a 90-degree rotation tag.
    run("-f", "lavfi", "-i", f"gradients=s=1920x1080:r=60:speed=0.02:c0=0x2b3a55:c1=0x8a6d5b:c2=0x1d2433:d={dur}",
        "-i", out / "narration.wav", "-vf", "transpose=2," + label.format(f=font, y=120) + ",transpose=1",
        "-c:v", "libx265", "-preset", "ultrafast", "-crf", "26", "-tag:v", "hvc1", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", out / "_landscape.mov")
    run("-display_rotation", "90", "-i", out / "_landscape.mov", "-c", "copy", out / "sample_vertical_hevc.mov")
    (out / "_landscape.mov").unlink()
    # B: horizontal H.264 MP4 at 30 fps.
    run("-f", "lavfi", "-i", f"gradients=s=1920x1080:r=30:speed=0.02:c0=0x33415c:c1=0x7d8597:c2=0x001845:d={dur}",
        "-i", out / "narration.wav", "-vf", label.format(f=font, y=80),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
        out / "sample_horizontal_h264.mp4")


if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    models = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / "models"
    d = narration(out, models)
    video(out, d)
    print(f"wrote {out} ({d:.1f}s)")
