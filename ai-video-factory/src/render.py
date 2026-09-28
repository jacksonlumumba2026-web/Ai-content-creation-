"""Render a finished vertical video with ffmpeg.

Layers (bottom to top):
  animated gradient background (palette picked per video) + vignette + light grain
  headline card near the top (script front matter `title`)
  word-by-word captions: the spoken word is highlighted in the accent colour
  channel handle, progress bar along the bottom
Audio: the voiceover, loudness-normalised to the configured LUFS target.
"""

from __future__ import annotations

import hashlib
import subprocess
import textwrap
import wave
from pathlib import Path

from src.captions import Cue, Word
from src.visuals import build_beats
from src.config import ConfigError, Settings

# (three gradient colours, accent) — dark, high-contrast palettes that keep white text readable.
PALETTES = [
    (("0f0c29", "302b63", "24243e"), "FFD700"),  # midnight / gold
    (("02111b", "0b3d2e", "1d6f5f"), "7CFFB2"),  # emerald / mint
    (("1a0a0a", "5c1a1a", "2b1055"), "FFB347"),  # ember / amber
    (("000428", "004e92", "0a1931"), "5CE1E6"),  # ocean / cyan
    (("141e30", "243b55", "0f2027"), "FF4D6D"),  # graphite / coral
]

TAIL_SEC = 0.6  # breathing room after the last word
VISUAL_TOP = 0.235  # graphics card top edge, as a fraction of video height
HANDLE_Y = 0.765   # channel handle, below the captions and above platform UI


def pick_palette(slug: str) -> tuple[tuple[str, str, str], str]:
    index = int(hashlib.sha256(slug.encode()).hexdigest(), 16) % len(PALETTES)
    return PALETTES[index]


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def _ass_color(hex_rgb: str, alpha: str = "00") -> str:
    r, g, b = hex_rgb[0:2], hex_rgb[2:4], hex_rgb[4:6]
    return f"&H{alpha}{b}{g}{r}".upper()


