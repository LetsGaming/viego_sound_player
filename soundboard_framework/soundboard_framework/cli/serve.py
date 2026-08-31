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
