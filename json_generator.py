import requests
from bs4 import BeautifulSoup
import re
import json
import os

def fetch_webpage(url):
    """Fetch the content of the webpage."""
    response = requests.get(url)
    response.raise_for_status()
    return response.content

def parse_html(content):
    """Parse HTML content and return BeautifulSoup object."""
    return BeautifulSoup(content, "html.parser")

def extract_ogg_links(soup):
    """Extract all .ogg links from the parsed HTML."""
    ogg_links = []
    for link in soup.find_all("source"):
        src = link.get("src")
        if src and re.search(r".*/(.*)\.ogg", src):
            ogg_links.append(src)
    return ogg_links

def generate_json(ogg_links):
    """Generate a JSON structure for all audio files containing 'Original'."""
    audio_json = {}
    for link in ogg_links:
        filename = re.search(r".*/(.*)\.ogg", link).group(1)
        if "Original" in filename:
            # Create a JSON entry with the filename as the key
            audio_json[filename] = {
                "title": filename,
                "description": ""
            }

    return audio_json

def save_json_to_file(audio_json, file_path):
    """Save the JSON structure to a file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as json_file:
        json.dump(audio_json, json_file, indent=4)
    print(f"JSON saved to {file_path}")

def main():
    url = "https://leagueoflegends.fandom.com/wiki/Viego/LoL/Audio"
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(current_file_dir, 'server', 'static', 'sounds_metadata.json')

    content = fetch_webpage(url)
    soup = parse_html(content)
    ogg_links = extract_ogg_links(soup)
    
    # Generate JSON structure
    audio_json = generate_json(ogg_links)
    
    # Save the JSON to a file
    save_json_to_file(audio_json, json_file_path)

if __name__ == "__main__":
    main()
