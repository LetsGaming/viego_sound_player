"""Central configuration for the Viego Sound Player server."""
from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
SOUNDS_DIR = os.path.join(STATIC_DIR, "sounds")
METADATA_PATH = os.path.join(SOUNDS_DIR, "sounds_metadata.json")

# Categories that live directly under SOUNDS_DIR and are shared across
# languages (no per-language subfolder).
LANGUAGE_INDEPENDENT_CATEGORIES = {"music"}

# Display order for categories in the UI. Categories discovered on disk that
# are not listed here are appended alphabetically.
CATEGORY_ORDER = [
    "general",
    "move",
    "long_move",
    "encounter",
    "attack",
    "ability",
    "kill",
    "death",
    "respawn",
    "recall",
    "music",
]

# Human-friendly category labels.
CATEGORY_LABELS = {
    "general": "General",
    "move": "Move",
    "long_move": "Long move",
    "encounter": "Encounter",
    "attack": "Attack",
    "ability": "Ability",
    "kill": "Kill",
    "death": "Death",
    "respawn": "Respawn",
    "recall": "Recall",
    "music": "Music & SFX",
    "unsorted": "Unsorted",
}

# Fade durations in milliseconds.
FADE_IN_MS = 400
FADE_OUT_MS = 300

# Network defaults. 0.0.0.0 so a phone on the same network can connect.
HOST = os.environ.get("VIEGO_HOST", "0.0.0.0")
PORT = int(os.environ.get("VIEGO_PORT", "5000"))
