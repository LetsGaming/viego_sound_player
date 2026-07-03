import requests
from bs4 import BeautifulSoup
import re
import os
import json

# --- Config ---
URL = "https://wiki.leagueoflegends.com/en-us/Viego/Audio"
BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server", "static", "sounds")
LANGUAGE = "jp"  # change to 'en', 'de' if needed

CATEGORY_MAP = {
    "Joke": "general",
    "Taunt": "general",
    "Ban": "general",
    "Movement": "move",
    "Long movement": "long_move",
    "First Encounter": "encounter",
    "Attack": "attack",
    "Ability": "ability",
    "Kill": "kill",
    "Death": "death",
    "Respawn": "respawn",
    "Recall": "recall",
}

METADATA_FILE = os.path.join(BASE_PATH, "sounds_metadata.json")
metadata = {}

# --- Helpers ---
def fetch_html(url):
    r = requests.get(url)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def normalize_category(raw_category):
    """Map wiki header text into one of the fixed categories."""
    for key, value in CATEGORY_MAP.items():
        if key.lower() in raw_category.lower():
            return value
    return "general"  # fallback

def sanitize_filename(name):
    return re.sub(r"[\\/*?\"<>|:]", "_", name)

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# --- Main Extraction ---
def extract_and_download(soup):
    current_category = "general"

    # Go through headers and their following lists/tables
    for header in soup.find_all(["h2", "h3", "h4"]):
        header_text = header.get_text(strip=True)
        current_category = normalize_category(header_text)

        # Find next sibling elements that may contain audios
        sibling = header.find_next_sibling()
        while sibling and sibling.name not in ["h2", "h3", "h4"]:
            for audio in sibling.find_all("audio"):
                source = audio.find("source")
                if not source:
                    continue
                src = source.get("src")
                if not src.endswith(".ogg"):
                    continue

                match = re.search(r".*/(.*)\.ogg", src)
                if not match:
                    print(f"Could not extract filename from src: {src}")
                    continue
                filename = match.group(1)
                safe_filename = sanitize_filename(filename)

                out_dir = os.path.join(BASE_PATH, LANGUAGE, current_category)
                ensure_dir(out_dir)
                out_path = os.path.join(out_dir, safe_filename + ".ogg")

                print(f"Downloading {safe_filename}.ogg -> {current_category}")

                # Download file
                try:
                    audio_resp = requests.get(src, stream=True)
                    audio_resp.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in audio_resp.iter_content(1024):
                            f.write(chunk)
                except Exception as e:
                    print(f"Error downloading {src}: {e}")
                    continue

                # Extract nearby text for metadata
                parent_text = audio.find_parent().get_text(" ", strip=True)
                metadata[safe_filename] = {
                    "title": header_text,
                    "description": parent_text
                }

            sibling = sibling.find_next_sibling()

def save_metadata():
    ensure_dir(os.path.join(BASE_PATH, LANGUAGE))
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

# --- Run ---
def main():
    soup = fetch_html(URL)
    extract_and_download(soup)
    save_metadata()
    print("All done! Sounds + metadata ready.")

if __name__ == "__main__":
    main()
