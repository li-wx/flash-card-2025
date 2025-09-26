from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import csv
import os
import json
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-secret-key'

DATA_FILE = 'words.csv'
PROGRESS_FILE = 'progress.json'

# Helper to load words from CSV

def load_words():
    words = []
    with open(DATA_FILE, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            words.append({
                'word': row['word'],
                'definition': row['definition'],
                'S': random.uniform(19, 21),
                'T': '2000-01-01T00:00:00',
            })
    return words

# Helper to load/save progress

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding='utf-8') as f:
            return json.load(f)
    return None

def save_progress(progress):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

# Calculate M for each word
def calculate_memory(words):
    now = datetime.now()
    for w in words:
        T = datetime.fromisoformat(w['T'])
        t = (now - T).total_seconds()
        w['M'] = w['S'] / t if t > 0 else float('inf')
    return words

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
    word = pick_word(words)
    # Format T for display
    T_display = word['T']
    try:
        T_display = datetime.fromisoformat(word['T']).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return render_template('flashcard.html', word=word, S=word['S'], T=T_display, M=round(word['M'], 3))

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
                w['S'] *= 10000
                msg = "OK, it won’t show up in the foreseeable future."
            elif action == 'B':
                w['S'] *= 1.5
                msg = "Good, it will show up less frequently."
            else:
                w['S'] *= 0.5
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
