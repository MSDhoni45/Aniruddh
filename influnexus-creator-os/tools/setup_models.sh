#!/usr/bin/env bash
# Download the speech models (about 950 MB) from GitHub releases. No paid services.
set -euo pipefail
DEST="${CREATOROS_MODELS:-$HOME/models}"
BASE="https://github.com/k2-fsa/sherpa-onnx/releases/download"
mkdir -p "$DEST" && cd "$DEST"
[ -f silero_vad.onnx ] || curl -fsSL --retry 3 -O "$BASE/asr-models/silero_vad.onnx"
[ -d sherpa-onnx-whisper-small ] || curl -fsSL --retry 3 "$BASE/asr-models/sherpa-onnx-whisper-small.tar.bz2" | tar xj
if [ "${1:-}" = "--with-test-voice" ] && [ ! -d vits-piper-hi_IN-pratham-medium ]; then
  curl -fsSL --retry 3 "$BASE/tts-models/vits-piper-hi_IN-pratham-medium.tar.bz2" | tar xj
fi
echo "models ready in $DEST"
