#!/usr/bin/env python3
"""Download the Piper voice configured in settings.yaml (tts.piper.voice).

    python3 ai-video-factory/scripts/setup_piper_voice.py            # configured voice
    python3 ai-video-factory/scripts/setup_piper_voice.py en_US-amy-medium

Voices are free (see each voice's MODEL_CARD for its license) and are
downloaded from huggingface.co into models/piper/ (git-ignored).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_settings  # noqa: E402


def main() -> int:
    settings = load_settings()
    voice = sys.argv[1] if len(sys.argv) > 1 else settings["tts"]["piper"]["voice"]
    target = settings.path("models") / "piper"
    target.mkdir(parents=True, exist_ok=True)

    if (target / f"{voice}.onnx").exists() and (target / f"{voice}.onnx.json").exists():
        print(f"Voice already installed: {target / voice}.onnx")
        return 0

    print(f"Downloading Piper voice {voice} -> {target}")
    result = subprocess.run(
        [sys.executable, "-m", "piper.download_voices", voice, "--download-dir", str(target)]
    )
    if result.returncode != 0:
        print(
            "\nDownload failed. If you are in Claude Code on the web, huggingface.co must be\n"
            "allowed in the environment's network settings. Alternatively, place\n"
            f"{voice}.onnx and {voice}.onnx.json in {target} manually.",
            file=sys.stderr,
        )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
