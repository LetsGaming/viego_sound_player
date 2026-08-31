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

    character_dir = Path(character_dir).resolve()
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
