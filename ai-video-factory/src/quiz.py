"""Quiz / challenge videos: question cards, 3-second countdown, answer reveal.

Spec (YAML, scripts/<slug>.quiz.yaml):

    title: "CAN YOU PASS THIS 5-QUESTION CHALLENGE?"
    hook: {narration: "...", scene: "classroom students exam"}
    questions:
      - narration: "Question one! What is the largest planet in our solar system?"
        question: "What is the largest planet in our solar system?"
        options: ["Earth", "Jupiter", "Mars"]
        answer: 1                      # index into options
        reveal: "Correct answer: Jupiter!"
        scene: "student thinking exam"
        reveal_scene: "jupiter planet" # optional footage for the reveal
    ending: {narration: "...", scene: "students celebrating classroom"}

Timeline per question: narration -> 3 s countdown (ticks) -> reveal narration (ding).
Only the exact question text and options are drawn on screen, plus the countdown timer.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from src.config import Settings
from src.render import audio_duration, build_footage_background, pick_palette
from src.stock import Scene, download, is_safe, pick_file, relevance, search
from src.tts import synthesize
from src.visuals import _emoji, _font, _rgb, _wrap

COUNTDOWN = 3.0
GAP = 0.35
CARD_W, CARD_H = 960, 980
OPTION_LETTERS = "ABC"


@dataclass
class Segment:
    kind: str            # hook | question | countdown | reveal | ending
    start: float
    end: float
    q: int = -1          # question index
    audio: Path | None = None


# ---------------------------------------------------------------- graphics

def draw_card(q: dict, number: int, total: int, accent: str, reveal: bool) -> Image.Image:
    acc = _rgb(accent)
    good = (46, 204, 113)
    img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, CARD_W - 1, CARD_H - 1), radius=48,
                        fill=(12, 14, 24, 215), outline=(255, 255, 255, 70), width=3)
    d.rounded_rectangle((60, 0, CARD_W - 60, 10), radius=5, fill=acc + (255,))

    # Always show the full question: shrink the font until it fits in 4 lines.
    for size in (62, 56, 50, 46):
        qf = _font(size)
        lines = _wrap(d, q["question"], qf, CARD_W - 120)
        if len(lines) <= 4:
            break
    if len(lines) > 4:
        raise ValueError(f"question too long for the card: {q['question']!r}")
    y = 70
    for line in lines:
        w = d.textlength(line, font=qf)
        d.text(((CARD_W - w) / 2, y), line, font=qf, fill=(255, 255, 255))
        y += qf.size + 14

    of, lf = _font(58), _font(58)
    top = max(y + 50, CARD_H - 3 * 170 - 40)
    for i, opt in enumerate(q["options"]):
        oy = top + i * 170
        correct = reveal and i == q["answer"]
        dimmed = reveal and not correct
        fill = good + (255,) if correct else (255, 255, 255, 26 if dimmed else 40)
        d.rounded_rectangle((60, oy, CARD_W - 60, oy + 140), radius=70, fill=fill,
                            outline=(255, 255, 255, 40 if dimmed else 110), width=3)
        badge = (255, 255, 255) if correct else acc
        d.ellipse((80, oy + 15, 190, oy + 125), fill=badge + (255,))
        letter = OPTION_LETTERS[i]
        lw = d.textlength(letter, font=lf)
        d.text((135 - lw / 2, oy + 30), letter, font=lf,
               fill=(20, 110, 60) if correct else (20, 20, 30))
        text_color = (255, 255, 255, 110) if dimmed else (255, 255, 255, 255)
        d.text((225, oy + 36), str(opt), font=of, fill=text_color)
        if correct:
            img.alpha_composite(_emoji("✅", 96), (CARD_W - 190, oy + 22))
    return img


def draw_timer(n: int, accent: str) -> Image.Image:
    size = 300
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((10, 10, size - 10, size - 10), fill=(12, 14, 24, 220))
    d.arc((10, 10, size - 10, size - 10), start=-90, end=-90 + 360 * n / COUNTDOWN,
          fill=_rgb(accent) + (255,), width=26)
    f = _font(150)
    w = d.textlength(str(n), font=f)
    d.text(((size - w) / 2, 52), str(n), font=f, fill=(255, 255, 255))
    return img


# ------------------------------------------------------------------- audio

def _tone(path: Path, expr: str, dur: float, rate: int) -> Path:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"aevalsrc='{expr}':s={rate}:d={dur}", "-ac", "1", str(path)], check=True)
    return path


def make_sfx(tmp: Path, rate: int) -> dict[str, Path]:
    return {
        # short wood-block style tick
        "tick": _tone(tmp / "tick.wav", "0.5*sin(2*PI*1500*t)*exp(-60*t)", 0.12, rate),
        # two-note "correct" chime
        "ding": _tone(tmp / "ding.wav",
                      "0.35*(sin(2*PI*1046*t)*exp(-6*t)+if(gt(t,0.12),sin(2*PI*1568*(t-0.12))*exp(-6*(t-0.12)),0))",
                      0.9, rate),
        # filtered-noise whoosh for transitions
        "whoosh": _tone(tmp / "whoosh.wav",
                        "0.25*(random(0)*2-1)*sin(PI*t/0.45)", 0.45, rate),
    }


def make_music(tmp: Path, duration: float, rate: int, music_dir: Path) -> Path:
    """Use a licensed track from music/ if present; otherwise a simple 120 BPM pulse bed."""
    tracks = sorted([*music_dir.glob("*.mp3"), *music_dir.glob("*.wav")])
    out = tmp / "music.wav"
    if tracks:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(tracks[0]),
                        "-t", str(duration), "-ar", str(rate), "-ac", "1", str(out)], check=True)
        return out
    beat = 0.5  # 120 BPM
    expr = (f"0.55*sin(2*PI*55*t)*exp(-18*mod(t,{beat}))"              # kick
            f"+0.12*(random(0)*2-1)*exp(-40*mod(t+{beat/2},{beat}))"   # off-beat hat
            f"+0.10*sin(2*PI*110*t)*(0.5+0.5*sin(2*PI*t/8))")          # slow bass swell
    return _tone(out, expr, duration, rate)


# -------------------------------------------------------------------- build

def build_timeline(spec: dict, tmp: Path, settings: Settings) -> list[Segment]:
    segs: list[Segment] = []
    t = 0.0

    def say(kind: str, text: str, q: int = -1) -> None:
        nonlocal t
        path = tmp / f"{len(segs):02d}_{kind}.wav"
        dur = synthesize(text, path, settings)
        segs.append(Segment(kind, round(t, 3), round(t + dur, 3), q, path))
        t += dur + GAP

    say("hook", spec["hook"]["narration"])
    for i, q in enumerate(spec["questions"]):
        say("question", q["narration"], i)
        segs.append(Segment("countdown", round(t, 3), round(t + COUNTDOWN, 3), i))
        t += COUNTDOWN
        say("reveal", q["reveal"], i)
    say("ending", spec["ending"]["narration"])
    segs[-1].end = round(segs[-1].end + 0.8, 3)
    return segs


def mix_audio(segs: list[Segment], tmp: Path, duration: float, settings: Settings) -> Path:
    v = settings["video"]
    rate = 22050
    sfx = make_sfx(tmp, rate)
    music = make_music(tmp, duration, rate, settings.path("music"))
    inputs, parts = [], []

    def add(path: Path, at: float, vol: float) -> None:
        idx = len(inputs) // 2
        inputs.extend(["-i", str(path)])
        parts.append(f"[{idx}:a]aresample={rate},volume={vol},adelay={int(at * 1000)}:all=1[a{idx}]")

    # voice
    for s in segs:
        if s.audio:
            add(s.audio, s.start, 1.0)
    # sfx: whoosh into each question, ticks during countdown, ding on reveal
    for s in segs:
        if s.kind == "question":
            add(sfx["whoosh"], max(0.0, s.start - 0.3), 0.8)
        if s.kind == "countdown":
            for k in range(int(COUNTDOWN)):
                add(sfx["tick"], s.start + k, 0.9)
        if s.kind == "reveal":
            add(sfx["ding"], s.start, 0.9)
    n_before_music = len(inputs) // 2
    inputs.extend(["-i", str(music)])
    # duck the music a little under the voice (sidechain on the summed voice track)
    labels = "".join(f"[a{i}]" for i in range(n_before_music))
    graph = ";".join(parts) + (
        f";{labels}amix=inputs={n_before_music}:normalize=0[fg]"
        f";[{n_before_music}:a]aresample={rate},volume=0.22[bg]"
        f";[fg][bg]amix=inputs=2:normalize=0,"
        f"loudnorm=I={v['target_loudness_lufs']}:TP=-1.5:LRA=11,aresample={v['audio_sample_rate']}[out]"
    )
    out = tmp / "mix.wav"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for i in range(0, len(inputs), 2):
        cmd += inputs[i:i + 2]
    cmd += ["-filter_complex", graph, "-map", "[out]", "-t", str(duration), "-ac", "2", str(out)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out


def fetch_clip(query: str, used: set, settings: Settings, min_dur: float) -> tuple[Path, dict]:
    key = settings.secrets["PEXELS_API_KEY"]
    cands = [v for v in search(query, key) if v["id"] not in used and pick_file(v)
             and v.get("duration", 0) >= min_dur and is_safe(v)]
    if not cands:
        raise ValueError(f"no clips for {query!r}")
    video = max(cands, key=lambda v: (relevance(query, v), -cands.index(v)))
    used.add(video["id"])
    r = pick_file(video)
    cache = settings.path("video") / "pexels"
    cache.mkdir(parents=True, exist_ok=True)
    clip = download(r["link"], cache / f"{video['id']}_{r['height']}.mp4")
    return clip, {"pexels_id": video["id"], "url": video.get("url"),
                  "author": video.get("user", {}).get("name"), "query": query}


def photo_clip(photo_id: int, duration: float, settings: Settings) -> tuple[Path, dict]:
    """Pexels photo -> slow push-in vertical clip (needs images.pexels.com network access)."""
    from src.stock import _request_json
    key = settings.secrets["PEXELS_API_KEY"]
    photo = _request_json(f"https://api.pexels.com/v1/photos/{photo_id}", key)
    cache = settings.path("images") / "pexels"
    cache.mkdir(parents=True, exist_ok=True)
    img = download(photo["src"]["original"] + "?auto=compress&cs=tinysrgb&h=2400", cache / f"{photo_id}.jpg")
    v = settings["video"]
    frames = int(duration * v["fps"]) + 2
    out = cache / f"{photo_id}_{frames}.mp4"
    if not out.exists():
        vf = (f"scale=-2:2200,crop=1238:2200,"
              f"zoompan=z='min(zoom+0.0009,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={v['width']}x{v['height']}:fps={v['fps']}")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(img), "-vf", vf,
                        "-frames:v", str(frames), "-pix_fmt", "yuv420p", "-c:v", "libx264", str(out)],
                       check=True)
    return out, {"pexels_photo_id": photo_id, "url": photo.get("url"),
                 "author": photo.get("photographer"), "query": f"photo {photo_id}"}


def render_quiz(slug: str, spec: dict, settings: Settings) -> tuple[Path, list[dict]]:
    v = settings["video"]
    out_dir = settings.path("output")
    work = out_dir / f"{slug}_quiz"
    work.mkdir(parents=True, exist_ok=True)
    _, accent = pick_palette(slug)

    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        segs = build_timeline(spec, tmp, settings)
        duration = round(segs[-1].end, 2)
        audio = mix_audio(segs, tmp, duration, settings)
        final_audio = work / "mix.wav"
        final_audio.write_bytes(audio.read_bytes())

    # footage: one clip per block (hook, each question [+ reveal], ending)
    used: set = set()
    scenes, credits = [], []

    def add_scene(query: str, start: float, end: float) -> None:
        clip, credit = fetch_clip(query, used, settings, 3)
        scenes.append(Scene(clip, round(start, 2), round(end, 2), credit))
        credits.append(credit | {"start": round(start, 2), "end": round(end, 2)})

    q_blocks = {}
    for s in segs:
        if s.q >= 0:
            b = q_blocks.setdefault(s.q, [s.start, s.end, None])
            b[1] = s.end
            if s.kind == "reveal":
                b[2] = s.start
    hook_end = q_blocks[0][0]
    add_scene(spec["hook"]["scene"], 0.0, hook_end)
    qs = spec["questions"]
    for i, q in enumerate(qs):
        start, end, reveal_at = q_blocks[i]
        end = q_blocks[i + 1][0] if i + 1 < len(qs) else end + GAP
        reveal_clip = None
        if q.get("reveal_photo"):
            try:
                reveal_clip = photo_clip(int(q["reveal_photo"]), end - reveal_at, settings)
            except Exception as exc:  # e.g. images.pexels.com not network-allowed
                print(f"WARNING: reveal photo unavailable ({exc}); keeping the question scene",
                      file=sys.stderr)
        if reveal_clip:
            add_scene(q["scene"], start, reveal_at)
            clip, credit = reveal_clip
            scenes.append(Scene(clip, round(reveal_at, 2), round(end, 2), credit))
            credits.append(credit | {"start": round(reveal_at, 2), "end": round(end, 2)})
        elif q.get("reveal_scene"):
            add_scene(q["scene"], start, reveal_at)
            add_scene(q["reveal_scene"], reveal_at, end)
        else:
            add_scene(q["scene"], start, end)
    add_scene(spec["ending"]["scene"], scenes[-1].end, duration)
    background = build_footage_background(scenes, duration, settings, work / "bg.mp4")

    # overlays: question card (question+countdown), reveal card, countdown timer digits
    overlays: list[tuple[Path, float, float, int]] = []   # png, start, end, y
    card_y, timer_y = 300, 1330
    for i, q in enumerate(qs):
        start, end, reveal_at = q_blocks[i]
        end = q_blocks[i + 1][0] - 0.05 if i + 1 < len(qs) else end + GAP
        qp = work / f"q{i + 1}.png"
        rp = work / f"q{i + 1}_reveal.png"
        draw_card(q, i + 1, len(qs), accent, reveal=False).save(qp)
        draw_card(q, i + 1, len(qs), accent, reveal=True).save(rp)
        overlays.append((qp, start, reveal_at, card_y))
        overlays.append((rp, reveal_at, end, card_y))
        cd = next(s for s in segs if s.kind == "countdown" and s.q == i)
        for k in range(int(COUNTDOWN)):
            n = int(COUNTDOWN) - k
            tp = work / f"timer{n}.png"
            if not tp.exists():
                draw_timer(n, accent).save(tp)
            overlays.append((tp, cd.start + k, cd.start + k + 1, timer_y))

    inputs = ["-i", str(background), "-i", str(final_audio)]
    chains = ["[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.28:t=fill,vignette=PI/4[b0]"]
    last = "b0"
    for k, (png, s0, s1, y) in enumerate(overlays):
        inputs += ["-loop", "1", "-t", str(duration), "-i", str(png)]
        idx = k + 2
        chains.append(f"[{idx}:v]format=rgba,fade=t=in:st={s0}:d=0.2:alpha=1[g{k}]")
        chains.append(f"[{last}][g{k}]overlay=x=(W-w)/2:y='{y}+40*max(0,1-(t-{s0})/0.25)'"
                      f":enable='between(t,{s0},{s1})'[o{k}]")
        last = f"o{k}"
    out = out_dir / f"{slug}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs,
           "-filter_complex", ";".join(chains), "-map", f"[{last}]", "-map", "1:a",
           "-t", str(duration), "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-r", str(v["fps"]), "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", str(out)]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode != 0:
        raise RuntimeError(f"quiz render failed: {run.stderr.strip()[-500:]}")
    return out, credits
