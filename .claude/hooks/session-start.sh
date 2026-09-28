#!/bin/bash
# Installs the AI Video Factory toolchain in Claude Code on the web sessions:
# ffmpeg, PyYAML, piper-tts, faster-whisper, the Piper voice and the Whisper model.
# Idempotent: already-installed pieces are skipped. Network failures don't block the session.
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

APP="$CLAUDE_PROJECT_DIR/ai-video-factory"

bash "$APP/scripts/setup_env.sh"

# Pre-download the Whisper model used for caption timing (skips if already cached).
cd "$APP" && python3 - <<'PY' || echo "!! Whisper model download failed (is huggingface.co allowed?). Continuing."
import sys
sys.path.insert(0, ".")
from src.config import load_settings
s = load_settings()
cfg = s["transcription"]["whisper_local"]
from faster_whisper import WhisperModel
WhisperModel(cfg["model"], device=cfg["device"], compute_type=cfg["compute_type"],
             download_root=str(s.path("models") / "whisper"))
print("Whisper model ready:", cfg["model"])
PY

exit 0
