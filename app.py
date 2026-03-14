from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import csv
import os
import json
import random
from datetime import datetime
import math
from pathlib import Path
import shutil

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-secret-key'

DATA_FILE = 'words.csv'
TARGET_NUMBER_REVIEW = 20 # A word is considered learned if estimated to be recalled 20 times


def get_progress_file_path():
    configured_path = os.getenv('FLASHCARD_PROGRESS_FILE')
    if configured_path:
        return Path(configured_path)

    if os.getenv('WEBSITE_INSTANCE_ID'):
        return Path('/home/data/progress.json')

    return Path(__file__).resolve().parent / 'progress.json'


PROGRESS_FILE = get_progress_file_path()
LEGACY_PROGRESS_FILE = Path(__file__).resolve().parent / 'progress.json'


def ensure_progress_storage_ready():
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if PROGRESS_FILE.exists() or PROGRESS_FILE == LEGACY_PROGRESS_FILE:
        return

    if LEGACY_PROGRESS_FILE.exists():
        shutil.copy2(LEGACY_PROGRESS_FILE, PROGRESS_FILE)

# Helper to load words from CSV

def load_words():
    words = []
    with open(DATA_FILE, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            words.append({
                'word': row['word'],
                'definition': row['definition'],
                'S': random.uniform(4.001, 4.999),
                'T': '2000-01-01T00:00:00',
            })
    return words

# Helper to load/save progress

def load_progress():
    ensure_progress_storage_ready()
    if PROGRESS_FILE.exists():
        with PROGRESS_FILE.open(encoding='utf-8') as f:
            return json.load(f)
    return None

def save_progress(progress):
    ensure_progress_storage_ready()
    with PROGRESS_FILE.open('w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

# Calculate M for each word
def calculate_memory(words):
    now = datetime.now()
    for w in words:
        T = datetime.fromisoformat(w['T'])
        t = (now - T).total_seconds()
        w['M'] = w['S'] / t if t > 0 else float('inf')
    return words

def estimate_words_learned(words):
    if not words:
        return 0.0
    total = 0.0
    for w in words:
        try:
            strength = float(w.get('S', 0))
        except (TypeError, ValueError):
            strength = 20.0
        total += min(math.log(strength, 2), TARGET_NUMBER_REVIEW)
    return total / TARGET_NUMBER_REVIEW

# Pick word with M closest to 1
def pick_word(words):
    return min(words, key=lambda w: abs(w['M'] - 1))

@app.route('/')
def index():
    # Load progress or initialize
    progress = load_progress()
    if progress is None:
        words = load_words()
    else:
        words = progress
    words = calculate_memory(words)
    estimated_learned = estimate_words_learned(words)
    word = pick_word(words)
    # Format T for display
    T_display = word['T']
    try:
        T_display = datetime.fromisoformat(word['T']).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return render_template(
        'flashcard.html',
        word=word,
        S=round(word['S'], 3),
        T=T_display,
        M=round(word['M'], 3),
        estimated_learned=round(estimated_learned, 3),
    )

@app.route('/review', methods=['POST'])
def review():
    data = request.json
    word = data['word']
    action = data['action']
    progress = load_progress()
    if progress is None:
        progress = load_words()
    for w in progress:
        if w['word'] == word:
            if action == 'A':
                w['S'] *= 20000
                msg = "OK, it won’t show up in the foreseeable future."
            elif action == 'B':
                w['S'] *= 2.0
                msg = "Good, it will show up less frequently."
            else:
                w['S'] *= 0.3
                msg = "No problem, it will show up more frequently."
            w['T'] = datetime.now().isoformat()
            break
    save_progress(progress)
    # Pick next word
    words = calculate_memory(progress)
    next_word = pick_word(words)
    return jsonify({'msg': msg, 'word': next_word})

if __name__ == '__main__':
    app.run(debug=True)
