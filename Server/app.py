import os
import pygame
from flask import Flask, render_template, request, jsonify, send_from_directory

# Create Flask app with custom template_folder path and static_folder path
app = Flask(__name__, template_folder='../GUI', static_folder='../GUI')

# Define the available languages and categories
LANGUAGES = ['en', 'de', 'jp']
CATEGORIES = ['general', 'move', 'long_move', 'encounter', 'attack', 'ability', 'kill', 'death']

# Get the directory of the current file and construct the SOUNDS_PATH
current_file_dir = os.path.dirname(os.path.abspath(__file__))
SOUNDS_PATH = os.path.join(current_file_dir, 'static', 'sounds')

# Set a temporary directory for pydub to avoid permission issues
temp_dir = os.path.join(current_file_dir, 'temp')

# Ensure the temp directory exists
os.makedirs(temp_dir, exist_ok=True)

# Global variable to control playback
stop_playback = False

@app.route('/')
def index():
    return render_template('index.html', languages=LANGUAGES, categories=CATEGORIES)

@app.route('/play', methods=['POST'])
def play_request():
    global stop_playback
    stop_playback = False
    
    language = request.form['language']
    category = request.form['category']
    sound = request.form['sound']
    loop = request.form['loop'] == "on"

    sound_path = os.path.join(SOUNDS_PATH, language, category, f"{sound}.ogg")

    if os.path.exists(sound_path):
        try:
            play_sound(sound_path, loop)
            return f'Played sound: {sound} in {language} from {category} category', 200
        except Exception as e:
            return f'Error playing sound: {e}', 500
    else:
        return 'Sound not found', 404

def play_sound(file: str, loop: bool):
    global stop_playback
    pygame.mixer.init()
    sound = pygame.mixer.Sound(file)

    while not stop_playback:
        sound.play(loops=-1 if loop else 0)
        while pygame.mixer.get_busy() and not stop_playback:
            pygame.time.Clock().tick(10)
        if not loop:
            break

    pygame.mixer.quit()

# API endpoint to stop playback
@app.route('/stop', methods=['POST'])
def stop_playback_request():
    global stop_playback
    stop_playback = True
    return 'Playback stopped', 200

# Serve static files from the GUI directory
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join('..', 'GUI'), filename)

# API endpoint to get available sounds for a specific language and category
@app.route('/sounds', methods=['GET'])
def get_sounds():
    language = request.args.get('language')
    category = request.args.get('category')

    if language not in LANGUAGES or category not in CATEGORIES:
        return jsonify({'error': 'Invalid language or category'}), 400

    sounds_path = os.path.join(SOUNDS_PATH, language, category)
    
    if not os.path.exists(sounds_path):
        return jsonify({'error': 'Sounds directory not found'}), 404

    sounds = [os.path.splitext(sound)[0] for sound in os.listdir(sounds_path) if sound.endswith('.ogg')]

    return jsonify(sounds)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
