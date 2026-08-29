# Soundboard Framework — Design

Date: 2026-08-30

## Goal

Turn the Viego-specific sound player into a reusable framework so new
cosplay/character soundboards can be stood up with minimal effort: a config
file, a folder of `.ogg` files, and optional theme tweaks — no forking or
rewriting server code.

## Non-goals

- Multi-character runtime switching in a single server process. Each
  deployment still serves exactly one character (this project's own use
  case doesn't need it, and it would complicate the Player/Library
  singletons for no current benefit).
- Publishing the package to PyPI. It's installed locally/editable
  (`-e ../../soundboard_framework`) from within this monorepo for now.
- Rewriting `player.py`'s audio engine — it is already character-agnostic
  and needs no behavioral changes.

## Repo layout

```
viego_sound_player/
├── soundboard_framework/        # installable core package
│   ├── pyproject.toml
│   ├── soundboard_framework/
│   │   ├── __init__.py
│   │   ├── app.py               # create_app(character_dir) factory + routes
│   │   ├── config.py            # Character dataclass + TOML loader/validator
│   │   ├── library.py           # generic sound scanning (Sound, Library)
│   │   ├── player.py            # unchanged playback engine, moved as-is
│   │   ├── static/              # shared PWA shell: app.js, sw.js, styles.css
│   │   ├── templates/
│   │   │   ├── index.html.jinja
│   │   │   └── manifest.webmanifest.jinja
│   │   └── cli/
│   │       ├── serve.py         # `soundboard-serve`
│   │       ├── fetch.py         # `soundboard-fetch` (generalized scraper)
│   │       └── new_character.py # `soundboard-new`
│   └── tests/
│       ├── test_config.py
│       ├── test_library.py
│       └── test_player.py
└── characters/
    └── viego/
        ├── character.toml
        ├── theme.css             # optional extra CSS (mist-pulse animation)
        ├── icons/                # favicon.ico, icon-192.png, icon-512.png
        ├── sounds/                # en/, de/, music/, sounds_metadata.json
        ├── requirements.txt       # -e ../../soundboard_framework
        └── run.py                 # thin entrypoint
```

`Server/` and `tools/` are deleted after migration; their content moves
into `soundboard_framework/` (generalized) and `characters/viego/`
(character-specific data).

## Character config (`character.toml`)

One TOML file per character holds everything that today lives in
`config.py` plus branding, e.g.:

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

`soundboard_framework.config.load_character(character_dir)`:
- Reads `character.toml`, builds a frozen `Character` dataclass.
- Required fields: `character.name`, `audio.fade_in_ms`, `audio.fade_out_ms`.
  Everything else has a sane default (empty category order → alphabetical
  discovery, default theme = today's Viego palette as a starting point,
  empty `voice_scraper` section disables the `soundboard-fetch` CLI for
  that character with a clear message).
- Raises `CharacterConfigError` with a specific, actionable message
  (missing file, missing required key, wrong type) — never a bare
  `KeyError`/`TypeError` from deep inside library/app code.

`library.py` changes: `Library.__init__` takes a `Character` (for
`category order/labels`, `language_independent_categories`,
`filename_prefix_to_strip`) and a `sounds_dir`/`metadata_path`, replacing
the current module-level `import config` usage. Behavior (scanning,
merging metadata, duration caching, catalog shape) is otherwise unchanged.

`player.py` changes: `Player.__init__` takes `fade_in_ms`/`fade_out_ms`
instead of reading `config.FADE_IN_MS`/`FADE_OUT_MS` at import time.
No other changes — the render callback, locking model, and status shape
are untouched.

## Frontend theming

- `index.html` and `manifest.webmanifest` become Jinja templates rendered
  by Flask with the `Character` object: page title, `short_name`,
  `description`, theme-color meta, icon paths (`/icons/favicon.ico` etc.).
- New route `GET /theme.css` returns: the framework's base `styles.css`
  (all structural/layout rules — unchanged from today) + a generated
  `:root { --abyss: ...; --glow: ...; ... }` block built from
  `[theme]` + the character's `theme.css` file content appended verbatim,
  if present. This lets Viego keep its bespoke `mist-pulse` keyframes and
  `.tile.playing` animation as a small opt-in file instead of forcing
  every visual detail into TOML.
