"""Sound library.

Scans the sounds directory once at startup, merges in the metadata file and
caches durations, so requests never touch the filesystem or re-parse audio
files. Playback lookups go through the catalog, which also prevents any
path-traversal via user input: only known, indexed files can be played.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

import soundfile as sf

import config

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
    def __init__(self) -> None:
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

        if not os.path.isdir(config.SOUNDS_DIR):
            log.error("Sounds directory not found: %s", config.SOUNDS_DIR)
            return

        for entry in sorted(os.listdir(config.SOUNDS_DIR)):
            entry_path = os.path.join(config.SOUNDS_DIR, entry)
            if not os.path.isdir(entry_path):
                continue

            if entry in config.LANGUAGE_INDEPENDENT_CATEGORIES:
                categories.add(entry)
                self._index_folder(entry_path, language="-", category=entry)
            else:
                # Treat as a language folder containing category folders.
                languages.add(entry)
                for category in sorted(os.listdir(entry_path)):
                    category_path = os.path.join(entry_path, category)
                    if not os.path.isdir(category_path):
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
                    "label": config.CATEGORY_LABELS.get(c, c.replace("_", " ").title()),
                    "shared": c in config.LANGUAGE_INDEPENDENT_CATEGORIES,
                }
                for c in self.categories
            ],
            "sounds": [s.to_dict() for s in self.sounds.values()],
        }

    # -- internals ----------------------------------------------------------

    def _read_metadata(self) -> dict:
        try:
            with open(config.METADATA_PATH, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            log.warning("Metadata file not found: %s", config.METADATA_PATH)
        except json.JSONDecodeError as exc:
            log.error("Metadata file is not valid JSON: %s", exc)
        return {}

    def _index_folder(self, folder: str, language: str, category: str) -> None:
        for filename in sorted(os.listdir(folder)):
            if not filename.lower().endswith(".ogg"):
                continue
            path = os.path.join(folder, filename)
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
                path=path,
            )

    @staticmethod
    def _read_duration(path: str) -> float:
        try:
            info = sf.info(path)
            return info.frames / info.samplerate
        except Exception as exc:  # corrupt/odd file: keep it, just no duration
            log.warning("Could not read duration of %s: %s", path, exc)
            return 0.0

    @staticmethod
    def _prettify(filename: str) -> str:
        """Fallback title from a filename like Viego_Original_Attack_12."""
        name = filename.removeprefix("Viego_Original_")
        return name.replace("_", " ").strip() or filename

    @staticmethod
    def _order_categories(found: set[str]) -> list[str]:
        ordered = [c for c in config.CATEGORY_ORDER if c in found]
        ordered += sorted(found - set(ordered))
        return ordered
