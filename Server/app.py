import json
import os
from flask import Flask, render_template, request, jsonify, send_from_directory
import pygame
from mutagen.oggvorbis import OggVorbis

app = Flask(__name__, template_folder='../GUI', static_folder='../GUI')

LANGUAGES = ['en', 'de', 'jp']
CATEGORIES = ['general', 'move', 'long_move', 'encounter', 'attack', 'ability', 'kill', 'death', 'respawn', 'recall']

current_file_dir = os.path.dirname(os.path.abspath(__file__))
SOUNDS_PATH = os.path.join(current_file_dir, 'static', 'sounds')

METADATA_PATH = os.path.join(current_file_dir, 'static', 'sounds_metadata.json')
with open(METADATA_PATH, 'r') as f:
    METADATA = json.load(f)

stop_playback = False
current_sound = None
current_volume = 1.0

def validate_form_data(language, category, sound, loop):
    missing_fields = []
    if language is None:
        missing_fields.append("language")
    if category is None:
        missing_fields.append("category")
    if sound is None:
        missing_fields.append("sound")
    if loop is None:
        missing_fields.append("loop")
    
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"
    return None

@app.route('/')
def index():
    return render_template('index.html', languages=LANGUAGES, categories=CATEGORIES)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_file_dir, 'static'), 'favicon.ico')


@app.route('/play', methods=['POST'])
def play_request():
    global stop_playback, current_sound
    stop_playback = False

    language = request.form['language']
    category = request.form['category']
    sound = request.form['sound']
    loop = request.form.get('loop', False) == "on"

    validation_error = validate_form_data(language, category, sound, loop)
    if validation_error:
        return f"Invalid form data: {validation_error}", 400

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
    global stop_playback, current_sound
    pygame.mixer.init()
    current_sound = pygame.mixer.Sound(file)
    
    # Set volume to 0 for the fade-in effect
    current_sound.set_volume(0)
    fade_in_time = 1000  # Fade-in time in milliseconds (1 second)
    
    current_sound.play(loops=-1 if loop else 0, fade_ms=fade_in_time)
    
    # Gradually increase the volume to the current volume
    start_ticks = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start_ticks < fade_in_time:
        if stop_playback:
            break  # Exit the loop if playback is stopped
        
        elapsed_time = pygame.time.get_ticks() - start_ticks
        volume = (elapsed_time / fade_in_time) * current_volume
        current_sound.set_volume(volume)
        pygame.time.Clock().tick(10)

    # If stop_playback was not triggered, set the volume to the desired level
    if not stop_playback:
        current_sound.set_volume(current_volume)

    # Continue playing the sound or stop if requested
    while pygame.mixer.get_busy() and not stop_playback:
        pygame.time.Clock().tick(10)
    
    if stop_playback:
        current_sound.stop()  # Ensure the sound stops immediately when requested
        stop_playback = False  # Reset the flag for future use

    if not loop:
        pygame.mixer.quit()
        current_sound = None

@app.route('/stop', methods=['POST'])
def stop_playback_request():
    global stop_playback
    stop_playback = True
    return 'Playback stopped', 200

@app.route('/volume', methods=['POST'])
def set_volume():
    global current_volume, current_sound
    volume = request.form.get('volume', type=float, default=1.0)
    current_volume = volume
    
    if current_sound:
        current_sound.set_volume(current_volume)

    return f'Volume set to {volume}', 200

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join('..', 'GUI'), filename)

@app.route('/sounds', methods=['GET'])
def get_sounds():
    language = request.args.get('language')
    category = request.args.get('category')

    if language not in LANGUAGES or category not in CATEGORIES:
        return jsonify({'error': 'Invalid language or category'}), 400

    sounds_path = os.path.join(SOUNDS_PATH, language, category)

    if not os.path.exists(sounds_path):
        return jsonify({'error': 'Sounds directory not found'}), 404

    sound_data = []
    for sound_file in os.listdir(sounds_path):
        if sound_file.endswith('.ogg'):
            sound_name = os.path.splitext(sound_file)[0]
            sound_file_path = os.path.join(sounds_path, sound_file)
            audio = OggVorbis(sound_file_path)  # Load the audio file
            sound_length = audio.info.length  # Get the length in seconds
            
            metadata = METADATA.get(sound_name, {})
            title = metadata.get('title', '')
            description = metadata.get('description', '')
            
            sound_data.append({
                'filename': sound_name,
                'title': title if title else 'Unknown Title',
                'description': description if description else 'No Description',
                'length': sound_length  # Add the length property
            })

    return jsonify(sound_data)

if __name__ == '__main__':
    app.run(host='192.168.2.128')
