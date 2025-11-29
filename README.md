# Finance Bot - Modular Version

This is a modularized, working version of the WhatsApp Finance Manager Bot.
The original monolithic file `final.py` is included in `original/final.py`.

## Quick start

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set Gemini API key (optional; without it the bot runs in demo mode):
   ```
   export GEMINI_API_KEY='YOUR_KEY'
   ```

3. Run:
   ```
   python app.py
   ```

4. Expose to internet (ngrok) and set your webhook to `/webhook`.

## Notes
- The code uses a simplified split of the original file.
- Per-user sqlite DBs are saved in `user_dbs/`.
- The original monolithic script is preserved at `original/final.py`.
