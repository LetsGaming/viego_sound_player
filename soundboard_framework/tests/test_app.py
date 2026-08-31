import os

import numpy as np
import soundfile as sf

from soundboard_framework.app import create_app

CHARACTER_TOML = """
[character]
name = "Testy"
short_name = "TST"

[audio]
fade_in_ms = 400
fade_out_ms = 300
"""


def write_ogg(path, seconds=0.2, samplerate=8000):
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = np.zeros((int(seconds * samplerate), 1), dtype="float32")
    sf.write(str(path), frames, samplerate, format="OGG", subtype="VORBIS")


def make_character_dir(base_dir):
    """Write a minimal but complete character project under base_dir."""
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "character.toml").write_text(CHARACTER_TOML, encoding="utf-8")

    icons_dir = base_dir / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    (icons_dir / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    (icons_dir / "icon-192.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    write_ogg(base_dir / "sounds" / "en" / "general" / "Testy_Joke_0.ogg")

    return base_dir


def test_index_returns_character_name(tmp_path):
    character_dir = make_character_dir(tmp_path / "testy")
    app = create_app(character_dir)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "Testy" in response.get_data(as_text=True)


def test_theme_css_returns_root_block(tmp_path):
    character_dir = make_character_dir(tmp_path / "testy")
    app = create_app(character_dir)
    client = app.test_client()

    response = client.get("/theme.css")

    assert response.status_code == 200
    assert response.content_type.startswith("text/css")
    assert ":root" in response.get_data(as_text=True)


def test_favicon_and_icons_are_served(tmp_path):
    character_dir = make_character_dir(tmp_path / "testy")
    app = create_app(character_dir)
    client = app.test_client()

    assert client.get("/favicon.ico").status_code == 200
    assert client.get("/icons/icon-192.png").status_code == 200


def test_favicon_and_icons_served_with_relative_character_dir(tmp_path, monkeypatch):
    """Regression test: create_app() must resolve a relative character_dir
    against the cwd, not against Flask's app.root_path, or icon routes 404
    (this is the documented `soundboard-serve --character-dir characters/x`
    invocation)."""
    parent = tmp_path / "workdir"
    make_character_dir(parent / "characters" / "testy")
    monkeypatch.chdir(parent)

    app = create_app(os.path.join("characters", "testy"))
    client = app.test_client()

    assert client.get("/favicon.ico").status_code == 200
    assert client.get("/icons/icon-192.png").status_code == 200


def test_api_library_returns_expected_shape(tmp_path):
    character_dir = make_character_dir(tmp_path / "testy")
    app = create_app(character_dir)
    client = app.test_client()

    response = client.get("/api/library")

    assert response.status_code == 200
    data = response.get_json()
    assert set(data.keys()) == {"languages", "categories", "sounds"}
    assert data["languages"] == ["en"]
    assert len(data["sounds"]) == 1


def test_api_volume_clamps_out_of_range_values(tmp_path):
    character_dir = make_character_dir(tmp_path / "testy")
    app = create_app(character_dir)
    client = app.test_client()

    response = client.post("/api/volume", json={"volume": 5})

    assert response.status_code == 200
    assert response.get_json()["volume"] == 1.0

    response = client.post("/api/volume", json={"volume": -5})

    assert response.status_code == 200
    assert response.get_json()["volume"] == 0.0
