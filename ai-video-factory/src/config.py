"""Configuration loader.

Precedence (later wins):
    1. config/settings.yaml        committed defaults
    2. config/settings.local.yaml  personal overrides (git-ignored)
    3. config/.env                 secrets + AVF__ overrides (git-ignored)
    4. process environment         e.g. secrets set in Claude Code / GitHub Actions

Settings overrides use the form AVF__SECTION__KEY=value, e.g. AVF__VIDEO__FPS=60.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install -r requirements.txt") from exc

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
ENV_PREFIX = "AVF__"

# API keys the pipeline may use. Presence is reported, values are never printed.
KNOWN_SECRETS = (
    "ELEVENLABS_API_KEY",
    "PEXELS_API_KEY",
    "PIXABAY_API_KEY",
    "METRICOOL_API_TOKEN",
    "OPUSCLIP_API_KEY",
)

VALID_PROVIDERS = {
    "llm": {"claude_code"},
    "tts": {"none", "ffmpeg_flite", "piper", "edge_tts", "elevenlabs"},
    "images": {"none", "stock_pexels", "canva", "elevenlabs"},
    "stock_video": {"none", "pexels", "pixabay"},
    "music": {"none", "local_library"},
    "transcription": {"none", "whisper_local", "elevenlabs"},
    "render": {"none", "ffmpeg", "moviepy", "descript"},
    "publish": {"none", "manual", "metricool", "opusclip"},
}


class ConfigError(ValueError):
    pass


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping")
    return data


def _read_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser (KEY=value, # comments). No external dependency."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _apply_env_overrides(settings: dict, env: dict[str, str]) -> dict:
    for key, raw in env.items():
        if not key.startswith(ENV_PREFIX) or not raw:
            continue
        parts = [p.lower() for p in key[len(ENV_PREFIX):].split("__") if p]
        node = settings
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = yaml.safe_load(raw)  # "60" -> 60, "true" -> True
    return settings


def validate(settings: dict) -> list[str]:
    """Return a list of problems (empty list = valid)."""
    errors: list[str] = []
    video = settings.get("video", {})
    for field in ("width", "height", "fps", "min_duration_sec", "max_duration_sec"):
        if not isinstance(video.get(field), int) or video[field] <= 0:
            errors.append(f"video.{field} must be a positive integer")
    if not errors:
        if video["height"] <= video["width"]:
            errors.append("video must be vertical (height > width)")
        if video["min_duration_sec"] > video["max_duration_sec"]:
            errors.append("video.min_duration_sec must be <= max_duration_sec")

    providers = settings.get("providers", {})
    for role, allowed in VALID_PROVIDERS.items():
        value = providers.get(role)
        if value not in allowed:
            errors.append(f"providers.{role}={value!r} not in {sorted(allowed)}")

    for name, rel in settings.get("paths", {}).items():
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            errors.append(f"paths.{name} must be relative and inside the project")
    return errors


class Settings(dict):
    """Dict of settings plus helpers for paths and secrets."""

    secrets: dict[str, str]

    def path(self, name: str) -> Path:
        return ROOT / self["paths"][name]

    def has_secret(self, name: str) -> bool:
        return bool(self.secrets.get(name))

    def secret(self, name: str) -> str:
        value = self.secrets.get(name)
        if not value:
            raise ConfigError(f"{name} is not set (see config/.env.example)")
        return value


def load_settings(config_dir: Path = CONFIG_DIR) -> Settings:
    settings = _load_yaml(config_dir / "settings.yaml")
    if not settings:
        raise ConfigError(f"missing or empty {config_dir / 'settings.yaml'}")
    settings = _deep_merge(settings, _load_yaml(config_dir / "settings.local.yaml"))

    env = {**_read_dotenv(config_dir / ".env"), **os.environ}
    settings = _apply_env_overrides(settings, env)

    errors = validate(settings)
    if errors:
        raise ConfigError("invalid configuration:\n  - " + "\n  - ".join(errors))

    result = Settings(settings)
    result.secrets = {k: env[k] for k in KNOWN_SECRETS if env.get(k)}
    return result


def video_word_budget(settings: dict[str, Any]) -> tuple[int, int]:
    """Min/max narration words that fit the configured duration."""
    wpm = settings["script"]["words_per_minute"]
    v = settings["video"]
    return (v["min_duration_sec"] * wpm // 60, v["max_duration_sec"] * wpm // 60)
