# Soundboard Framework

A reusable framework for cosplay/character soundboards: a Flask server
plays sounds (e.g. on a Raspberry Pi hidden in a costume, connected to a
speaker), and any phone on the same network is a remote control at
`http://<server-ip>:5000`. Playback is non-blocking, sample-accurate
gapless looping via `sounddevice`/`soundfile`, and the frontend is an
installable PWA.

**Viego is the reference character** — the original cosplay this
framework was extracted from — but the server, player, and PWA shell are
entirely character-agnostic. A new character needs only a `character.toml`,
an `icons/` folder, and a `sounds/` folder of `.ogg` files.

## Project structure

```
viego_sound_player/
├── soundboard_framework/       # the installable core package
│   ├── soundboard_framework/
│   │   ├── app.py              # create_app(character_dir)
│   │   ├── config.py           # Character dataclass + character.toml loader
│   │   ├── library.py          # scans sounds/, caches metadata & durations
│   │   ├── player.py           # thread-safe non-blocking playback engine
│   │   ├── static/              # shared app.js, sw.js, styles.css
│   │   ├── templates/           # index.html.jinja, manifest.webmanifest.jinja
│   │   └── cli/                 # soundboard-serve, soundboard-fetch, soundboard-new
│   └── tests/
└── characters/
    └── viego/
        ├── character.toml       # branding, theme, categories, fades
        ├── theme.css            # optional extra CSS (Viego's glow animation)
        ├── icons/                # favicon.ico, icon-192.png, icon-512.png
        ├── sounds/                # sounds_metadata.json, en/, de/, music/
        ├── requirements.txt
        └── run.py
```

## Setup (Viego, or any existing character)

```bash
cd characters/viego
python -m venv venv && source venv/bin/activate   # optional
pip install -r requirements.txt
python run.py
```

Open `http://<server-ip>:5000` on your phone and add it to the home screen.

Environment variables: `SOUNDBOARD_HOST` (default `0.0.0.0`),
`SOUNDBOARD_PORT` (default `5000`) — or pass `--host`/`--port` to
`soundboard-serve`.

## Creating a new character

```bash
pip install -e soundboard_framework
soundboard-new "My Character"
cd characters/my_character
# edit character.toml (theme colors, category labels, fade timings)
# drop icons into icons/ (favicon.ico, icon-192.png, icon-512.png)
# drop .ogg files into sounds/<language>/<category>/, or:
soundboard-fetch --character-dir . --language en   # if [voice_scraper] is configured
pip install -r requirements.txt
python run.py
```

New languages and categories are auto-discovered from the `sounds/`
folder structure — drop a new language folder in and call
`POST /api/reload` (or restart) to pick it up.

## Raspberry Pi note

`sounddevice` needs the PortAudio system library:

```bash
sudo apt install libportaudio2
```

`soundfile` ships with libsndfile bundled in its wheel — no extra packages.

## API

| Method | Route          | Body / params                  | Purpose                          |
|--------|----------------|--------------------------------|-----------------------------------|
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
- Pin your go-to lines to ★ Favorites the night before; at the con you're
  one tap away.

Example systemd unit (`/etc/systemd/system/viego.service`):

```ini
[Unit]
Description=Viego Sound Player
After=network.target sound.target

[Service]
WorkingDirectory=/home/pi/viego_sound_player/characters/viego
ExecStart=/home/pi/viego_sound_player/characters/viego/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Framework development

```bash
pip install -e "soundboard_framework[dev]"
pytest soundboard_framework/tests
```
