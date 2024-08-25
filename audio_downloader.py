import requests
from bs4 import BeautifulSoup
import re
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

def download_ogg_files(ogg_links, download_path):
    """Download .ogg files from the provided links."""
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    for link in ogg_links:
        filename = re.search(r".*/(.*)\.ogg", link).group(1)
        if not "Original" in filename:
            continue  # Skip files without "Original" in the filename

        full_path = os.path.join(download_path, filename + ".ogg")
        print(f"Downloading: {filename}.ogg")

        try:
            ogg_response = requests.get(link, stream=True)
            ogg_response.raise_for_status()

            with open(full_path, "wb") as f:
                for chunk in ogg_response.iter_content(1024):
                    f.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {filename}: {e}")

    print("Download complete!")

def main():
    url = "https://leagueoflegends.fandom.com/wiki/Viego/LoL/Audio"
    download_path = "C:\\Users\\Domenic\\Downloads\\viego_sounds"

    content = fetch_webpage(url)
    soup = parse_html(content)
    ogg_links = extract_ogg_links(soup)
    download_ogg_files(ogg_links, download_path)

if __name__ == "__main__":
    main()
