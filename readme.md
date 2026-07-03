# Viego Sound Player

A soundboard for a Viego cosplay. The server (e.g. a Raspberry Pi hidden in
the costume, connected to a speaker) plays the sounds; any phone on the same
network is a remote control at `http://<server-ip>:5000`.

## What changed in v2 (full rewrite)

**Backend**
- Playback no longer blocks the request thread. The old `/play` handler
  busy-waited until the sound finished — with loop enabled it *never*
  returned. Now `play()` starts the sound and returns immediately.
- Audio engine replaced: pygame/SDL is gone in favour of
  **sounddevice + soundfile** (PortAudio + libsndfile). Looping is
  sample-accurate and gapless (the loop wrap happens inside the render
  callback), toggling loop never interrupts playback, the reported position
  is frame-exact rather than a wall-clock estimate, and fades are computed
  per sample. mutagen was dropped too — soundfile reads durations.
- One `Player` class with a lock instead of three globals — safe with
  concurrent requests (two phones can control the same speaker).
- The sound library is scanned **once** at startup (durations + metadata
  cached). The old `/sounds` route re-parsed every `.ogg` on every request.
- Sounds are addressed by catalog key, never by user-supplied file paths —
  the path-traversal hole is closed.
- Languages and categories are auto-discovered from the folder structure.
  Drop a new `jp/` folder in and it appears (or call `POST /api/reload`).
- Proper JSON API with real error codes instead of plain-text responses.

**Frontend**
- Mobile-first one-tap soundboard instead of three dropdowns — tap a tile to
  play, tap it again to stop. Big targets that work with gloves.
- ★ Favorites (pin the lines you use most at cons) and a Recent tab, stored
  on the device.
- Search across titles and descriptions.
- Live progress from the server: the page polls `/api/status`, so the
  progress bar is accurate and every connected device shows the same state.
- Installable PWA: "Add to Home Screen" gives a fullscreen app that opens
  instantly (app shell is cached by a service worker). Screen wake lock keeps
  the panel awake while open.
- Bootstrap and Font Awesome removed (~3 MB of unused assets) — the UI is
  ~15 KB of hand-written HTML/CSS/JS, themed after the Shadow Isles.

## Project structure

```
viego_sound_player/
├── server/
│   ├── app.py          # Flask app + JSON API
│   ├── config.py       # paths, category order/labels, fades, host/port
│   ├── library.py      # scans sounds/, caches metadata & durations
│   ├── player.py       # thread-safe non-blocking sounddevice + soundfile playback
│   ├── requirements.txt
│   └── static/
│       ├── index.html, app.js, styles.css
│       ├── manifest.webmanifest, sw.js, icon-*.png
│       └── sounds/
│           ├── sounds_metadata.json
│           ├── en/<category>/*.ogg
│           ├── de/<category>/*.ogg
│           └── music/*.ogg        # shared across languages
├── tools/
│   ├── audio_downloader.py   # scrape voice lines from the wiki
│   └── json_generator.py     # regenerate metadata skeleton
└── README.md
```

## Setup

```bash
cd server
python -m venv venv && source venv/bin/activate   # optional
pip install -r requirements.txt
python app.py
```

Open `http://<server-ip>:5000` on your phone and add it to the home screen.

Environment variables: `VIEGO_HOST` (default `0.0.0.0`), `VIEGO_PORT`
(default `5000`).

## Raspberry Pi note

`sounddevice` needs the PortAudio system library:

```bash
sudo apt install libportaudio2
```

`soundfile` ships with libsndfile bundled in its wheel — no extra packages.

## API

| Method | Route          | Body / params                  | Purpose                          |
|--------|----------------|--------------------------------|----------------------------------|
| GET    | `/api/library` | —                              | Full catalog (languages, categories, sounds with durations) |
| GET    | `/api/status`  | —                              | Now playing, position, loop, volume |
| POST   | `/api/play`    | `{"key": "en/kill/…", "loop": false}` | Play a sound (replaces current) |
| POST   | `/api/stop`    | —                              | Fade out and stop                |
| POST   | `/api/volume`  | `{"volume": 0.0–1.0}`          | Set server volume                |
| POST   | `/api/loop`    | `{"loop": true}`               | Toggle looping (never interrupts playback)  |
| POST   | `/api/reload`  | —                              | Rescan the sounds folder         |

## Cosplay / on-the-go tips

- **No venue Wi-Fi needed:** run a Wi-Fi hotspot on the Pi (or your phone)
  so the phone ↔ Pi link is self-contained. Give the Pi a static IP and
  bookmark it.
- **Autostart:** run the server as a `systemd` service so it comes up when
  the Pi boots — no keyboard/monitor required.
- Pin your go-to taunts, laughs and the dance music to ★ Favorites the night
  before; at the con you're one tap away.
- Loop the dance music or E-mist SFX from the Music tab for ambient effect.

Example systemd unit (`/etc/systemd/system/viego.service`):

```ini
[Unit]
Description=Viego Sound Player
After=network.target sound.target

[Service]
WorkingDirectory=/home/pi/viego_sound_player/server
ExecStart=/home/pi/viego_sound_player/server/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Adding sounds

Drop `.ogg` files into `server/static/sounds/<language>/<category>/` (or
`sounds/music/` for language-independent audio), optionally add a
`title`/`description` entry in `sounds_metadata.json`, then hit
`POST /api/reload` or restart. New languages and categories are picked up
automatically.
