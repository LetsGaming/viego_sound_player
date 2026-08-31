"""Entrypoint for the Viego soundboard. Run with: python run.py"""
from pathlib import Path

from soundboard_framework.cli.serve import run

if __name__ == "__main__":
    run(character_dir=Path(__file__).parent)
