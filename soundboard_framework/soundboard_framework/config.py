"""Character configuration: loads character.toml into a Character dataclass."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_THEME: dict[str, str] = {
    "abyss": "#0a0f12",
    "mist": "#101a1e",
    "mist_raised": "#16242a",
    "edge": "#1e3038",
    "glow": "#35e0b8",
    "glow_soft": "rgba(53, 224, 184, 0.18)",
    "bone": "#dce8e4",
    "muted": "#7d9691",
    "danger": "#e06060",
    "font_display": '"Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif',
}

REQUIRED_FIELDS = ("character.name", "audio.fade_in_ms", "audio.fade_out_ms")


class CharacterConfigError(Exception):
    """Raised when character.toml is missing or invalid."""


@dataclass(frozen=True)
class Character:
    dir: Path
    name: str
    short_name: str
    description: str
    filename_prefix_to_strip: str
    fade_in_ms: int
    fade_out_ms: int
    language_independent_categories: frozenset[str]
    category_order: tuple[str, ...]
    category_labels: dict[str, str] = field(default_factory=dict)
    theme: dict[str, str] = field(default_factory=dict)
    voice_scraper_url: str | None = None
    voice_scraper_category_map: dict[str, str] = field(default_factory=dict)


def _get(data: dict, dotted_path: str):
    node = data
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def load_character(character_dir: Path) -> Character:
    character_dir = Path(character_dir)
    toml_path = character_dir / "character.toml"
    if not toml_path.is_file():
        raise CharacterConfigError(f"character.toml not found in {character_dir}")

    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise CharacterConfigError(f"character.toml is not valid TOML: {exc}") from exc

    missing = [f for f in REQUIRED_FIELDS if _get(data, f) is None]
    if missing:
        raise CharacterConfigError(
            f"character.toml is missing required field(s): {', '.join(missing)}"
        )

    character_section = data.get("character", {})
    audio_section = data.get("audio", {})
    categories_section = data.get("categories", {})
    theme_section = data.get("theme", {})
    scraper_section = data.get("voice_scraper", {})

    name = character_section["name"]
    theme = {**DEFAULT_THEME, **theme_section}

    return Character(
        dir=character_dir,
        name=name,
        short_name=character_section.get("short_name", name),
        description=character_section.get("description", ""),
        filename_prefix_to_strip=character_section.get("filename_prefix_to_strip", ""),
        fade_in_ms=audio_section["fade_in_ms"],
        fade_out_ms=audio_section["fade_out_ms"],
        language_independent_categories=frozenset(
            audio_section.get("language_independent_categories", [])
        ),
        category_order=tuple(categories_section.get("order", [])),
        category_labels=dict(categories_section.get("labels", {})),
        theme=theme,
        voice_scraper_url=scraper_section.get("url"),
        voice_scraper_category_map=dict(scraper_section.get("category_map", {})),
    )
