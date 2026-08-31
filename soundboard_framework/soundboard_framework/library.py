"""Sound library.

Scans a character's sounds directory once, merges in the metadata file and
caches durations, so requests never touch the filesystem or re-parse audio
files. Playback lookups go through the catalog, which also prevents any
path-traversal via user input: only known, indexed files can be played.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import soundfile as sf

from soundboard_framework.config import Character

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Sound:
    key: str            # unique id: "<language>/<category>/<filename>"
    language: str       # "en", "de", ... or "-" for shared categories
    category: str
    filename: str       # without extension
    title: str
    description: str
    duration: float     # seconds
    path: str = field(repr=False)  # absolute path on disk

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "language": self.language,
            "category": self.category,
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
            "duration": round(self.duration, 2),
        }


class Library:
    def __init__(self, character: Character, sounds_dir: Path, metadata_path: Path) -> None:
        self.character = character
        self.sounds_dir = Path(sounds_dir)
        self.metadata_path = Path(metadata_path)
        self.sounds: dict[str, Sound] = {}
        self.languages: list[str] = []
        self.categories: list[str] = []
        self._metadata: dict = {}

    # -- public API ---------------------------------------------------------

    def load(self) -> None:
        """(Re)scan the sounds directory and metadata file."""
        self._metadata = self._read_metadata()
        self.sounds.clear()

        languages: set[str] = set()
        categories: set[str] = set()

        if not self.sounds_dir.is_dir():
            log.error("Sounds directory not found: %s", self.sounds_dir)
            return

        for entry in sorted(os.listdir(self.sounds_dir)):
            entry_path = self.sounds_dir / entry
            if not entry_path.is_dir():
                continue

            if entry in self.character.language_independent_categories:
                categories.add(entry)
                self._index_folder(entry_path, language="-", category=entry)
            else:
                languages.add(entry)
                for category in sorted(os.listdir(entry_path)):
                    category_path = entry_path / category
                    if not category_path.is_dir():
                        continue
                    categories.add(category)
                    self._index_folder(category_path, language=entry, category=category)

        self.languages = sorted(languages)
        self.categories = self._order_categories(categories)
        log.info(
            "Library loaded: %d sounds, languages=%s, categories=%s",
            len(self.sounds), self.languages, self.categories,
        )

    def get(self, key: str) -> Sound | None:
        return self.sounds.get(key)

    def catalog(self) -> dict:
        """Full catalog for the frontend, fetched once on page load."""
        return {
            "languages": self.languages,
            "categories": [
                {
                    "id": c,
                    "label": self.character.category_labels.get(c, c.replace("_", " ").title()),
                    "shared": c in self.character.language_independent_categories,
                }
                for c in self.categories
            ],
            "sounds": [s.to_dict() for s in self.sounds.values()],
        }

    # -- internals ----------------------------------------------------------

    def _read_metadata(self) -> dict:
        try:
            with open(self.metadata_path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            log.warning("Metadata file not found: %s", self.metadata_path)
        except json.JSONDecodeError as exc:
            log.error("Metadata file is not valid JSON: %s", exc)
        return {}

    def _index_folder(self, folder: Path, language: str, category: str) -> None:
        for filename in sorted(os.listdir(folder)):
            if not filename.lower().endswith(".ogg"):
                continue
            path = folder / filename
            name = os.path.splitext(filename)[0]
            duration = self._read_duration(path)
            meta = self._metadata.get(name, {})
            key = f"{language}/{category}/{name}"
            self.sounds[key] = Sound(
                key=key,
                language=language,
                category=category,
                filename=name,
                title=meta.get("title") or self._prettify(name),
                description=meta.get("description") or "",
                duration=duration,
                path=str(path),
            )

    @staticmethod
    def _read_duration(path: Path) -> float:
        try:
            info = sf.info(str(path))
            return info.frames / info.samplerate
        except Exception as exc:  # corrupt/odd file: keep it, just no duration
            log.warning("Could not read duration of %s: %s", path, exc)
            return 0.0

    def _prettify(self, filename: str) -> str:
        """Fallback title from a filename like <Prefix>Attack_12."""
        prefix = self.character.filename_prefix_to_strip
        name = filename.removeprefix(prefix) if prefix else filename
        return name.replace("_", " ").strip() or filename

    def _order_categories(self, found: set[str]) -> list[str]:
        order = self.character.category_order
        ordered = [c for c in order if c in found]
        ordered += sorted(found - set(ordered))
        return ordered
