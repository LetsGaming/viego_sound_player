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
