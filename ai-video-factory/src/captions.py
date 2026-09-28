"""Word-timed captions.

Whisper is used only for *timing*. When the script text is known, the caption
words come from the script, so Whisper mishearings and hallucinated trailing
text never reach the screen.
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.config import ConfigError, Settings


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Cue:
    start: float
    end: float
    lines: list[str]
    words: list[Word] = field(default_factory=list)


def _norm(token: str) -> str:
    return re.sub(r"[^a-z0-9]", "", token.lower())


def transcribe_words(audio: Path, settings: Settings, prompt: str | None = None) -> list[Word]:
    if settings["providers"]["transcription"] != "whisper_local":
        raise ConfigError(
            f"providers.transcription={settings['providers']['transcription']!r} is not implemented yet"
        )
    from faster_whisper import WhisperModel

    cfg = settings["transcription"]["whisper_local"]
    model = WhisperModel(
        cfg["model"], device=cfg["device"], compute_type=cfg["compute_type"],
        download_root=str(settings.path("models") / "whisper"),
    )
    segments, _ = model.transcribe(
        str(audio),
        language=settings["project"]["language"],
        word_timestamps=True,
        beam_size=cfg["beam_size"],
        initial_prompt=prompt,
        condition_on_previous_text=False,  # reduces repeated/hallucinated text
        vad_filter=True,
    )
    return [Word(w.word.strip(), w.start, w.end) for s in segments for w in s.words if w.word.strip()]


def align_to_script(script: str, heard: list[Word]) -> list[Word]:
    """Give every script word a time, using Whisper's words as timing anchors."""
    tokens = script.split()
    if not heard:
        raise ValueError("transcription returned no words")
    matcher = difflib.SequenceMatcher(
        a=[_norm(t) for t in tokens], b=[_norm(w.text) for w in heard], autojunk=False
    )
    times: list[tuple[float, float] | None] = [None] * len(tokens)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            w = heard[block.b + k]
            times[block.a + k] = (w.start, w.end)

    if not any(times):
        raise ValueError("script and audio do not match — is this the right voiceover?")

    # Fill unmatched runs (e.g. "thirty" vs "30") by spreading them across the gap.
    audio_end = heard[-1].end
    i = 0
    while i < len(tokens):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tokens) and times[j] is None:
            j += 1
        gap_start = times[i - 1][1] if i > 0 else 0.0
        gap_end = times[j][0] if j < len(tokens) else audio_end
        run = tokens[i:j]
        total = sum(len(t) for t in run) or 1
        cursor = gap_start
        for n, tok in enumerate(run, start=i):
            span = (gap_end - gap_start) * len(tok) / total
            times[n] = (cursor, cursor + span)
            cursor += span
        i = j

    return [Word(t, round(s, 3), round(e, 3)) for t, (s, e) in zip(tokens, times)]


def group_cues(words: list[Word], settings: Settings) -> list[Cue]:
    """Short, punchy cues: break on sentence ends, pauses, and line-length limits."""
    cfg = settings["captions"]
    max_chars, max_lines = cfg["max_chars_per_line"], cfg["max_lines"]
    max_words, pause = cfg["max_words_per_cue"], cfg["break_on_pause_sec"]

    cues: list[Cue] = []
    current: list[Word] = []

    def flush() -> None:
        if not current:
            return
        lines: list[str] = []
        for w in current:
            if lines and len(lines[-1]) + 1 + len(w.text) <= max_chars:
                lines[-1] += " " + w.text
            else:
                lines.append(w.text)
        cues.append(Cue(current[0].start, current[-1].end, lines, list(current)))
        current.clear()

    for w in words:
        if current:
            candidate = " ".join(x.text for x in current + [w])
            too_long = len(candidate) > max_chars * max_lines
            if too_long or len(current) >= max_words or w.start - current[-1].end >= pause:
                flush()
        current.append(w)
        if w.text[-1] in ".!?":
            flush()
    flush()

    # Keep each cue on screen until the next one starts, so sentence pauses never leave a
    # blank screen (a gap of more than 1.5s is a deliberate beat and stays empty).
    for a, b in zip(cues, cues[1:]):
        if b.start - a.end < 1.5:
            a.end = b.start
    return cues


def _ts(seconds: float, sep: str) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(cues: list[Cue]) -> str:
    return "\n".join(
        f"{n}\n{_ts(c.start, ',')} --> {_ts(c.end, ',')}\n" + "\n".join(c.lines) + "\n"
        for n, c in enumerate(cues, start=1)
    )


def to_vtt(cues: list[Cue]) -> str:
    body = "\n".join(
        f"{_ts(c.start, '.')} --> {_ts(c.end, '.')}\n" + "\n".join(c.lines) + "\n" for c in cues
    )
    return "WEBVTT\n\n" + body


def write_captions(slug: str, words: list[Word], cues: list[Cue], settings: Settings) -> list[Path]:
    out_dir = settings.path("captions")
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = settings["captions"]["format"]
    main = out_dir / f"{slug}.{fmt}"
    if fmt == "srt":
        main.write_text(to_srt(cues))
    elif fmt == "vtt":
        main.write_text(to_vtt(cues))
    else:
        raise ConfigError(f"captions.format={fmt!r} is not implemented yet (use srt or vtt)")
    # Word-level timings, for animated word-by-word captions in the render stage.
    words_file = out_dir / f"{slug}.words.json"
    words_file.write_text(json.dumps([asdict(w) for w in words], indent=1))
    return [main, words_file]