- New route serving character icons, e.g. `GET /icons/<path:filename>`
  from `character_dir/icons/`.
- `app.js` is copied into the framework unchanged — it never referenced
  Viego by name; it renders whatever `/api/library` returns.

## API

Unchanged from today: `/api/library`, `/api/status`, `/api/play`,
`/api/stop`, `/api/volume`, `/api/loop`, `/api/reload`. Route handlers
move into `soundboard_framework/app.py`'s `create_app()`, closing over
that character's `Library`/`Player` instances instead of module globals.

## CLI tools

- **`soundboard-serve --character-dir <path>`**: loads the character,
  builds the Flask app, runs it. Reads `SOUNDBOARD_HOST` (default
  `0.0.0.0`) / `SOUNDBOARD_PORT` (default `5000`) env vars, overridable
  by CLI flags. `characters/viego/run.py` is a 3-line script calling this
  programmatically so `python run.py` keeps working as a habit from
  today's `python app.py`.
- **`soundboard-fetch --character-dir <path> [--language <lang>]`**:
  generalized `audio_downloader.py`. Reads `[voice_scraper]` from that
  character's `character.toml` for the source URL and category map,
  downloads `.ogg`s into `sounds/<language>/<category>/`, and writes/merges
  `sounds_metadata.json`. Subsumes `json_generator.py` (pure link-extraction
  was a strict subset of the downloader's job — no separate script needed).
- **`soundboard-new <name> [--dir characters]`**: scaffolds
  `characters/<name>/` with a template `character.toml` (defaults filled
  in, placeholders for name/theme), empty `sounds/<default-category>/`
  folders, and a `run.py`. Prints next steps (edit character.toml, add
  .ogg files, `pip install -e ../../soundboard_framework`).

## Migration of Viego

1. `git mv Server/static/sounds characters/viego/sounds`
2. `git mv` favicon/icons into `characters/viego/icons/`
3. Extract `.tile.playing` / `mist-pulse` rules from `styles.css` into
   `characters/viego/theme.css`; the rest of `styles.css` moves into
   `soundboard_framework/static/styles.css` unchanged.
4. Write `characters/viego/character.toml` (values taken from today's
   `config.py` + `index.html`/`manifest.webmanifest` branding).
5. Write `characters/viego/run.py`, `requirements.txt`.
6. Delete `Server/` and `tools/` once the equivalent functionality lives
   in `soundboard_framework/`.
7. Update `readme.md` to describe the framework + how Viego consumes it,
   and how to scaffold a new character.

## Testing

No existing test suite; this introduces one for the framework package:

- `test_config.py`: valid TOML loads correctly; missing required field
  raises `CharacterConfigError` with a useful message; unknown keys are
  ignored (forward compatible); defaults apply when optional sections are
  omitted.
- `test_library.py`: category ordering (explicit order + alphabetical
  fallback for unlisted categories), `language_independent_categories`
  handling, filename-prefix stripping in the title fallback, metadata
  merge behavior — using a temp directory with synthetic `.ogg`-named
  files (duration reading mocked/skipped, or using tiny real generated
  wav/ogg fixtures via `soundfile`).
- `test_player.py`: fade-in/fade-out gain envelope math and loop wrap
  logic against synthetic in-memory float32 arrays — no real audio
  device required (construct `_Playback` directly and call `_render`).

Manual verification: run `soundboard-serve --character-dir
characters/viego`, open the PWA in a browser, and confirm parity with
current behavior — play/stop/loop/volume/favorites/search/language
switch/recent all still work, and the mist-pulse glow still renders on
the playing tile.

## Open risks / follow-ups (not blocking this spec)

- `soundboard-fetch`'s wiki scraping is inherently fragile to markup
  changes on the target wiki; that fragility is inherited as-is from
  `audio_downloader.py`, not introduced by this rework.
- No multi-character runtime switching (see Non-goals) — if a future need
  arises for one server hosting several characters, that's a separate
  design.
