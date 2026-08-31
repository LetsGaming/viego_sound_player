# Soundboard Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the Viego-specific sound player into an installable `soundboard_framework` package, with Viego becoming the first "character project" built on top of it — so a new character needs only a config file, an icons folder, and a folder of `.ogg` files.

**Architecture:** Monorepo split into `soundboard_framework/` (installable Python package: Flask app factory, `Library`/`Player` engine, shared PWA static assets/templates, CLI tools) and `characters/viego/` (a `character.toml`, sound assets, optional theme CSS, and a 3-line `run.py`). Character-specific values (branding, theme colors, category labels/order, fade timings, voice-scraper source) move from hardcoded Python/HTML into `character.toml`, loaded into a `Character` dataclass at startup.

**Tech Stack:** Python 3.11+, Flask, `sounddevice`/`soundfile` (unchanged), stdlib `tomllib` for config parsing, `pytest` for the new test suite, vanilla JS/CSS frontend (unchanged, moved as-is).

**Spec:** `docs/superpowers/specs/2026-08-30-soundboard-framework-design.md`

## Global Constraints

- Core package installed locally/editable (`-e ../../soundboard_framework`), not published to PyPI.
- No multi-character runtime switching — one server process serves exactly one character.
- `player.py`'s audio engine logic (render callback, locking model, fade/loop math) must not change behaviorally — only how fade durations are supplied to it (constructor params instead of module-level `config` import).
- `app.js` and the bulk of `styles.css` move into the framework unchanged (byte-for-byte except CSS `:root` theme-variable extraction, see Task 5).
- API routes (`/api/library`, `/api/status`, `/api/play`, `/api/stop`, `/api/volume`, `/api/loop`, `/api/reload`) keep their exact paths, methods, and JSON shapes.
- `CharacterConfigError` must be raised with a specific, actionable message for missing/invalid config — never a bare `KeyError`/`TypeError` surfacing from library/app code.
- Env vars for host/port become `SOUNDBOARD_HOST` (default `0.0.0.0`) / `SOUNDBOARD_PORT` (default `5000`), replacing `VIEGO_HOST`/`VIEGO_PORT`.

---

## File Structure

```
soundboard_framework/
├── pyproject.toml
├── soundboard_framework/
│   ├── __init__.py
│   ├── app.py                    # create_app(character_dir) + routes
│   ├── config.py                 # Character dataclass + load_character()
│   ├── library.py                # Sound, Library (character-scoped)
│   ├── player.py                 # Player, _Playback (fade params via ctor)
│   ├── static/
│   │   ├── app.js                # moved from Server/static/app.js, unchanged
│   │   ├── sw.js                 # moved, unchanged
│   │   └── styles.css            # moved, colors/font_display extracted out
│   ├── templates/
│   │   ├── index.html.jinja
│   │   └── manifest.webmanifest.jinja
│   └── cli/
│       ├── __init__.py
│       ├── serve.py              # `soundboard-serve`
│       ├── fetch.py              # `soundboard-fetch`
│       └── new_character.py      # `soundboard-new`
└── tests/
    ├── test_config.py
    ├── test_library.py
    └── test_player.py

characters/viego/
├── character.toml
├── theme.css                     # mist-pulse animation only
├── icons/
│   ├── favicon.ico
│   ├── icon-192.png
│   └── icon-512.png
├── sounds/                       # git mv from Server/static/sounds
│   ├── sounds_metadata.json
│   ├── en/<category>/*.ogg
│   ├── de/<category>/*.ogg
│   └── music/*.ogg
├── requirements.txt
└── run.py
```

`Server/` and `tools/` are deleted in Task 11 once their content has moved.

---

### Task 1: Framework package scaffold

**Files:**
- Create: `soundboard_framework/pyproject.toml`
- Create: `soundboard_framework/soundboard_framework/__init__.py`
- Create: `soundboard_framework/soundboard_framework/cli/__init__.py`
- Create: `soundboard_framework/tests/__init__.py`

**Interfaces:**
- Produces: an importable, editable-installable package named `soundboard_framework` that later tasks add modules to.

- [ ] **Step 1: Create the package directories and empty `__init__.py` files**

```bash
mkdir -p /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework/soundboard_framework/cli
mkdir -p /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework/soundboard_framework/static
mkdir -p /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework/soundboard_framework/templates
mkdir -p /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework/tests
touch /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework/soundboard_framework/__init__.py
touch /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework/soundboard_framework/cli/__init__.py
touch /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework/tests/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "soundboard-framework"
version = "0.1.0"
description = "Reusable server + PWA framework for cosplay/character soundboards."
requires-python = ">=3.11"
dependencies = [
    "Flask>=3.0",
    "sounddevice>=0.5",
    "soundfile>=0.13",
    "numpy>=1.26",
    "requests>=2.31",
    "beautifulsoup4>=4.12",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
soundboard-serve = "soundboard_framework.cli.serve:main"
soundboard-fetch = "soundboard_framework.cli.fetch:main"
soundboard-new = "soundboard_framework.cli.new_character:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["soundboard_framework*"]

[tool.setuptools.package-data]
soundboard_framework = ["static/*", "templates/*"]
```

- [ ] **Step 3: Install the package editable, with dev deps, into the current environment**

Run: `pip install -e "/home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework[dev]"`
Expected: installs successfully; `python -c "import soundboard_framework"` exits 0.

- [ ] **Step 4: Commit**

```bash
git add soundboard_framework/pyproject.toml soundboard_framework/soundboard_framework/__init__.py soundboard_framework/soundboard_framework/cli/__init__.py soundboard_framework/tests/__init__.py
git commit -m "scaffold soundboard_framework package"
```

---

### Task 2: Character config loader

**Files:**
- Create: `soundboard_framework/soundboard_framework/config.py`
- Test: `soundboard_framework/tests/test_config.py`

**Interfaces:**
- Produces:
  - `class CharacterConfigError(Exception)`
  - `DEFAULT_THEME: dict[str, str]` — Viego's palette used as fallback theme values (keys: `abyss`, `mist`, `mist_raised`, `edge`, `glow`, `glow_soft`, `bone`, `muted`, `danger`, `font_display`)
  - `@dataclass(frozen=True) class Character` with fields: `dir: Path`, `name: str`, `short_name: str`, `description: str`, `filename_prefix_to_strip: str`, `fade_in_ms: int`, `fade_out_ms: int`, `language_independent_categories: frozenset[str]`, `category_order: tuple[str, ...]`, `category_labels: dict[str, str]`, `theme: dict[str, str]`, `voice_scraper_url: str | None`, `voice_scraper_category_map: dict[str, str]`
  - `load_character(character_dir: Path) -> Character`
- Consumes: nothing (first logic module).

- [ ] **Step 1: Write the failing tests**

Create `soundboard_framework/tests/test_config.py`:

```python
import pytest

from soundboard_framework.config import CharacterConfigError, load_character

MINIMAL_TOML = """
[character]
name = "Testy"

[audio]
fade_in_ms = 400
fade_out_ms = 300
"""

FULL_TOML = """
[character]
name = "Testy"
short_name = "TST"
description = "A test character."
filename_prefix_to_strip = "Testy_Original_"

[audio]
fade_in_ms = 400
fade_out_ms = 300
language_independent_categories = ["music"]

[categories]
order = ["general", "attack"]

[categories.labels]
general = "General"
attack = "Attack"

[theme]
abyss = "#000000"
glow = "#ff00ff"

[voice_scraper]
url = "https://example.com/audio"

[voice_scraper.category_map]
Joke = "general"
"""


def write_toml(tmp_path, content):
    (tmp_path / "character.toml").write_text(content, encoding="utf-8")
    return tmp_path


def test_minimal_config_loads_with_defaults(tmp_path):
    character_dir = write_toml(tmp_path, MINIMAL_TOML)

    character = load_character(character_dir)

    assert character.name == "Testy"
    assert character.short_name == "Testy"  # defaults to name
    assert character.description == ""
    assert character.filename_prefix_to_strip == ""
    assert character.fade_in_ms == 400
    assert character.fade_out_ms == 300
    assert character.language_independent_categories == frozenset()
    assert character.category_order == ()
    assert character.category_labels == {}
    assert character.theme["abyss"]  # falls back to DEFAULT_THEME
    assert character.voice_scraper_url is None
    assert character.voice_scraper_category_map == {}


def test_full_config_loads_all_fields(tmp_path):
    character_dir = write_toml(tmp_path, FULL_TOML)

    character = load_character(character_dir)

    assert character.short_name == "TST"
    assert character.description == "A test character."
    assert character.filename_prefix_to_strip == "Testy_Original_"
    assert character.language_independent_categories == frozenset({"music"})
    assert character.category_order == ("general", "attack")
    assert character.category_labels == {"general": "General", "attack": "Attack"}
    assert character.theme["abyss"] == "#000000"
    assert character.theme["glow"] == "#ff00ff"
    assert character.voice_scraper_url == "https://example.com/audio"
    assert character.voice_scraper_category_map == {"Joke": "general"}


def test_missing_file_raises_specific_error(tmp_path):
    with pytest.raises(CharacterConfigError, match="character.toml not found"):
        load_character(tmp_path)


def test_missing_required_field_raises_specific_error(tmp_path):
    write_toml(tmp_path, '[character]\nname = "Testy"\n')

    with pytest.raises(CharacterConfigError, match="audio.fade_in_ms"):
        load_character(tmp_path)


def test_unknown_keys_are_ignored(tmp_path):
    write_toml(
        tmp_path,
        MINIMAL_TOML + '\n[character]\nnickname = "ignored"\n',
    )
    # duplicate [character] table is invalid TOML on purpose only if it
    # redefines the table; use a genuinely unknown key instead:
    write_toml(
        tmp_path,
        MINIMAL_TOML.replace(
            '[character]\nname = "Testy"',
            '[character]\nname = "Testy"\nnickname = "ignored"',
        ),
    )

    character = load_character(tmp_path)

    assert character.name == "Testy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'soundboard_framework.config'` (or similar import error) for every test.

