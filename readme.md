# Viego Sound Player

A Flask-based web application that allows the server to play various sound files based on user input. The application serves an interface where users can select a language, category, and specific sound, which is then played on the server.

## Features

- **Language Selection:** Choose from available languages (English, German, Japanese).
- **Category Selection:** Choose from various sound categories (move, long_move, encounter, attack, ability, kill).
- **Server-Side Audio Playback:** Plays selected sound files on the server using `pygame`.

## Prerequisites

- **Python 3.10 or later**: Ensure Python is installed and added to your system's PATH.

### Installing Dependencies

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/viego_sound_player.git
   cd viego_sound_player
   ```

2. **Set Up a Virtual Environment (Optional but Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Installation of `pygame`

- `pygame` is included in the `requirements.txt` file, so no additional installation steps are needed beyond the `pip install -r requirements.txt` command.

## Usage

1. **Run the Flask Application:**
   ```bash
   python app.py
   ```

2. **Access the Web Interface:**
   Open a web browser and go to `http://127.0.0.1:5000/`.

3. **Play Sounds:**
   - Select a language and category from the dropdown menus.
   - Choose a specific sound to play on the server.

## Project Structure

```
viego_sound_player/
│
├── Server/
│   ├── app.py                # Main Flask application
│   ├── static/
│   │   └── sounds/           # Directory containing sound files organized by language and category
│   └── temp/                 # Temporary directory for pydub (not used with pygame)
├── GUI/
│   └── index.html            # HTML template for the web interface
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

## Troubleshooting

- **`pygame` Issues:**
  Ensure `pygame` is installed correctly. If you encounter issues, verify your installation with:
  ```bash
  python -m pygame.examples.aliens
  ```

- **Permission Issues:**
  If you run into permission errors while playing sounds, ensure the server process has the necessary permissions to access and play audio files.

## Acknowledgments

- This project uses [Flask](https://flask.palletsprojects.com/) for the web framework.
- [pygame](https://www.pygame.org/) is used for audio playback.
- Special thanks to the creators and maintainers of these libraries.
```