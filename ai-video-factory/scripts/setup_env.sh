#!/usr/bin/env bash
# Install the AI Video Factory's system + Python dependencies.
#
# Self-contained on purpose: it can be pasted into the Claude Code on the web
# environment "Setup script" field (which may run before the repo is cloned),
# or run locally:  bash ai-video-factory/scripts/setup_env.sh
#
# Everything here is free. Safe to re-run.
set -uo pipefail

SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null && SUDO="sudo"

if ! command -v ffmpeg >/dev/null; then
  echo ">> Installing ffmpeg"
  $SUDO apt-get update -qq || true          # unreachable extra repos only warn
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq ffmpeg
fi

echo ">> Installing Python packages"
python3 -m pip install -q "PyYAML>=6.0" "piper-tts>=1.8,<2" "faster-whisper>=1.1,<2"

# Piper voice (needs huggingface.co to be reachable). Non-fatal if blocked.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
if [ -f "$REPO_DIR/config/settings.yaml" ]; then
  # In the repo: verified download (size + MD5), repairs truncated files.
  echo ">> Checking Piper voice"
  python3 "$REPO_DIR/scripts/setup_piper_voice.py" \
    || echo "!! Voice download failed (is huggingface.co allowed?). Continuing."
else
  # Standalone (e.g. pasted as a setup script before the repo exists).
  VOICE="${PIPER_VOICE:-en_US-ryan-high}"
  MODELS="${PIPER_MODELS_DIR:-$HOME/.local/share/piper-voices}"
  mkdir -p "$MODELS"
  if [ ! -f "$MODELS/$VOICE.onnx" ]; then
    echo ">> Downloading Piper voice $VOICE -> $MODELS"
    python3 -m piper.download_voices "$VOICE" --download-dir "$MODELS" \
      || echo "!! Voice download failed (is huggingface.co allowed?). Continuing."
  fi
fi

ffmpeg -version | head -1
python3 -c "import piper; print('piper-tts OK')"
