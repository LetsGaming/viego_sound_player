# Viego Sound Player

A soundboard for a Viego cosplay. The server (e.g. a Raspberry Pi hidden in
the costume, connected to a speaker) plays the sounds; any phone on the same
network is a remote control at `http://<server-ip>:5000`.

This project is a "character" built on the
[soundboard_framework](https://github.com/LetsGaming/soundboard_framework)
package: `character.toml` holds Viego's branding/theme/categories, `sounds/`
and `icons/` hold the assets, and `run.py` is a thin entrypoint. The server,
player, and PWA shell themselves live in the framework package — see that
repo if you want to build a soundboard for a different character.

## Project structure

```
viego_sound_player/
├── character.toml       # branding, theme, categories, fades
├── theme.css             # Viego's glow-pulse animation (extra CSS)
├── icons/                 # favicon.ico, icon-192.png, icon-512.png
├── sounds/                 # sounds_metadata.json, en/, de/, music/
├── requirements.txt
└── run.py
```

## Setup

```bash
python -m venv venv && source venv/bin/activate   # optional
pip install -r requirements.txt
python run.py
```

Open `http://<server-ip>:5000` on your phone and add it to the home screen.

Environment variables: `SOUNDBOARD_HOST` (default `0.0.0.0`),
`SOUNDBOARD_PORT` (default `5000`) — or pass `--host`/`--port` to
`soundboard-serve`.

## Raspberry Pi note

`sounddevice` needs the PortAudio system library:

```bash
sudo apt install libportaudio2
```

`soundfile` ships with libsndfile bundled in its wheel — no extra packages.

## API

| Method | Route          | Body / params                  | Purpose                          |
|--------|----------------|---------------------------------|-----------------------------------|
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
- Loop the dance music or E-mist SFX from the Music tab for ambient effect.

Example systemd unit (`/etc/systemd/system/viego.service`):

```ini
[Unit]
Description=Viego Sound Player
After=network.target sound.target

[Service]
WorkingDirectory=/home/pi/viego_sound_player
ExecStart=/home/pi/viego_sound_player/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Adding sounds

Drop `.ogg` files into `sounds/<language>/<category>/` (or `sounds/music/`
for language-independent audio), optionally add a `title`/`description`
entry in `sounds/sounds_metadata.json`, then hit `POST /api/reload` or
restart. New languages and categories are picked up automatically.

## Updating the framework

This project depends on `soundboard_framework` via a git URL
(`requirements.txt`), so `pip install -r requirements.txt --upgrade` pulls
in the latest framework release.
