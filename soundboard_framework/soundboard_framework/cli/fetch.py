"""`soundboard-fetch` — scrape voice lines + metadata from a wiki audio page.

Generalizes the old Viego-specific audio_downloader.py: the source URL and
category-name mapping now come from the character's character.toml
[voice_scraper] section instead of being hardcoded per-character.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from soundboard_framework.config import load_character

FALLBACK_CATEGORY = "general"


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?"<>|:]', "_", name)


def normalize_category(raw_category: str, category_map: dict[str, str]) -> str:
    for key, value in category_map.items():
        if key.lower() in raw_category.lower():
            return value
    return FALLBACK_CATEGORY


def fetch_html(url: str) -> BeautifulSoup:
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_and_download(
    soup: BeautifulSoup,
    category_map: dict[str, str],
    out_base: Path,
    language: str,
) -> dict:
    metadata: dict = {}
    for header in soup.find_all(["h2", "h3", "h4"]):
        header_text = header.get_text(strip=True)
        current_category = normalize_category(header_text, category_map)

        sibling = header.find_next_sibling()
        while sibling and sibling.name not in ["h2", "h3", "h4"]:
            for audio in sibling.find_all("audio"):
                source = audio.find("source")
                if not source:
                    continue
                src = source.get("src")
                if not src or not src.endswith(".ogg"):
                    continue

                match = re.search(r".*/(.*)\.ogg", src)
                if not match:
                    print(f"Could not extract filename from src: {src}")
                    continue
                filename = sanitize_filename(match.group(1))

                out_dir = out_base / language / current_category
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{filename}.ogg"

                print(f"Downloading {filename}.ogg -> {current_category}")
                try:
                    audio_resp = requests.get(src, stream=True)
                    audio_resp.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in audio_resp.iter_content(1024):
                            f.write(chunk)
                except Exception as exc:
                    print(f"Error downloading {src}: {exc}")
                    continue

                parent_text = audio.find_parent().get_text(" ", strip=True)
                metadata[filename] = {"title": header_text, "description": parent_text}

            sibling = sibling.find_next_sibling()
    return metadata


def save_metadata(metadata: dict, metadata_path: Path) -> None:
    existing: dict = {}
    if metadata_path.is_file():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
    existing.update(metadata)
    metadata_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch voice lines + metadata for a character.")
    parser.add_argument("--character-dir", required=True, type=Path, help="Path to the character's project folder.")
    parser.add_argument("--language", default="en", help="Language subfolder to save sounds under (default: en).")
    args = parser.parse_args()

    character = load_character(args.character_dir)
    if not character.voice_scraper_url:
        raise SystemExit(
            f"{args.character_dir}/character.toml has no [voice_scraper] url set; nothing to fetch."
        )

    sounds_dir = args.character_dir / "sounds"
    metadata_path = sounds_dir / "sounds_metadata.json"

    soup = fetch_html(character.voice_scraper_url)
    metadata = extract_and_download(soup, character.voice_scraper_category_map, sounds_dir, args.language)
    save_metadata(metadata, metadata_path)
    print(f"Done. {len(metadata)} sounds downloaded/updated, metadata written to {metadata_path}")


if __name__ == "__main__":
    main()
