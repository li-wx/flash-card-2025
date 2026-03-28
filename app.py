from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import csv
import os
import json
import random
import re
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
PROGRESS_DIR = PROGRESS_FILE.parent / 'user_progress'
USERS_FILE = PROGRESS_FILE.parent / 'users.json'
ADMIN_PASSWORD = os.getenv('FLASHCARD_ADMIN_PASSWORD')


def normalize_user_id(raw_value):
    cleaned = re.sub(r'[^a-zA-Z0-9_-]+', '_', (raw_value or '').strip())
    return cleaned.strip('_').lower()[:64]


def mask_display_name(display_name):
    value = (display_name or '').strip()
    if not value:
        return '***'
    if len(value) == 1:
        return '*'
    if len(value) == 2:
        return value[0] + '*'
    return value[0] + ('*' * (len(value) - 2)) + value[-1]


def load_allowed_users():
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        return []

    with USERS_FILE.open(encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        users = [normalize_user_id(user) for user in data]
    else:
        users = []

    return sorted({user for user in users if user})


def save_allowed_users(users):
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    normalized = sorted({normalize_user_id(user) for user in users if normalize_user_id(user)})
    with USERS_FILE.open('w', encoding='utf-8') as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)


def is_allowed_user(user_id):
    if not user_id:
        return False
    return normalize_user_id(user_id) in load_allowed_users()


def get_current_user_id():
    user_id = session.get('user_id')
    if not user_id:
        return None
    normalized_user_id = normalize_user_id(user_id)
    if not is_allowed_user(normalized_user_id):
        session.pop('user_id', None)
        session.pop('display_name', None)
        return None
    return normalized_user_id


def is_admin():
    return bool(session.get('is_admin'))


def get_user_progress_file_path(user_id):
    return PROGRESS_DIR / f'{user_id}.json'


def ensure_progress_storage_ready(user_id):
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

    user_progress_file = get_user_progress_file_path(user_id)

    if user_progress_file.exists():
        return

    # Migrate legacy single-user progress to a special "legacy" account once.
    legacy_target = get_user_progress_file_path('legacy')
    if LEGACY_PROGRESS_FILE.exists() and not legacy_target.exists():
        shutil.copy2(LEGACY_PROGRESS_FILE, legacy_target)


def ensure_admin_access():
    if not is_admin():
        return redirect(url_for('admin_login'))
    return None

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

def load_progress(user_id):
    ensure_progress_storage_ready(user_id)
    progress_file = get_user_progress_file_path(user_id)
    if progress_file.exists():
        with progress_file.open(encoding='utf-8') as f:
            return json.load(f)
    return None

def save_progress(user_id, progress):
    ensure_progress_storage_ready(user_id)
    progress_file = get_user_progress_file_path(user_id)
    with progress_file.open('w', encoding='utf-8') as f:
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
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('login'))

    # Load progress or initialize
    progress = load_progress(user_id)
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
        masked_username=mask_display_name(session.get('display_name', user_id)),
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        display_name = (request.form.get('username') or '').strip()
        user_id = normalize_user_id(display_name)
        if not user_id:
            error = 'Please enter a valid username.'
        elif not is_allowed_user(user_id):
            error = 'This user does not exist. Please contact an administrator.'
        else:
            session['user_id'] = user_id
            session['display_name'] = display_name
            return redirect(url_for('index'))
    return render_template('login.html', error=error)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        submitted_password = request.form.get('password') or ''
        if not ADMIN_PASSWORD:
            error = 'Admin password is not configured. Set FLASHCARD_ADMIN_PASSWORD.'
        elif submitted_password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_users'))
        else:
            error = 'Incorrect admin password.'
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    redirect_response = ensure_admin_access()
    if redirect_response:
        return redirect_response

    error = None
    message = None
    if request.method == 'POST':
        action = request.form.get('action') or 'create'
        users = load_allowed_users()

        if action == 'create':
            display_name = (request.form.get('username') or '').strip()
            user_id = normalize_user_id(display_name)
            if not user_id:
                error = 'Please enter a valid username.'
            elif user_id in users:
                error = f'User "{user_id}" already exists.'
            else:
                users.append(user_id)
                save_allowed_users(users)
                message = f'User "{user_id}" was created.'
        elif action == 'delete':
            user_id = normalize_user_id(request.form.get('user_id'))
            delete_progress = bool(request.form.get('delete_progress'))
            if not user_id:
                error = 'Please choose a valid user to delete.'
            elif user_id not in users:
                error = f'User "{user_id}" does not exist.'
            else:
                users.remove(user_id)
                save_allowed_users(users)
                message = f'User "{user_id}" was deleted from allowed users.'

                if delete_progress:
                    progress_file = get_user_progress_file_path(user_id)
                    if progress_file.exists():
                        progress_file.unlink()
                        message += ' Progress data file was also deleted.'
                    else:
                        message += ' No progress data file was found.'
        else:
            error = 'Unsupported action.'

    return render_template(
        'admin_users.html',
        users=load_allowed_users(),
        error=error,
        message=message,
        is_admin=is_admin(),
    )


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('display_name', None)
    return redirect(url_for('login'))

@app.route('/review', methods=['POST'])
def review():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'msg': 'Please log in first.'}), 401

    data = request.json
    word = data['word']
    action = data['action']
    progress = load_progress(user_id)
    if progress is None:
        progress = load_words()
    msg = 'Word not found. Loading next card.'
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
    save_progress(user_id, progress)
    # Pick next word
    words = calculate_memory(progress)
    next_word = pick_word(words)
    return jsonify({'msg': msg, 'word': next_word})

if __name__ == '__main__':
    app.run(debug=True)