- [ ] **Step 3: Write `soundboard_framework/soundboard_framework/config.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && pytest tests/test_config.py -v`
Expected: PASS — all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add soundboard_framework/soundboard_framework/config.py soundboard_framework/tests/test_config.py
git commit -m "add character.toml loader with Character dataclass"
```

---

### Task 3: Library refactor (character-scoped)

**Files:**
- Create: `soundboard_framework/soundboard_framework/library.py`
- Test: `soundboard_framework/tests/test_library.py`

**Interfaces:**
- Consumes: `soundboard_framework.config.Character` (from Task 2) — reads `.filename_prefix_to_strip`, `.language_independent_categories`, `.category_order`, `.category_labels`.
- Produces:
  - `@dataclass(frozen=True) class Sound` (same fields/`.to_dict()` as today's `Server/library.py`)
  - `class Library` with `__init__(self, character: Character, sounds_dir: Path, metadata_path: Path)`, `.load()`, `.get(key: str) -> Sound | None`, `.catalog() -> dict`, `.sounds: dict[str, Sound]`, `.languages: list[str]`, `.categories: list[str]`

- [ ] **Step 1: Write the failing tests**

Create `soundboard_framework/tests/test_library.py`:

```python
import json

import numpy as np
import soundfile as sf

from soundboard_framework.config import Character
from soundboard_framework.library import Library


def make_character(tmp_path, **overrides):
    defaults = dict(
        dir=tmp_path,
        name="Testy",
        short_name="Testy",
        description="",
        filename_prefix_to_strip="Testy_Original_",
        fade_in_ms=400,
        fade_out_ms=300,
        language_independent_categories=frozenset({"music"}),
        category_order=("general", "attack"),
        category_labels={"general": "General", "attack": "Attack"},
        theme={},
        voice_scraper_url=None,
        voice_scraper_category_map={},
    )
    defaults.update(overrides)
    return Character(**defaults)


def write_ogg(path, seconds=1.0, samplerate=8000):
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = np.zeros((int(seconds * samplerate), 1), dtype="float32")
    sf.write(str(path), frames, samplerate, format="OGG", subtype="VORBIS")


def test_scans_languages_and_categories(tmp_path):
    sounds_dir = tmp_path / "sounds"
    write_ogg(sounds_dir / "en" / "general" / "Testy_Original_Joke_0.ogg")
    write_ogg(sounds_dir / "en" / "attack" / "Testy_Original_Attack_0.ogg")
    write_ogg(sounds_dir / "de" / "general" / "Testy_Original_Joke_0.ogg")
    write_ogg(sounds_dir / "music" / "Testy_Original_Theme.ogg")
    character = make_character(tmp_path)

    library = Library(character, sounds_dir, sounds_dir / "sounds_metadata.json")
    library.load()

    assert library.languages == ["de", "en"]
    assert library.categories == ["general", "attack", "music"]
    assert set(library.sounds) == {
        "en/general/Testy_Original_Joke_0",
        "en/attack/Testy_Original_Attack_0",
        "de/general/Testy_Original_Joke_0",
        "-/music/Testy_Original_Theme",
    }


def test_unlisted_category_appended_alphabetically(tmp_path):
    sounds_dir = tmp_path / "sounds"
    write_ogg(sounds_dir / "en" / "zzz_extra" / "Testy_Original_Foo.ogg")
    write_ogg(sounds_dir / "en" / "general" / "Testy_Original_Joke_0.ogg")
    character = make_character(tmp_path)

    library = Library(character, sounds_dir, sounds_dir / "sounds_metadata.json")
    library.load()

    assert library.categories == ["general", "zzz_extra"]


def test_filename_prefix_stripped_for_fallback_title(tmp_path):
    sounds_dir = tmp_path / "sounds"
    write_ogg(sounds_dir / "en" / "general" / "Testy_Original_Big_Joke.ogg")
    character = make_character(tmp_path)

    library = Library(character, sounds_dir, sounds_dir / "sounds_metadata.json")
    library.load()

    sound = library.get("en/general/Testy_Original_Big_Joke")
    assert sound.title == "Big Joke"


def test_metadata_file_overrides_title_and_description(tmp_path):
    sounds_dir = tmp_path / "sounds"
    write_ogg(sounds_dir / "en" / "general" / "Testy_Original_Joke_0.ogg")
    metadata_path = sounds_dir / "sounds_metadata.json"
    metadata_path.write_text(
        json.dumps({"Testy_Original_Joke_0": {"title": "Custom Title", "description": "Desc"}}),
        encoding="utf-8",
    )
    character = make_character(tmp_path)

    library = Library(character, sounds_dir, metadata_path)
    library.load()

    sound = library.get("en/general/Testy_Original_Joke_0")
    assert sound.title == "Custom Title"
    assert sound.description == "Desc"


def test_catalog_shape(tmp_path):
    sounds_dir = tmp_path / "sounds"
    write_ogg(sounds_dir / "en" / "general" / "Testy_Original_Joke_0.ogg")
    character = make_character(tmp_path)

    library = Library(character, sounds_dir, sounds_dir / "sounds_metadata.json")
    library.load()
    catalog = library.catalog()

    assert catalog["languages"] == ["en"]
    assert catalog["categories"] == [{"id": "general", "label": "General", "shared": False}]
    assert len(catalog["sounds"]) == 1
    assert catalog["sounds"][0]["key"] == "en/general/Testy_Original_Joke_0"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && pytest tests/test_library.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'soundboard_framework.library'`.

- [ ] **Step 3: Write `soundboard_framework/soundboard_framework/library.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && pytest tests/test_library.py -v`
Expected: PASS — all 5 tests pass. (If `format="OGG"` write fails because the installed `libsndfile` lacks Vorbis support, switch fixture writes to `format="WAV"` and adjust the `.ogg`-only filter assumption in the failing test's fixture filenames' extensions accordingly — but try OGG first since it matches production files exactly.)

- [ ] **Step 5: Commit**

```bash
git add soundboard_framework/soundboard_framework/library.py soundboard_framework/tests/test_library.py
git commit -m "add character-scoped Library"
```

---

### Task 4: Player refactor (fade params via constructor)

**Files:**
- Create: `soundboard_framework/soundboard_framework/player.py`
- Test: `soundboard_framework/tests/test_player.py`

**Interfaces:**
- Consumes: `soundboard_framework.library.Sound` (from Task 3).
- Produces: `class Player` with `__init__(self, fade_in_ms: int, fade_out_ms: int)`, `.init()`, `.available`, `.play(sound, loop)`, `.stop()`, `.set_volume(volume) -> float`, `.set_loop(loop) -> bool`, `.status() -> dict`. Internal `class _Playback` now takes `fade_in_ms`/`fade_out_ms` in its constructor instead of reading a module-level `config`.

- [ ] **Step 1: Write the failing tests**

Create `soundboard_framework/tests/test_player.py`. These test the render math directly against `_Playback`/`Player._render`, without opening a real audio device:

```python
import numpy as np

