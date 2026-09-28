"""Text-to-speech. Free, local engines only: ffmpeg's built-in Flite and Piper."""

from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

from src.config import ConfigError, Settings


# Where scripts/setup_env.sh puts voices when run outside the repo (e.g. as a
# Claude Code on the web setup script, before the clone exists).
SHARED_VOICE_DIR = Path.home() / ".local" / "share" / "piper-voices"


def piper_model_path(settings: Settings) -> Path:
    voice = settings["tts"]["piper"]["voice"]
    project = settings.path("models") / "piper" / f"{voice}.onnx"
    shared = SHARED_VOICE_DIR / f"{voice}.onnx"
    return shared if not project.exists() and shared.exists() else project


def piper_voice_installed(settings: Settings) -> bool:
    model = piper_model_path(settings)
    return model.exists() and model.with_suffix(".onnx.json").exists()


def synthesize(text: str, out_path: Path, settings: Settings) -> float:
    """Render `text` to a WAV file. Returns the audio duration in seconds."""
    provider = settings["providers"]["tts"]
    if not text.strip():
        raise ValueError("text is empty")
    if provider == "ffmpeg_flite":
        return _synthesize_flite(text, out_path, settings)
    if provider != "piper":
        raise ConfigError(f"providers.tts={provider!r} is not implemented yet")

    from piper import PiperVoice, SynthesisConfig

    model = piper_model_path(settings)
    if not piper_voice_installed(settings):
        raise ConfigError(
            f"Piper voice not found at {model}. "
            "Run: python3 scripts/setup_piper_voice.py"
        )

    cfg = settings["tts"]["piper"]
    voice = PiperVoice.load(model)
    syn = SynthesisConfig(length_scale=cfg["length_scale"], volume=cfg["volume"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    silence = int(voice.config.sample_rate * cfg["sentence_silence"]) * b"\x00\x00"
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(voice.config.sample_rate)
        for chunk in voice.synthesize(text, syn_config=syn):  # one chunk per sentence
            wav.writeframes(chunk.audio_int16_bytes)
            wav.writeframes(silence)

    with wave.open(str(out_path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def _synthesize_flite(text: str, out_path: Path, settings: Settings) -> float:
    """Use ffmpeg's libflite filter. Text goes via a file to avoid filtergraph escaping."""
    voice = settings["tts"]["ffmpeg_flite"]["voice"]
    rate = settings["video"]["audio_sample_rate"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        text_file = Path(tmp) / "text.txt"
        text_file.write_text(" ".join(text.split()))
        run = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-f", "lavfi", "-i", f"flite=textfile={text_file}:voice={voice}",
             "-ar", str(rate), "-ac", "1", str(out_path)],
            capture_output=True, text=True,
        )
    if run.returncode != 0:
        raise ConfigError(f"ffmpeg flite failed: {run.stderr.strip()[:200]}")
    with wave.open(str(out_path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()
