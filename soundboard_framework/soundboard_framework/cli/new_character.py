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