from soundboard_framework.library import Sound
from soundboard_framework.player import Player, _Playback


def make_sound():
    return Sound(
        key="en/general/x",
        language="en",
        category="general",
        filename="x",
        title="X",
        description="",
        duration=1.0,
        path="/dev/null",
    )


def test_player_stores_fade_settings():
    player = Player(fade_in_ms=400, fade_out_ms=300)
    assert player._fade_in_ms == 400
    assert player._fade_out_ms == 300


def test_playback_computes_fade_frames_from_constructor_args():
    data = np.ones((8000, 1), dtype="float32")
    pb = _Playback(make_sound(), data, samplerate=8000, fade_in_ms=500, fade_out_ms=250)

    assert pb.fade_in_frames == 4000  # 500ms at 8kHz
    assert pb.fade_out_frames == 2000  # 250ms at 8kHz


def test_render_loops_gaplessly_when_loop_enabled():
    data = np.arange(4, dtype="float32").reshape(4, 1)  # 4-frame "sound"
    pb = _Playback(make_sound(), data, samplerate=8000, fade_in_ms=0, fade_out_ms=0)
    player = Player(fade_in_ms=0, fade_out_ms=0)
    player._pb = pb
    player._loop = True

    out = np.zeros((6, 1), dtype="float32")  # request more frames than the sound has
    player._render(pb, out, 6)

    # wraps within the same callback: [0,1,2,3] then wraps to [0,1]
    np.testing.assert_array_equal(out[:, 0], [0, 1, 2, 3, 0, 1])
    assert pb.pos == 2
    assert not pb.finished


def test_render_ends_when_loop_disabled_and_data_exhausted():
    data = np.arange(4, dtype="float32").reshape(4, 1)
    pb = _Playback(make_sound(), data, samplerate=8000, fade_in_ms=0, fade_out_ms=0)
    player = Player(fade_in_ms=0, fade_out_ms=0)
    player._pb = pb
    player._loop = False

    out = np.full((6, 1), -1, dtype="float32")

    try:
        player._render(pb, out, 6)
    except Exception as exc:
        # sounddevice.CallbackStop is raised when a stream ends; accept any
        # exception here since `sd` may be unavailable in the test env.
        assert type(exc).__name__ == "CallbackStop"

    np.testing.assert_array_equal(out[:4, 0], [0, 1, 2, 3])
    np.testing.assert_array_equal(out[4:, 0], [0, 0])
    assert pb.finished
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && pytest tests/test_player.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'soundboard_framework.player'`.

- [ ] **Step 3: Write `soundboard_framework/soundboard_framework/player.py`**

```python
"""Thread-safe, non-blocking audio playback via sounddevice + soundfile.

Each sound is decoded to a float32 numpy array once, and a PortAudio stream
callback renders it. Because we fill the buffers ourselves:

- Looping is sample-accurate and truly gapless: when the read position hits
  the end and loop is on, it wraps *within the same callback buffer*.
- Toggling loop mid-play is just a flag the callback reads -- playback is
  never interrupted (loop-off finishes the current pass, then stops).
- The reported position is exact (frames rendered / sample rate), not a
  wall-clock estimate.
- Fade-in, fade-out and volume are per-sample envelopes.

Concurrency model: control methods take a lock; the realtime callback never
takes the lock -- it only reads plain attributes (atomic under the GIL).
Each stream's callback is bound to its own _Playback, so a superseded stream
can never render the sound that replaced it. Stream teardown always happens
outside the lock, because PortAudio may invoke finished_callback from within
abort()/close().
"""
from __future__ import annotations

import logging
import threading

import numpy as np
import soundfile as sf

from soundboard_framework.library import Sound

log = logging.getLogger(__name__)

try:
    import sounddevice as sd
    _SD_ERROR: str | None = None
except OSError as exc:  # PortAudio library missing on the host
    sd = None
    _SD_ERROR = str(exc)


class _Playback:
    """State of one playing sound, owned by its stream's render callback."""

    __slots__ = (
        "sound", "data", "samplerate", "stream", "pos", "frames_done",
        "fade_in_frames", "fade_out_frames", "fadeout_at", "finished",
    )

    def __init__(
        self,
        sound: Sound,
        data: np.ndarray,
        samplerate: int,
        fade_in_ms: int,
        fade_out_ms: int,
    ) -> None:
        self.sound = sound
        self.data = data                     # float32, shape (frames, channels)
        self.samplerate = samplerate
        self.stream = None
        self.pos = 0                         # read position within data
        self.frames_done = 0                 # total frames rendered (monotonic)
        self.fade_in_frames = int(fade_in_ms / 1000 * samplerate)
        self.fade_out_frames = int(fade_out_ms / 1000 * samplerate)
        self.fadeout_at: int | None = None   # frames_done at which fade-out began
        self.finished = False


class Player:
    def __init__(self, fade_in_ms: int, fade_out_ms: int) -> None:
        self._fade_in_ms = fade_in_ms
        self._fade_out_ms = fade_out_ms
        self._lock = threading.Lock()
        self._pb: _Playback | None = None
        self._loop: bool = False
        self._volume: float = 1.0
        self._available = False

    def init(self) -> None:
        """Check that an output device exists. Streams are opened per play so
        they can match each file's sample rate and channel count exactly."""
        if sd is None:
            log.error("PortAudio not available: %s", _SD_ERROR)
            return
        try:
            sd.check_output_settings()
            self._available = True
            device = sd.query_devices(kind="output")
            log.info("Audio output ready: %s", device["name"])
        except Exception as exc:
            self._available = False
            log.error("No usable audio output device: %s", exc)

    @property
    def available(self) -> bool:
        return self._available

    # -- controls -----------------------------------------------------------

    def play(self, sound: Sound, loop: bool) -> None:
        if not self._available:
            raise RuntimeError("No audio output device is available on the server.")
        data, samplerate = sf.read(sound.path, dtype="float32", always_2d=True)
        pb = _Playback(sound, data, samplerate, self._fade_in_ms, self._fade_out_ms)
        pb.stream = sd.OutputStream(
            samplerate=samplerate,
            channels=data.shape[1],
            dtype="float32",
            callback=lambda out, fr, t, s, _pb=pb: self._render(_pb, out, fr),
            finished_callback=lambda _pb=pb: self._on_finished(_pb),
        )

        with self._lock:
            old = self._pb
            self._pb = pb
            self._loop = loop
        self._teardown(old)  # outside the lock
        pb.stream.start()

    def stop(self) -> None:
        """Request a fade-out; the callback ends the stream at silence."""
        with self._lock:
            pb = self._pb
            if pb is not None and pb.fadeout_at is None:
                pb.fadeout_at = pb.frames_done

    def set_volume(self, volume: float) -> float:
        volume = max(0.0, min(1.0, volume))
        with self._lock:
            self._volume = volume
        return volume

    def set_loop(self, loop: bool) -> bool:
        """Flip the loop flag without interrupting playback. Loop-on repeats
        seamlessly after the current pass; loop-off finishes the current pass
        and then stops."""
        with self._lock:
            self._loop = loop
        return loop

    # -- status ---------------------------------------------------------------

    def status(self) -> dict:
        with self._lock:
            pb = self._pb
            playing = pb is not None and not pb.finished
            if not playing:
                return {
                    "playing": False,
                    "sound": None,
                    "position": 0.0,
                    "loop": False,
                    "volume": self._volume,
                    "audio_available": self._available,
                }
            return {
                "playing": True,
                "sound": pb.sound.to_dict(),
                "position": round(pb.pos / pb.samplerate, 2),
                "loop": self._loop,
                "volume": self._volume,
                "audio_available": self._available,
            }

    # -- realtime callback (never blocks, never takes the lock) ----------------

    def _render(self, pb: _Playback, outdata: np.ndarray, frames: int) -> None:
        if pb is not self._pb or pb.finished:
            # Superseded by a newer play(); go silent and end this stream.
            outdata.fill(0)
            raise sd.CallbackStop

        total = len(pb.data)
        filled = 0
        ended = False
        while filled < frames:
            if pb.pos >= total:
                if self._loop:
                    pb.pos = 0  # gapless wrap within this very buffer
                else:
                    ended = True
                    break
            n = min(frames - filled, total - pb.pos)
            outdata[filled:filled + n] = pb.data[pb.pos:pb.pos + n]
            pb.pos += n
            filled += n
        if filled < frames:
            outdata[filled:] = 0

        # per-sample gain envelope: fade-in * fade-out * volume
        idx = pb.frames_done + np.arange(frames, dtype=np.float32)
        gain = np.full(frames, self._volume, dtype=np.float32)
        if pb.fade_in_frames > 0:
            gain *= np.clip(idx / pb.fade_in_frames, 0.0, 1.0)
        faded_out = False
        if pb.fadeout_at is not None:
            if pb.fade_out_frames > 0:
                fade = 1.0 - (idx - pb.fadeout_at) / pb.fade_out_frames
                gain *= np.clip(fade, 0.0, 1.0)
                faded_out = pb.frames_done + frames >= pb.fadeout_at + pb.fade_out_frames
            else:
                gain[:] = 0.0
                faded_out = True
        if filled:
            outdata[:filled] *= gain[:filled, None]

        pb.frames_done += frames
        if ended or faded_out:
            pb.finished = True
            raise sd.CallbackStop

    # -- teardown ---------------------------------------------------------------

    def _on_finished(self, pb: _Playback) -> None:
        """PortAudio calls this after the stream stops. Clear state only if
        this playback is still the current one (it may have been replaced)."""
        pb.finished = True
        with self._lock:
            if self._pb is pb:
                self._pb = None
                self._loop = False
        self._close_stream(pb)

    def _teardown(self, pb: _Playback | None) -> None:
        if pb is None:
            return
        pb.finished = True
        self._close_stream(pb)

    @staticmethod
    def _close_stream(pb: _Playback) -> None:
        stream, pb.stream = pb.stream, None
        if stream is None:
            return
        try:
            stream.abort(ignore_errors=True)
            stream.close(ignore_errors=True)
        except Exception:
            pass
