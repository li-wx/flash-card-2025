# Flashcard Web App

A simple Flask web app for spaced repetition flashcards using a CSV word list. Tracks your memory strength and review time for each word, and saves your progress between sessions.

This app supports multiple users with separate progress. User accounts are admin-managed: only usernames created by an administrator can log in.

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
- Supports multiple users (admin-managed usernames)
- Tracks memory strength (S) and last review time (T) for each word
- Picks the word you’re most likely to forget next
- Lets you review, mark as remembered, or mark as forgotten
- Saves progress in per-user JSON files
- Pronunciation button for each word

## Admin Setup
1. Set an admin password environment variable before running the app:

   ```sh
   export FLASHCARD_ADMIN_PASSWORD="your-strong-password"
   ```

2. Start the app and open `/admin/login`.
3. Create usernames from the admin page.
4. Delete usernames from the admin page when they are no longer needed.
5. Optional: when deleting a user, you can also delete that user's progress file.
6. Users can then log in from `/login` using one of the created usernames.

## Progress Storage
- Local development: progress is saved in `user_progress/<username>.json`.
- Azure App Service: progress is saved in `/home/data/user_progress/<username>.json` so it survives app restarts.
- Optional override: set `FLASHCARD_PROGRESS_FILE` to choose the base folder parent.
- Legacy migration: existing `progress.json` is copied one time to `user_progress/legacy.json`.

## File Structure
- `app.py` — Flask backend
- `templates/flashcard.html` — Main UI
- `templates/login.html` — Username entry UI
- `templates/admin_login.html` — Admin login UI
- `templates/admin_users.html` — Admin user management UI
- `words.csv` — Word list
- `user_progress/` — Per-user progress files (auto-created)
- `users.json` — Allowed usernames (auto-created)
- `requirements.txt` — Python dependencies

---

Replace `words.csv` with your own list to add more words!
