"""Viego Sound Player — Flask server.

Serves the mobile-first control panel and a small JSON API. All playback
happens on the server (e.g. a Raspberry Pi in the costume with a speaker);
any phone on the same network is a remote control. Multiple clients stay in
sync through GET /api/status.
"""
from __future__ import annotations

import logging

from flask import Flask, jsonify, request, send_from_directory

import config
from library import Library
from player import Player

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("viego")

app = Flask(__name__, static_folder=config.STATIC_DIR, static_url_path="/static")

library = Library()
library.load()

player = Player()
player.init()


# -- pages -------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(config.STATIC_DIR, "index.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(config.STATIC_DIR, "favicon.ico")


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(config.STATIC_DIR, "manifest.webmanifest")


@app.route("/sw.js")
def service_worker():
    # Served from root scope so the PWA can control the whole app.
    return send_from_directory(config.STATIC_DIR, "sw.js")


# -- API ----------------------------------------------------------------------

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


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, threaded=True)