```

Note: in the test file, `_render`'s `raise sd.CallbackStop` requires `sd` to be non-`None`. If `sounddevice`/PortAudio is unavailable in the CI/dev environment, `sd is None` and `sd.CallbackStop` raises `AttributeError` instead — the test already tolerates any exception type name check being skipped by asserting on `type(exc).__name__ == "CallbackStop"` only inside the `except` branch; if PortAudio truly isn't installed, install `libportaudio2` first (see README) since `sounddevice` itself is always importable but needs the system library at runtime for `OutputStream`, not for raising its `CallbackStop` exception class (which is defined regardless of device availability as long as `import sounddevice` succeeded — only the `OSError` guard in `player.py` sets `sd = None`, and that only happens if the shared library truly can't load).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && pytest tests/test_player.py -v`
Expected: PASS — all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add soundboard_framework/soundboard_framework/player.py soundboard_framework/tests/test_player.py
git commit -m "add Player with constructor-supplied fade timings"
```

---

### Task 5: Framework static assets and templates

**Files:**
- Create: `soundboard_framework/soundboard_framework/static/app.js` (copy of `Server/static/app.js`, unchanged)
- Create: `soundboard_framework/soundboard_framework/static/sw.js` (copy of `Server/static/sw.js`, with one path update)
- Create: `soundboard_framework/soundboard_framework/static/styles.css` (copy of `Server/static/styles.css` with brand-color/font `:root` vars removed)
- Create: `soundboard_framework/soundboard_framework/templates/index.html.jinja`
- Create: `soundboard_framework/soundboard_framework/templates/manifest.webmanifest.jinja`

**Interfaces:**
- Consumes: `Character` (Task 2) fields `.name`, `.short_name`, `.description`, `.theme["abyss"]` — via Jinja `{{ character.* }}` in templates.
- Produces: assets Task 6's `create_app` serves at `/static/app.js`, `/static/sw.js`, `/theme.css` (built from `static/styles.css` + theme + optional character `theme.css`), and templates rendered at `/` and `/manifest.webmanifest`.

- [ ] **Step 1: Copy `app.js` unchanged**

```bash
cp /home/kirchner/Dokumente/github/viego_sound_player/Server/static/app.js /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework/soundboard_framework/static/app.js
```

- [ ] **Step 2: Copy `sw.js`, updating the cached shell paths**

Read `Server/static/sw.js`, then write the framework copy with `/static/styles.css` replaced by `/theme.css` (the stylesheet is now served dynamically, not as a static file) in the `SHELL` array:

```javascript
/* Caches the app shell so the panel opens instantly on convention Wi-Fi.
 * API calls always go to the network — playback state must be live. */
const CACHE = "soundboard-shell-v1";
const SHELL = [
  "/",
  "/theme.css",
  "/static/app.js",
  "/manifest.webmanifest",
  "/favicon.ico",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) return; // always live

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((c) => c.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
```

Write this to `soundboard_framework/soundboard_framework/static/sw.js`.

- [ ] **Step 3: Copy `styles.css`, extracting theme colors/font out of `:root`**

Read `Server/static/styles.css` and write the framework copy with the `:root { ... }` block (lines 6-22 of the original) replaced so only non-theme, structural variables remain — `--font-ui`, `--dock-height`, `--radius` stay; `--abyss`, `--mist`, `--mist-raised`, `--edge`, `--glow`, `--glow-soft`, `--bone`, `--muted`, `--danger`, `--font-display` are removed (Task 6's `/theme.css` route supplies them). Everything else in the file (all rules below `:root`) is copied verbatim, unchanged:

```css
/* ============================================================
   Soundboard framework — base structural styles
   Mobile-first. Big tap targets for use in costume/gloves.
   Brand colors and --font-display come from /theme.css, generated
   per-character from character.toml + optional theme.css overrides.
   ============================================================ */

:root {
  --font-ui: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --dock-height: 8.25rem;
  --radius: 12px;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background: var(--abyss);
  color: var(--bone);
  font-family: var(--font-ui);
  -webkit-tap-highlight-color: transparent;
}

body {
  min-height: 100vh;
  /* ambient mist at the top of the page */
  background:
    radial-gradient(120% 45% at 50% -10%, var(--glow-soft), transparent 60%),
    var(--abyss);
}

button {
  font-family: inherit;
  color: inherit;
  background: none;
  border: none;
  cursor: pointer;
}

/* ---------- top bar ---------- */

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  padding: 0.6rem 0.9rem 0.5rem;
  padding-top: calc(0.6rem + env(safe-area-inset-top));
  background: rgba(10, 15, 18, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--edge);
}

.topbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
}

.brand {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.45rem;
  font-weight: 400;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--bone);
  text-shadow: 0 0 18px var(--glow-soft);
}

.lang-switch {
  display: flex;
  border: 1px solid var(--edge);
  border-radius: 999px;
  overflow: hidden;
}

.lang-switch button {
  min-width: 3.2rem;
  padding: 0.5rem 0.9rem;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--muted);
  background: var(--mist);
}

.lang-switch button[aria-pressed="true"] {
  background: var(--glow-soft);
  color: var(--glow);
}

.search {
  width: 100%;
  padding: 0.65rem 1rem;
  font-size: 1rem;
  color: var(--bone);
  background: var(--mist);
  border: 1px solid var(--edge);
  border-radius: 999px;
  outline: none;
}

.search:focus { border-color: var(--glow); }
.search::placeholder { color: var(--muted); }

/* ---------- category chips ---------- */

.chips {
  display: flex;
  gap: 0.45rem;
  overflow-x: auto;
  scrollbar-width: none;
  padding-bottom: 0.15rem;
}
.chips::-webkit-scrollbar { display: none; }

.chip {
  flex: 0 0 auto;
  padding: 0.55rem 1rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--muted);
  background: var(--mist);
  border: 1px solid var(--edge);
  border-radius: 999px;
  white-space: nowrap;
}

.chip[aria-pressed="true"] {
  color: var(--abyss);
  background: var(--glow);
  border-color: var(--glow);
}

/* ---------- sound board ---------- */

.board {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.7rem;
  padding: 0.9rem;
  padding-bottom: calc(var(--dock-height) + 1.5rem + env(safe-area-inset-bottom));
  max-width: 900px;
  margin: 0 auto;
}

.board-empty {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--muted);
  padding: 3rem 1rem;
}

.tile {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 0.4rem;
  min-height: 92px;
  padding: 0.75rem 0.8rem;
  text-align: left;
  background: var(--mist-raised);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  transition: transform 80ms ease, border-color 150ms ease;
}

.tile:active { transform: scale(0.97); }

.tile-title {
  font-family: var(--font-display);
  font-size: 1.02rem;
  line-height: 1.25;
  color: var(--bone);
}

.tile-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.78rem;
  color: var(--muted);
}

