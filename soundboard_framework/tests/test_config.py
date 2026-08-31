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
