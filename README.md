# Flashcard Web App

A simple Flask web app for spaced repetition flashcards using a CSV word list. Tracks your memory strength and review time for each word, and saves your progress between sessions.

## How to Run

1. Make sure you have Python and Flask installed (already set up by requirements.txt).
2. Run the app:
   
   ```sh
   python app.py
   ```
   or use the VS Code Run/Debug button.
3. Open your browser to http://127.0.0.1:5000/

## Features
- Loads words and definitions from `words.csv` (definition in Chinese)
- Tracks memory strength (S) and last review time (T) for each word
- Picks the word you’re most likely to forget next
- Lets you review, mark as remembered, or mark as forgotten
- Saves your progress in `progress.json`
- Pronunciation button for each word

## File Structure
- `app.py` — Flask backend
- `templates/flashcard.html` — Main UI
- `words.csv` — Word list
- `progress.json` — User progress (auto-created)
- `requirements.txt` — Python dependencies

---

Replace `words.csv` with your own list to add more words!