.tile-fav {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  padding: 0.5rem;          /* generous target */
  font-size: 1.05rem;
  line-height: 1;
  color: var(--muted);
}

.tile-fav[aria-pressed="true"] { color: var(--glow); }

/* ---------- bottom dock ---------- */

.dock {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 30;
  padding: 0 0.9rem calc(0.6rem + env(safe-area-inset-bottom));
  background: rgba(13, 20, 24, 0.97);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--edge);
}

.dock.playing { border-top-color: var(--glow); }

.dock-progress {
  height: 4px;
  margin: 0 -0.9rem 0.55rem;
  background: var(--edge);
  overflow: hidden;
}

.dock-progress-fill {
  height: 100%;
  width: 0%;
  background: var(--glow);
  box-shadow: 0 0 10px var(--glow);
  transition: width 0.9s linear;
}

.dock-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.dock-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.dock-title {
  font-family: var(--font-display);
  font-size: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dock-time {
  font-size: 0.78rem;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.dock-controls {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.ctl {
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  color: var(--muted);
  background: var(--mist-raised);
  border: 1px solid var(--edge);
  border-radius: 50%;
}

.ctl:active { transform: scale(0.94); }

.ctl[aria-pressed="true"] {
  color: var(--glow);
  border-color: var(--glow);
  background: var(--glow-soft);
}

.ctl-stop { color: var(--danger); }
.ctl-small { width: 2.4rem; height: 2.4rem; }

.dock-volume {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.5rem;
}

#volume {
  flex: 1;
  height: 2rem;          /* tall touch strip */
  accent-color: var(--glow);
}

.vol-value {
  width: 3.2rem;
  text-align: right;
  font-size: 0.82rem;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.muted .vol-wave { opacity: 0; }

/* ---------- toast ---------- */

.toast {
  position: fixed;
  left: 50%;
  bottom: calc(var(--dock-height) + 1rem + env(safe-area-inset-bottom));
  transform: translate(-50%, 12px);
  z-index: 40;
  max-width: 90vw;
  padding: 0.6rem 1.1rem;
  font-size: 0.9rem;
  color: var(--bone);
  background: var(--mist-raised);
  border: 1px solid var(--edge);
  border-radius: 999px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 200ms ease, transform 200ms ease;
}

.toast.error { border-color: var(--danger); color: var(--danger); }

.toast.show {
  opacity: 1;
  transform: translate(-50%, 0);
}

/* ---------- larger screens ---------- */

@media (min-width: 700px) {
  .board { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
  .brand { font-size: 1.7rem; }
}

/* visible keyboard focus */
:focus-visible {
  outline: 2px solid var(--glow);
  outline-offset: 2px;
}
```

Note: the `.tile.playing` glow-pulse rule (with its `mist-pulse` keyframes and the `prefers-reduced-motion` override) is intentionally **not** included here — it moves to `characters/viego/theme.css` in Task 10, since it's Viego-specific flavor, not a framework default. A character that omits a `theme.css` simply gets no special playing-tile animation beyond the `border-color` implied by `.dock.playing`/`.chip[aria-pressed]` rules already present above.

- [ ] **Step 4: Write `index.html.jinja`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="{{ character.theme['abyss'] }}" />
  <title>{{ character.name }} Soundboard</title>
  <link rel="manifest" href="/manifest.webmanifest" />
  <link rel="icon" href="/favicon.ico" />
  <link rel="apple-touch-icon" href="/icons/icon-192.png" />
  <link rel="stylesheet" href="/theme.css" />
</head>
<body>
  <header class="topbar">
    <div class="topbar-row">
      <h1 class="brand">{{ character.short_name }}</h1>
      <div class="lang-switch" id="lang-switch" role="group" aria-label="Voice language"></div>
    </div>
    <div class="topbar-row">
      <input
        type="search"
        id="search"
        class="search"
        placeholder="Search sounds…"
        autocomplete="off"
        aria-label="Search sounds"
      />
    </div>
    <nav class="chips" id="category-chips" aria-label="Categories"></nav>
  </header>

  <main class="board" id="board" aria-live="polite">
    <p class="board-empty" id="board-empty" hidden>No sounds match.</p>
  </main>

  <footer class="dock" id="dock">
    <div class="dock-progress">
      <div class="dock-progress-fill" id="progress-fill"></div>
    </div>
    <div class="dock-main">
      <div class="dock-info">
        <span class="dock-title" id="dock-title">Nothing playing</span>
        <span class="dock-time" id="dock-time"></span>
      </div>
      <div class="dock-controls">
        <button class="ctl" id="loop-btn" aria-pressed="false" aria-label="Loop" title="Loop">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 2l4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg>
        </button>
        <button class="ctl ctl-stop" id="stop-btn" aria-label="Stop" title="Stop">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
        </button>
      </div>
    </div>
    <div class="dock-volume">
      <button class="ctl ctl-small" id="mute-btn" aria-label="Mute" title="Mute">
        <svg id="vol-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor" stroke="none"/><path class="vol-wave" d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path class="vol-wave" d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>
      </button>
      <input type="range" id="volume" min="0" max="100" step="1" value="100" aria-label="Volume" />
      <span class="vol-value" id="vol-value">100%</span>
    </div>
  </footer>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 5: Write `manifest.webmanifest.jinja`**

```json
{
  "name": "{{ character.name }} Soundboard",
  "short_name": "{{ character.short_name }}",
  "description": "{{ character.description }}",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "{{ character.theme['abyss'] }}",
  "theme_color": "{{ character.theme['abyss'] }}",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 6: Commit**

```bash
git add soundboard_framework/soundboard_framework/static soundboard_framework/soundboard_framework/templates
git commit -m "add framework static assets and character-templated HTML/manifest"
```

---

### Task 6: Flask app factory

**Files:**
- Create: `soundboard_framework/soundboard_framework/app.py`

**Interfaces:**
- Consumes: `load_character` (Task 2), `Library` (Task 3), `Player` (Task 4), Jinja templates + `static/` (Task 5).
- Produces: `create_app(character_dir: Path) -> Flask` — the single entrypoint later consumed by `cli/serve.py` (Task 7) and `characters/viego/run.py` (Task 10).

- [ ] **Step 1: Write `soundboard_framework/soundboard_framework/app.py`**

```python
"""Soundboard framework — Flask app factory.

Serves a character's mobile-first control panel and JSON API. All playback
happens on the server (e.g. a Raspberry Pi in a costume with a speaker);
any phone on the same network is a remote control. Multiple clients stay in
sync through GET /api/status.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from soundboard_framework.config import load_character
from soundboard_framework.library import Library
from soundboard_framework.player import Player

log = logging.getLogger("soundboard")

FRAMEWORK_DIR = Path(__file__).resolve().parent
STATIC_DIR = FRAMEWORK_DIR / "static"
TEMPLATES_DIR = FRAMEWORK_DIR / "templates"


def create_app(character_dir: Path) -> Flask:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    character_dir = Path(character_dir)
    character = load_character(character_dir)
    sounds_dir = character_dir / "sounds"
    icons_dir = character_dir / "icons"

    library = Library(character, sounds_dir, sounds_dir / "sounds_metadata.json")
    library.load()

    player = Player(fade_in_ms=character.fade_in_ms, fade_out_ms=character.fade_out_ms)
    player.init()

    app = Flask(
        __name__,
        static_folder=str(STATIC_DIR),
        static_url_path="/static",
        template_folder=str(TEMPLATES_DIR),
    )

    # -- pages -----------------------------------------------------------

    @app.route("/")
    def index():
        return app.jinja_env.get_template("index.html.jinja").render(character=character)

    @app.route("/manifest.webmanifest")
    def manifest():
        body = app.jinja_env.get_template("manifest.webmanifest.jinja").render(character=character)
        return Response(body, mimetype="application/manifest+json")

    @app.route("/theme.css")
    def theme_css():
        base_css = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")
        theme_vars = "\n".join(
            f"  --{key.replace('_', '-')}: {value};" for key, value in character.theme.items()
        )
        generated = f":root {{\n{theme_vars}\n}}\n"
        custom_path = character_dir / "theme.css"
        custom_css = custom_path.read_text(encoding="utf-8") if custom_path.is_file() else ""
        return Response(f"{base_css}\n{generated}\n{custom_css}", mimetype="text/css")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(str(icons_dir), "favicon.ico")

    @app.route("/icons/<path:filename>")
    def icons(filename):
        return send_from_directory(str(icons_dir), filename)

    @app.route("/sw.js")
    def service_worker():
        # Served from root scope so the PWA can control the whole app.
        return send_from_directory(str(STATIC_DIR), "sw.js")

    # -- API ----------------------------------------------------------------

    @app.get("/api/library")
    def api_library():
        return jsonify(library.catalog())

    @app.get("/api/status")
    def api_status():
        return jsonify(player.status())

    @app.post("/api/play")
    def api_play():
        data = request.get_json(silent=True) or {}
        key = data.get("key")
        if not key:
            return jsonify({"error": "Missing 'key'."}), 400

        sound = library.get(key)
        if sound is None:
            return jsonify({"error": f"Unknown sound: {key}"}), 404

        loop = bool(data.get("loop", False))
        try:
            player.play(sound, loop=loop)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        except Exception:
            log.exception("Playback failed for %s", key)
            return jsonify({"error": "Playback failed on the server."}), 500

        return jsonify(player.status())

    @app.post("/api/stop")
    def api_stop():
        player.stop()
        return jsonify(player.status())

    @app.post("/api/volume")
    def api_volume():
        data = request.get_json(silent=True) or {}
        try:
            volume = float(data.get("volume"))
        except (TypeError, ValueError):
            return jsonify({"error": "'volume' must be a number between 0 and 1."}), 400
        applied = player.set_volume(volume)
        return jsonify({"volume": applied})

    @app.post("/api/loop")
    def api_loop():
        data = request.get_json(silent=True) or {}
        loop = bool(data.get("loop", False))
        player.set_loop(loop)
        return jsonify(player.status())

    @app.post("/api/reload")
    def api_reload():
        """Rescan the sounds folder (e.g. after adding new files) without restart."""
        library.load()
        return jsonify({"sounds": len(library.sounds)})

    return app
```

- [ ] **Step 2: Sanity-check the module imports without error**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && python -c "from soundboard_framework.app import create_app; print('ok')"`
Expected: prints `ok` with no exceptions.

- [ ] **Step 3: Commit**

```bash
git add soundboard_framework/soundboard_framework/app.py
git commit -m "add Flask app factory serving character-templated pages and API"
```

---

### Task 7: `soundboard-serve` CLI

**Files:**
- Create: `soundboard_framework/soundboard_framework/cli/serve.py`

**Interfaces:**
- Consumes: `create_app` (Task 6).
- Produces: `main()` console-script entrypoint, plus `run(character_dir: Path, host: str | None = None, port: int | None = None) -> None` importable directly (used by `characters/viego/run.py` in Task 10).

- [ ] **Step 1: Write `soundboard_framework/soundboard_framework/cli/serve.py`**

```python
"""`soundboard-serve` — run a character's soundboard server."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from soundboard_framework.app import create_app


def run(character_dir: Path, host: str | None = None, port: int | None = None) -> None:
    host = host or os.environ.get("SOUNDBOARD_HOST", "0.0.0.0")
    port = port or int(os.environ.get("SOUNDBOARD_PORT", "5000"))
    app = create_app(character_dir)
    app.run(host=host, port=port, threaded=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a soundboard character's server.")
    parser.add_argument("--character-dir", required=True, type=Path, help="Path to the character's project folder (containing character.toml).")
    parser.add_argument("--host", default=None, help="Override SOUNDBOARD_HOST.")
    parser.add_argument("--port", type=int, default=None, help="Override SOUNDBOARD_PORT.")
    args = parser.parse_args()

    run(args.character_dir, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Reinstall the package so the new console script registers, then verify `--help` works**

Run: `pip install -e "/home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework[dev]" && soundboard-serve --help`
Expected: prints usage text listing `--character-dir`, `--host`, `--port`.

- [ ] **Step 3: Commit**

```bash
git add soundboard_framework/soundboard_framework/cli/serve.py
git commit -m "add soundboard-serve CLI"
```

---

### Task 8: `soundboard-new` CLI (character scaffolder)

**Files:**
- Create: `soundboard_framework/soundboard_framework/cli/new_character.py`

**Interfaces:**
- Consumes: nothing from other modules (pure filesystem scaffolding).
- Produces: `main()` console-script entrypoint; `scaffold(name: str, characters_root: Path) -> Path` importable for testing/reuse.

- [ ] **Step 1: Write `soundboard_framework/soundboard_framework/cli/new_character.py`**

```python
"""`soundboard-new` — scaffold a new character project."""
from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_CATEGORIES = [
    "general", "move", "long_move", "encounter", "attack", "ability",
    "kill", "death", "respawn", "recall",
]

CHARACTER_TOML_TEMPLATE = """\
[character]
name = "{name}"
short_name = "{name}"
description = "Remote control panel for the {name} cosplay sound player."
filename_prefix_to_strip = ""

[audio]
fade_in_ms = 400
fade_out_ms = 300
language_independent_categories = ["music"]

[categories]
order = {categories!r}

[categories.labels]
{labels}

[theme]
# Leave empty to use the framework's default palette, or override any subset:
# abyss = "#0a0f12"
# glow = "#35e0b8"

[voice_scraper]
# url = "https://example.com/{name}/Audio"
# [voice_scraper.category_map]
# Joke = "general"
"""

RUN_PY_TEMPLATE = '''\
"""Entrypoint for the {name} soundboard. Run with: python run.py"""
from pathlib import Path

from soundboard_framework.cli.serve import run

if __name__ == "__main__":
    run(character_dir=Path(__file__).parent)
'''

REQUIREMENTS_TEMPLATE = "-e ../../soundboard_framework\n"


def scaffold(name: str, characters_root: Path) -> Path:
    character_dir = characters_root / name.lower().replace(" ", "_")
    if character_dir.exists():
        raise FileExistsError(f"{character_dir} already exists")

    labels = "\n".join(f'{c} = "{c.replace("_", " ").title()}"' for c in DEFAULT_CATEGORIES)
    (character_dir).mkdir(parents=True)
    (character_dir / "character.toml").write_text(
        CHARACTER_TOML_TEMPLATE.format(name=name, categories=DEFAULT_CATEGORIES, labels=labels),
        encoding="utf-8",
    )
    (character_dir / "run.py").write_text(RUN_PY_TEMPLATE.format(name=name), encoding="utf-8")
    (character_dir / "requirements.txt").write_text(REQUIREMENTS_TEMPLATE, encoding="utf-8")
    (character_dir / "icons").mkdir()
    for category in DEFAULT_CATEGORIES:
        (character_dir / "sounds" / "en" / category).mkdir(parents=True)
    (character_dir / "sounds" / "music").mkdir(parents=True)

    return character_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new soundboard character project.")
    parser.add_argument("name", help="Character name, e.g. 'Yasuo'.")
    parser.add_argument("--dir", type=Path, default=Path("characters"), help="Parent directory for character projects (default: ./characters).")
    args = parser.parse_args()

    character_dir = scaffold(args.name, args.dir)
    print(f"Created {character_dir}")
    print("Next steps:")
    print(f"  1. Edit {character_dir / 'character.toml'}")
    print(f"  2. Add icons to {character_dir / 'icons'} (favicon.ico, icon-192.png, icon-512.png)")
    print(f"  3. Drop .ogg files into {character_dir / 'sounds'}")
    print(f"  4. pip install -e ../../soundboard_framework  # from inside {character_dir}")
    print(f"  5. python {character_dir / 'run.py'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Manually verify scaffolding works end to end**

Run: `cd /tmp && python -c "from soundboard_framework.cli.new_character import scaffold; from pathlib import Path; print(scaffold('Test Hero', Path('/tmp/scaffold-check')))"`
Expected: prints the created path; `ls /tmp/scaffold-check/test_hero` shows `character.toml`, `run.py`, `requirements.txt`, `icons/`, `sounds/en/<categories>/`, `sounds/music/`.

Run: `rm -rf /tmp/scaffold-check` to clean up.

- [ ] **Step 3: Commit**

```bash
git add soundboard_framework/soundboard_framework/cli/new_character.py
git commit -m "add soundboard-new character scaffolder CLI"
```

---

### Task 9: `soundboard-fetch` CLI (generalized wiki scraper)

**Files:**
- Create: `soundboard_framework/soundboard_framework/cli/fetch.py`

**Interfaces:**
- Consumes: `load_character` (Task 2) for `.voice_scraper_url` / `.voice_scraper_category_map`.
- Produces: `main()` console-script entrypoint.

- [ ] **Step 1: Write `soundboard_framework/soundboard_framework/cli/fetch.py`**

```python
"""`soundboard-fetch` — scrape voice lines + metadata from a wiki audio page.

Generalizes the old Viego-specific audio_downloader.py: the source URL and
category-name mapping now come from the character's character.toml
[voice_scraper] section instead of being hardcoded per-character.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from soundboard_framework.config import load_character

FALLBACK_CATEGORY = "general"


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?"<>|:]', "_", name)


def normalize_category(raw_category: str, category_map: dict[str, str]) -> str:
    for key, value in category_map.items():
        if key.lower() in raw_category.lower():
            return value
    return FALLBACK_CATEGORY


def fetch_html(url: str) -> BeautifulSoup:
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_and_download(
    soup: BeautifulSoup,
    category_map: dict[str, str],
    out_base: Path,
    language: str,
) -> dict:
    metadata: dict = {}
    for header in soup.find_all(["h2", "h3", "h4"]):
        header_text = header.get_text(strip=True)
        current_category = normalize_category(header_text, category_map)

        sibling = header.find_next_sibling()
        while sibling and sibling.name not in ["h2", "h3", "h4"]:
            for audio in sibling.find_all("audio"):
                source = audio.find("source")
                if not source:
                    continue
                src = source.get("src")
                if not src or not src.endswith(".ogg"):
                    continue

                match = re.search(r".*/(.*)\.ogg", src)
                if not match:
                    print(f"Could not extract filename from src: {src}")
                    continue
                filename = sanitize_filename(match.group(1))

                out_dir = out_base / language / current_category
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{filename}.ogg"

                print(f"Downloading {filename}.ogg -> {current_category}")
                try:
                    audio_resp = requests.get(src, stream=True)
                    audio_resp.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in audio_resp.iter_content(1024):
                            f.write(chunk)
                except Exception as exc:
                    print(f"Error downloading {src}: {exc}")
                    continue

                parent_text = audio.find_parent().get_text(" ", strip=True)
                metadata[filename] = {"title": header_text, "description": parent_text}

            sibling = sibling.find_next_sibling()
    return metadata


def save_metadata(metadata: dict, metadata_path: Path) -> None:
    existing: dict = {}
    if metadata_path.is_file():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
    existing.update(metadata)
    metadata_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch voice lines + metadata for a character.")
    parser.add_argument("--character-dir", required=True, type=Path, help="Path to the character's project folder.")
    parser.add_argument("--language", default="en", help="Language subfolder to save sounds under (default: en).")
    args = parser.parse_args()

    character = load_character(args.character_dir)
    if not character.voice_scraper_url:
        raise SystemExit(
            f"{args.character_dir}/character.toml has no [voice_scraper] url set; nothing to fetch."
        )

    sounds_dir = args.character_dir / "sounds"
    metadata_path = sounds_dir / "sounds_metadata.json"

    soup = fetch_html(character.voice_scraper_url)
    metadata = extract_and_download(soup, character.voice_scraper_category_map, sounds_dir, args.language)
    save_metadata(metadata, metadata_path)
    print(f"Done. {len(metadata)} sounds downloaded/updated, metadata written to {metadata_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Sanity-check the module imports without error**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && python -c "from soundboard_framework.cli.fetch import main; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add soundboard_framework/soundboard_framework/cli/fetch.py
git commit -m "add soundboard-fetch CLI, generalizing the wiki voice-line scraper"
```

---

### Task 10: Migrate Viego to a character project

**Files:**
- Create: `characters/viego/character.toml`
- Create: `characters/viego/theme.css`
- Create: `characters/viego/run.py`
- Create: `characters/viego/requirements.txt`
- Move: `Server/static/sounds/` → `characters/viego/sounds/`
- Move: `Server/static/favicon.ico` → `characters/viego/icons/favicon.ico`
- Move: `Server/static/icon-192.png` → `characters/viego/icons/icon-192.png`
- Move: `Server/static/icon-512.png` → `characters/viego/icons/icon-512.png`

**Interfaces:**
- Consumes: `soundboard_framework` package (Tasks 1-9), installed editable.
- Produces: a working Viego deployment, used for manual verification in Task 12.

- [ ] **Step 1: Move the sound assets and icons with `git mv` (preserves history)**

```bash
cd /home/kirchner/Dokumente/github/viego_sound_player
mkdir -p characters/viego/icons
git mv Server/static/sounds characters/viego/sounds
git mv Server/static/favicon.ico characters/viego/icons/favicon.ico
git mv Server/static/icon-192.png characters/viego/icons/icon-192.png
git mv Server/static/icon-512.png characters/viego/icons/icon-512.png
```

- [ ] **Step 2: Write `characters/viego/character.toml`**

```toml
[character]
name = "Viego"
short_name = "Viego"
description = "Remote control panel for the Viego cosplay sound player."
filename_prefix_to_strip = "Viego_Original_"

[audio]
fade_in_ms = 400
fade_out_ms = 300
language_independent_categories = ["music"]

[categories]
order = ["general", "move", "long_move", "encounter", "attack", "ability", "kill", "death", "respawn", "recall", "music"]

[categories.labels]
general = "General"
move = "Move"
long_move = "Long move"
encounter = "Encounter"
attack = "Attack"
ability = "Ability"
kill = "Kill"
death = "Death"
respawn = "Respawn"
recall = "Recall"
music = "Music & SFX"
unsorted = "Unsorted"

[theme]
abyss = "#0a0f12"
mist = "#101a1e"
mist_raised = "#16242a"
edge = "#1e3038"
glow = "#35e0b8"
glow_soft = "rgba(53, 224, 184, 0.18)"
bone = "#dce8e4"
muted = "#7d9691"
danger = "#e06060"
font_display = "\"Palatino Linotype\", \"Book Antiqua\", Palatino, Georgia, serif"

[voice_scraper]
url = "https://wiki.leagueoflegends.com/en-us/Viego/Audio"

[voice_scraper.category_map]
Joke = "general"
Taunt = "general"
Ban = "general"
Movement = "move"
"Long movement" = "long_move"
"First Encounter" = "encounter"
Attack = "attack"
Ability = "ability"
Kill = "kill"
Death = "death"
Respawn = "respawn"
Recall = "recall"
```

- [ ] **Step 3: Write `characters/viego/theme.css`** (Viego's bespoke playing-tile glow, extracted from the old `styles.css`)

```css
/* signature: mist glow on the playing tile */
.tile.playing {
  border-color: var(--glow);
  animation: mist-pulse 2.4s ease-in-out infinite;
}

@keyframes mist-pulse {
  0%, 100% { box-shadow: 0 0 10px rgba(53, 224, 184, 0.25); }
  50%      { box-shadow: 0 0 26px rgba(53, 224, 184, 0.55); }
}

@media (prefers-reduced-motion: reduce) {
  .tile.playing { animation: none; box-shadow: 0 0 14px rgba(53, 224, 184, 0.4); }
  .tile:active { transform: none; }
}
```

- [ ] **Step 4: Write `characters/viego/run.py`**

```python
"""Entrypoint for the Viego soundboard. Run with: python run.py"""
from pathlib import Path

from soundboard_framework.cli.serve import run

if __name__ == "__main__":
    run(character_dir=Path(__file__).parent)
```

- [ ] **Step 5: Write `characters/viego/requirements.txt`**

```
-e ../../soundboard_framework
```

- [ ] **Step 6: Install Viego's requirements and start the server**

Run: `pip install -r /home/kirchner/Dokumente/github/viego_sound_player/characters/viego/requirements.txt`
Expected: installs (or confirms already-installed) `soundboard_framework` editable.

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/characters/viego && python run.py &`
Expected: server starts, logs `Audio output ready: ...` or a clear "no usable audio output device" warning (fine on a dev machine without speakers), and listens on port 5000.

- [ ] **Step 7: Smoke-test the API**

Run: `curl -s http://localhost:5000/api/library | python -m json.tool | head -30`
Expected: JSON with `languages: ["de", "en"]`, `categories` in the configured order, and a non-empty `sounds` array whose entries have `Viego_Original_` stripped from fallback titles where no metadata title exists.

Run: `curl -s http://localhost:5000/theme.css | head -5`
Expected: CSS starting with the framework's base rules, containing a `:root { --abyss: #0a0f12; ... }` block, ending with the `.tile.playing`/`mist-pulse` rules from `theme.css`.

Stop the server: `kill %1` (or find and kill the `python run.py` process).

- [ ] **Step 8: Commit**

```bash
git add characters/viego/character.toml characters/viego/theme.css characters/viego/run.py characters/viego/requirements.txt characters/viego/sounds characters/viego/icons
git commit -m "migrate Viego to a soundboard_framework character project"
```

---

### Task 11: Remove old Server/ and tools/, update README

**Files:**
- Delete: `Server/app.py`, `Server/config.py`, `Server/library.py`, `Server/player.py`, `Server/requirements.txt`, `Server/static/index.html`, `Server/static/styles.css`, `Server/static/sw.js`, `Server/static/app.js`, `Server/static/manifest.webmanifest`
- Delete: `tools/audio_downloader.py`, `tools/json_generator.py`
- Modify: `readme.md`

**Interfaces:**
- Consumes: nothing (cleanup + docs task).
- Produces: a repo where `Server/` and `tools/` no longer exist and `readme.md` describes the framework + Viego + how to add a new character.

- [ ] **Step 1: Confirm every file under `Server/` and `tools/` has an equivalent already migrated**

Run: `find /home/kirchner/Dokumente/github/viego_sound_player/Server /home/kirchner/Dokumente/github/viego_sound_player/tools -type f`
Expected: only the Python/HTML/CSS/JS source files handled in Tasks 3-10 remain (sounds/icons already moved by `git mv` in Task 10, so `Server/static/sounds` and the icon files should no longer appear in this listing).

- [ ] **Step 2: Delete the old directories**

```bash
git rm -r /home/kirchner/Dokumente/github/viego_sound_player/Server
git rm -r /home/kirchner/Dokumente/github/viego_sound_player/tools
```

- [ ] **Step 3: Rewrite `readme.md`**

```markdown
# Soundboard Framework

A reusable framework for cosplay/character soundboards: a Flask server
plays sounds (e.g. on a Raspberry Pi hidden in a costume, connected to a
speaker), and any phone on the same network is a remote control at
`http://<server-ip>:5000`. Playback is non-blocking, sample-accurate
gapless looping via `sounddevice`/`soundfile`, and the frontend is an
installable PWA.

**Viego is the reference character** — the original cosplay this
framework was extracted from — but the server, player, and PWA shell are
entirely character-agnostic. A new character needs only a `character.toml`,
an `icons/` folder, and a `sounds/` folder of `.ogg` files.

## Project structure

```
viego_sound_player/
├── soundboard_framework/       # the installable core package
│   ├── soundboard_framework/
│   │   ├── app.py              # create_app(character_dir)
│   │   ├── config.py           # Character dataclass + character.toml loader
│   │   ├── library.py          # scans sounds/, caches metadata & durations
│   │   ├── player.py           # thread-safe non-blocking playback engine
│   │   ├── static/              # shared app.js, sw.js, styles.css
│   │   ├── templates/           # index.html.jinja, manifest.webmanifest.jinja
│   │   └── cli/                 # soundboard-serve, soundboard-fetch, soundboard-new
│   └── tests/
└── characters/
    └── viego/
        ├── character.toml       # branding, theme, categories, fades
        ├── theme.css            # optional extra CSS (Viego's glow animation)
        ├── icons/                # favicon.ico, icon-192.png, icon-512.png
        ├── sounds/                # sounds_metadata.json, en/, de/, music/
        ├── requirements.txt
        └── run.py
```

## Setup (Viego, or any existing character)

```bash
cd characters/viego
python -m venv venv && source venv/bin/activate   # optional
pip install -r requirements.txt
python run.py
```

Open `http://<server-ip>:5000` on your phone and add it to the home screen.

Environment variables: `SOUNDBOARD_HOST` (default `0.0.0.0`),
`SOUNDBOARD_PORT` (default `5000`) — or pass `--host`/`--port` to
`soundboard-serve`.

## Creating a new character

```bash
pip install -e soundboard_framework
soundboard-new "My Character"
cd characters/my_character
# edit character.toml (theme colors, category labels, fade timings)
# drop icons into icons/ (favicon.ico, icon-192.png, icon-512.png)
# drop .ogg files into sounds/<language>/<category>/, or:
soundboard-fetch --character-dir . --language en   # if [voice_scraper] is configured
pip install -r requirements.txt
python run.py
```

New languages and categories are auto-discovered from the `sounds/`
folder structure — drop a new language folder in and call
`POST /api/reload` (or restart) to pick it up.

## Raspberry Pi note

`sounddevice` needs the PortAudio system library:

```bash
sudo apt install libportaudio2
```

`soundfile` ships with libsndfile bundled in its wheel — no extra packages.

## API

| Method | Route          | Body / params                  | Purpose                          |
|--------|----------------|--------------------------------|-----------------------------------|
| GET    | `/api/library` | —                              | Full catalog (languages, categories, sounds with durations) |
| GET    | `/api/status`  | —                              | Now playing, position, loop, volume |
| POST   | `/api/play`    | `{"key": "en/kill/…", "loop": false}` | Play a sound (replaces current) |
| POST   | `/api/stop`    | —                              | Fade out and stop                |
| POST   | `/api/volume`  | `{"volume": 0.0–1.0}`          | Set server volume                |
| POST   | `/api/loop`    | `{"loop": true}`               | Toggle looping (never interrupts playback)  |
| POST   | `/api/reload`  | —                              | Rescan the sounds folder         |

## Cosplay / on-the-go tips

- **No venue Wi-Fi needed:** run a Wi-Fi hotspot on the Pi (or your phone)
  so the phone ↔ Pi link is self-contained. Give the Pi a static IP and
  bookmark it.
- **Autostart:** run the server as a `systemd` service so it comes up when
  the Pi boots — no keyboard/monitor required.
- Pin your go-to lines to ★ Favorites the night before; at the con you're
  one tap away.

Example systemd unit (`/etc/systemd/system/viego.service`):

```ini
[Unit]
Description=Viego Sound Player
After=network.target sound.target

[Service]
WorkingDirectory=/home/pi/viego_sound_player/characters/viego
ExecStart=/home/pi/viego_sound_player/characters/viego/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Framework development

```bash
pip install -e "soundboard_framework[dev]"
pytest soundboard_framework/tests
```
```

Write this content to `/home/kirchner/Dokumente/github/viego_sound_player/readme.md`, replacing the existing file entirely.

- [ ] **Step 4: Commit**

```bash
git add readme.md
git commit -m "remove legacy Server/ and tools/, rewrite README for the framework"
```

---

### Task 12: End-to-end verification

**Files:** none (verification only).

**Interfaces:** none — exercises the full stack built in Tasks 1-11.

- [ ] **Step 1: Run the full framework test suite**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/soundboard_framework && pytest -v`
Expected: all tests from Tasks 2-4 pass (15 tests total: 6 config + 5 library + 4 player).

- [ ] **Step 2: Start Viego's server**

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player/characters/viego && python run.py`
Expected: starts without error, logs the audio device status, listens on `0.0.0.0:5000`.

- [ ] **Step 3: Open the PWA in a browser and manually verify parity with the original app**

Open `http://localhost:5000` and confirm:
- Page title/brand shows "Viego" and the Shadow Isles color theme renders (teal glow, dark background).
- Language switch shows EN/DE and switching filters the board correctly.
- Category chips (Favorites, Recent, All, General, Move, ..., Music & SFX) render in the configured order.
- Search filters tiles by title/description/filename.
- Tapping a tile plays it (dock shows title + progress bar advancing); tapping again stops it with a fade-out.
- The playing tile shows the teal glow-pulse animation (confirms `theme.css` merge worked).
- Loop toggle persists across the same sound and the dock label shows "· looping".
- Volume slider and mute button both call `/api/volume` and update the UI.
- ★ Favorites toggle persists across a page reload (localStorage) and the Favorites tab shows only pinned sounds.
- `POST /api/reload` (e.g. `curl -X POST http://localhost:5000/api/reload`) returns `{"sounds": N}` with the correct count.

- [ ] **Step 4: Verify PWA install assets**

Run: `curl -sI http://localhost:5000/manifest.webmanifest | head -1` — expect `200`.
Run: `curl -sI http://localhost:5000/sw.js | head -1` — expect `200`.
Run: `curl -sI http://localhost:5000/icons/icon-192.png | head -1` — expect `200`.
Run: `curl -sI http://localhost:5000/favicon.ico | head -1` — expect `200`.

- [ ] **Step 5: Stop the server and do a final repo sanity check**

Stop the `python run.py` process (Ctrl-C or `kill`).

Run: `cd /home/kirchner/Dokumente/github/viego_sound_player && git status`
Expected: working tree clean (everything from Tasks 1-11 already committed); no stray `Server/`/`tools/` directories; `git log --oneline -15` shows one commit per task.
