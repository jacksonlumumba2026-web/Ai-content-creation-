#!/usr/bin/env python3
"""Download (or repair) the Piper voice configured in settings.yaml (tts.piper.voice).

    python3 ai-video-factory/scripts/setup_piper_voice.py            # configured voice
    python3 ai-video-factory/scripts/setup_piper_voice.py en_US-amy-medium

Files are verified against the size + MD5 published in Piper's voices.json.
Existing files are re-checked on every run, so a truncated download is
detected and replaced. Downloads go to a .part file and are only moved into
place once verified. Safe to re-run.

Voices are free (see each voice's MODEL_CARD for its license) and come from
huggingface.co; they are stored in models/piper/ (git-ignored).
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_settings  # noqa: E402

BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
VOICES_JSON = BASE_URL + "voices.json?download=true"
ATTEMPTS = 3


def md5_of(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_valid(path: Path, expected: dict) -> bool:
    return (
        path.exists()
        and path.stat().st_size == expected["size_bytes"]
        and md5_of(path) == expected["md5_digest"]
    )


def download_verified(url: str, dest: Path, expected: dict) -> None:
    part = dest.with_name(dest.name + ".part")
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urlopen(url, timeout=60) as response, part.open("wb") as fh:
                while block := response.read(1 << 20):
                    fh.write(block)
            if is_valid(part, expected):
                part.replace(dest)
                return
            got = part.stat().st_size
            print(f"   attempt {attempt}: incomplete/corrupt ({got}/{expected['size_bytes']} bytes)")
        except OSError as exc:
            print(f"   attempt {attempt}: {exc}")
        time.sleep(2 * attempt)
    part.unlink(missing_ok=True)
    raise RuntimeError(f"could not download a valid copy of {dest.name}")


def main() -> int:
    settings = load_settings()
    voice = sys.argv[1] if len(sys.argv) > 1 else settings["tts"]["piper"]["voice"]
    target = settings.path("models") / "piper"
    target.mkdir(parents=True, exist_ok=True)
    wanted = {f"{voice}.onnx", f"{voice}.onnx.json"}

    try:
        with urlopen(VOICES_JSON, timeout=60) as response:
            catalog = json.load(response)
    except OSError as exc:
        if all((target / name).exists() for name in wanted):
            print(f"WARNING: can't reach huggingface.co ({exc}); keeping existing {voice} unverified.")
            return 0
        print(
            f"ERROR: can't reach huggingface.co ({exc}).\n"
            "In Claude Code on the web, allow huggingface.co and *.hf.co in the environment's "
            f"network settings, or place {voice}.onnx and {voice}.onnx.json in {target} manually.",
            file=sys.stderr,
        )
        return 1

    if voice not in catalog:
        print(f"ERROR: unknown Piper voice {voice!r}. See https://rhasspy.github.io/piper-samples/",
              file=sys.stderr)
        return 1

    for remote_path, expected in catalog[voice]["files"].items():
        name = Path(remote_path).name
        if name not in wanted:
            continue
        dest = target / name
        if is_valid(dest, expected):
            print(f"OK       {name} (verified)")
            continue
        action = "Repairing" if dest.exists() else "Downloading"
        print(f"{action} {name} ({expected['size_bytes'] / 1e6:.1f} MB)")
        try:
            download_verified(BASE_URL + remote_path + "?download=true", dest, expected)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"OK       {name} (verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