def _ass_text(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def _ass_time(seconds: float) -> str:
    cs = int(round(max(seconds, 0) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass(cues: list[Cue], title: str, handle: str, accent: str,
              settings: Settings, duration: float) -> str:
    v, c = settings["video"], settings["captions"]
    w, h = v["width"], v["height"]
    font = c["font"]
    upper = c.get("uppercase", False)
    hl = _ass_color(accent)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},{c['font_size']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,7,4,5,60,60,0,1
Style: Title,{font},66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,4,8,80,80,0,1
Style: Handle,{font},38,&H40FFFFFF,&H40FFFFFF,&H80000000,&H00000000,-1,0,0,0,100,100,1,0,1,2,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    end_all = _ass_time(duration)

    if title:
        # Headline must fit in 2 lines above the graphics card: shrink long titles to fit.
        size, lines = 66, textwrap.wrap(_ass_text(title), width=22)
        if len(lines) > 2:
            size, lines = 52, textwrap.wrap(_ass_text(title), width=28)
        wrapped = r"\N".join(lines[:2])
        events.append(f"Dialogue: 1,{_ass_time(0)},{end_all},Title,,0,0,0,,"
                      rf"{{\pos({w // 2},{int(h * 0.14)})\fs{size}\fad(250,0)}}{wrapped}")
    if handle:
        events.append(f"Dialogue: 1,{_ass_time(0)},{end_all},Handle,,0,0,0,,"
                      rf"{{\pos({w // 2},{int(h * HANDLE_Y)})}}{_ass_text(handle)}")

    y = c["position_y"]
    for cue in cues:
        words = cue.words or [Word(t, cue.start, cue.end) for t in " ".join(cue.lines).split()]
        # Rebuild line breaks from cue.lines so highlighting keeps the same layout.
        breaks, count = set(), 0
        for line in cue.lines[:-1]:
            count += len(line.split())
            breaks.add(count)
        for i, current in enumerate(words):
            start = cue.start if i == 0 else current.start
            end = words[i + 1].start if i + 1 < len(words) else cue.end
            if end <= start:
                continue
            parts = []
            for j, word in enumerate(words):
                text = _ass_text(word.text.upper() if upper else word.text)
                if j == i:
                    text = rf"{{\c{hl}&\fscx108\fscy108}}{text}{{\c&H00FFFFFF&\fscx100\fscy100}}"
                parts.append((r"\N" if j in breaks else " " if j else "") + text)
            events.append(f"Dialogue: 2,{_ass_time(start)},{_ass_time(end)},Caption,,0,0,0,,"
                          rf"{{\pos({w // 2},{y})}}" + "".join(parts))
    return header + "\n".join(events) + "\n"


def render_video(slug: str, cues: list[Cue], title: str, settings: Settings,
                 visuals: list | None = None, words: list[Word] | None = None) -> Path:
    v = settings["video"]
    voice = settings.path("voiceovers") / f"{slug}.wav"
    if not voice.exists():
        raise ConfigError(f"missing voiceover {voice}")
    duration = round(audio_duration(voice) + TAIL_SEC, 2)

    (c0, c1, c2), accent = pick_palette(slug)
    handle = settings.get("branding", {}).get("handle", "")
    out_dir = settings.path("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    ass_path = out_dir / f"{slug}.ass"
    ass_path.write_text(build_ass(cues, title, handle, accent, settings, duration))
    out = out_dir / f"{slug}.mp4"

    beats = []
    if visuals:
        beats, problems = build_beats(visuals, words or [], accent, out_dir / f"{slug}_visuals", duration)
        if problems:
            raise ValueError("visuals: " + "; ".join(problems))

    background = (
        f"gradients=s={v['width']}x{v['height']}:r={v['fps']}:d={duration}"
        f":c0=0x{c0}:c1=0x{c1}:c2=0x{c2}:n=3:speed=0.012:seed={len(slug)}"
    )
    # Graphics: slide up + fade in when their phrase is spoken, fade out before the next one.
    card_y = int(v["height"] * VISUAL_TOP)
    chains, last = [f"[0:v]vignette=PI/5,noise=alls=3:allf=t[bg]"], "bg"
    for k, beat in enumerate(beats):
        idx, s0, s1 = k + 2, beat.start, beat.end
        chains.append(
            f"[{idx}:v]format=rgba,fade=t=in:st={s0}:d=0.3:alpha=1,"
            f"fade=t=out:st={max(s0, s1 - 0.25)}:d=0.25:alpha=1[g{k}]"
        )
        chains.append(
            f"[{last}][g{k}]overlay=x=(W-w)/2:y='{card_y}+70*max(0,1-(t-{s0})/0.35)'"
            f":enable='between(t,{s0},{s1})'[o{k}]"
        )
        last = f"o{k}"
    chains.append(
        f"[{last}]drawbox=x=0:y=ih-14:w='iw*t/{duration}':h=14:color=0x{accent}@0.95:t=fill,"
        f"ass={ass_path}[v]"
    )
    video_chain = ";".join(chains)
    audio_chain = (
        f"[1:a]loudnorm=I={v['target_loudness_lufs']}:TP=-1.5:LRA=11,"
        f"aresample={v['audio_sample_rate']},apad=pad_dur={TAIL_SEC}[a]"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", background,
        "-i", str(voice),
        *[arg for beat in beats for arg in ("-loop", "1", "-t", str(duration), "-i", str(beat.image))],
        "-filter_complex", f"{video_chain};{audio_chain}",
        "-map", "[v]", "-map", "[a]", "-t", str(duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
        "-r", str(v["fps"]), "-c:a", "aac", "-b:a", "192k", "-ar", str(v["audio_sample_rate"]),
        "-movflags", "+faststart", str(out),
    ]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode != 0:
        raise RuntimeError(f"ffmpeg render failed: {run.stderr.strip()[-400:]}")
    return out


def probe(path: Path) -> dict:
    """Return width, height, codec, duration and size of a rendered file."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,codec_name:format=duration,size",
         "-of", "default=nw=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    info = dict(line.split("=", 1) for line in out.strip().splitlines())
    return {
        "width": int(info["width"]), "height": int(info["height"]), "codec": info["codec_name"],
        "duration": float(info["duration"]), "size_mb": int(info["size"]) / 1e6,
    }
