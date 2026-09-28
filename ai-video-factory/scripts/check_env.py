#!/usr/bin/env python3
"""Environment check for the AI Video Factory.

Run from anywhere:
    python3 ai-video-factory/scripts/check_env.py

Exit code 0 = the project foundation works (required checks pass).
Optional tools and API keys are reported but never fail the check,
because no media provider is required yet.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OK, WARN, FAIL = "PASS", "WARN", "FAIL"
results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))


def check_python() -> None:
    v = sys.version_info
    status = OK if v >= (3, 10) else FAIL
    record(status, "Python >= 3.10", f"{v.major}.{v.minor}.{v.micro}")


def check_config():
    try:
        from src.config import load_settings, video_word_budget
    except SystemExit as exc:  # PyYAML missing
        record(FAIL, "Config loader import", str(exc))
        return None
    try:
        settings = load_settings()
    except Exception as exc:
        record(FAIL, "Config loads and validates", str(exc))
        return None
    v = settings["video"]
    lo, hi = video_word_budget(settings)
    record(OK, "Config loads and validates",
           f"{v['width']}x{v['height']} @ {v['fps']}fps, "
           f"{v['min_duration_sec']}-{v['max_duration_sec']}s (~{lo}-{hi} words)")
    return settings


def check_directories(settings) -> None:
    for name in settings["paths"]:
        path = settings.path(name)
        if not path.is_dir():
            record(FAIL, f"Directory {name}/", f"missing: {path.relative_to(ROOT)}")
            continue
        try:
            with tempfile.NamedTemporaryFile(dir=path):
                pass
            record(OK, f"Directory {name}/", str(path.relative_to(ROOT)))
        except OSError as exc:
            record(FAIL, f"Directory {name}/", f"not writable: {exc}")


def check_tools() -> None:
    tools = {
        "ffmpeg": "render/encode video (required later)",
        "ffprobe": "inspect media (required later)",
        "git": "version control",
        "node": "optional JS tooling",
    }
    for tool, purpose in tools.items():
        exe = shutil.which(tool)
        if not exe:
            record(WARN, f"Tool: {tool}", f"not installed — {purpose}")
            continue
        try:
            out = subprocess.run([tool, "-version" if tool.startswith("ff") else "--version"],
                                 capture_output=True, text=True, timeout=10)
            first = (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else ""
        except Exception:
            first = exe
        record(OK, f"Tool: {tool}", first[:70])


def check_ffmpeg_render(settings) -> None:
    """Encode a 1-second silent vertical clip and verify it with ffprobe."""
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        record(WARN, "ffmpeg render test", "skipped — ffmpeg not installed")
        return
    v = settings["video"]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "smoke.mp4"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=black:s={v['width']}x{v['height']}:r={v['fps']}:d=1",
            "-f", "lavfi", "-i", f"anullsrc=r={v['audio_sample_rate']}:cl=stereo",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out),
        ]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if run.returncode != 0 or not out.exists():
            record(FAIL, "ffmpeg render test", run.stderr.strip()[:120] or "no output")
            return
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,codec_name", "-of", "csv=p=0", str(out)],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        expected = f"h264,{v['width']},{v['height']}"
        status = OK if probe == expected else FAIL
        record(status, "ffmpeg render test", f"encoded 1s test clip: {probe} (expected {expected})")


def _tts_smoke_test(settings, label: str, voice: str) -> None:
    from src.tts import synthesize
    with tempfile.TemporaryDirectory() as tmp:
        try:
            secs = synthesize("Environment check.", Path(tmp) / "tts.wav", settings)
            record(OK, label, f"voice {voice} synthesized {secs:.1f}s test audio")
        except Exception as exc:
            record(FAIL, label, str(exc)[:120])


def check_tts(settings) -> None:
    from src.tts import effective_provider, piper_model_path, piper_voice_installed
    provider = settings["providers"]["tts"]
    if provider == "piper":
        import importlib.util
        if importlib.util.find_spec("piper") is None:
            record(FAIL, "TTS: Piper", "providers.tts=piper but piper-tts is not installed")
            return
        model = piper_model_path(settings)
        if piper_voice_installed(settings):
            _tts_smoke_test(settings, "TTS: Piper voice", model.stem)
            return
        record(WARN, "TTS: Piper voice", f"{model.name} missing — run scripts/setup_piper_voice.py")

    active = effective_provider(settings)
    if active == "ffmpeg_flite":
        label = "TTS: ffmpeg flite" + (" (fallback)" if provider != active else "")
        _tts_smoke_test(settings, label, settings["tts"]["ffmpeg_flite"]["voice"])
    elif provider == "piper":
        record(FAIL, "TTS: fallback", "no Piper voice and tts.fallback is none — voiceovers will fail")


def check_captions(settings) -> None:
    """Alignment logic check (no model needed) + whisper model presence."""
    from src.captions import Word, align_to_script, group_cues, to_srt
    heard = [Word("Hello", 0.0, 0.4), Word("world.", 0.5, 0.9), Word("In", 1.2, 1.3),
             Word("30", 1.3, 1.6), Word("seconds.", 1.6, 2.0), Word("extra", 2.1, 2.4)]
    try:
        words = align_to_script("Hello world. In thirty seconds.", heard)
        srt = to_srt(group_cues(words, settings))
        assert [w.text for w in words][3] == "thirty" and "extra" not in srt
        record(OK, "Captions: script alignment", f"{len(words)} words aligned, hallucinated text dropped")
    except Exception as exc:
        record(FAIL, "Captions: script alignment", str(exc)[:120])

    if settings["providers"]["transcription"] == "whisper_local":
        model = settings["transcription"]["whisper_local"]["model"]
        cache = settings.path("models") / "whisper"
        found = any(cache.glob(f"models--*faster-whisper-{model}"))
        record(OK if found else WARN, "Captions: whisper model",
               f"{model} downloaded" if found else f"{model} not downloaded yet (auto-downloads on first use, ~140 MB)")


def check_python_packages() -> None:
    import importlib.util
    packages = {
        "yaml": ("PyYAML", True),
        "requests": ("requests", False),
        "PIL": ("Pillow — on-screen graphics", True),
        "moviepy": ("moviepy — Python video editing", False),
        "piper": ("piper-tts — local text-to-speech", False),
        "faster_whisper": ("faster-whisper — caption timing", False),
    }
    for module, (label, required) in packages.items():
        found = importlib.util.find_spec(module) is not None
        status = OK if found else (FAIL if required else WARN)
        record(status, f"Package: {label}", "installed" if found else "not installed")


def check_providers_and_secrets(settings) -> None:
    from src.config import KNOWN_SECRETS
    active = {k: v for k, v in settings["providers"].items() if v not in ("none", "claude_code")}
    record(OK, "Providers", ", ".join(f"{k}={v}" for k, v in active.items()) or
           "all media providers set to 'none' (safe default)")
    for key in KNOWN_SECRETS:
        record(OK if settings.has_secret(key) else WARN, f"Secret: {key}",
               "set" if settings.has_secret(key) else "not set (fine until that provider is enabled)")
    if settings["publishing"]["auto_publish"]:
        record(WARN, "Publishing", "auto_publish is ON — make sure this is intended")


def main() -> int:
    check_python()
    settings = check_config()
    if settings:
        check_directories(settings)
        check_providers_and_secrets(settings)
    check_tools()
    check_python_packages()
    if settings:
        check_ffmpeg_render(settings)
        check_tts(settings)
        check_captions(settings)

    width = max(len(n) for _, n, _ in results)
    print(f"\nAI Video Factory — environment check ({ROOT})\n")
    for status, name, detail in results:
        print(f"  [{status}] {name.ljust(width)}  {detail}")

    fails = sum(s == FAIL for s, _, _ in results)
    warns = sum(s == WARN for s, _, _ in results)
    print(f"\n{len(results) - fails - warns} passed, {warns} warnings, {fails} failed")
    print("RESULT:", "READY (foundation OK)" if not fails else "NOT READY")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
