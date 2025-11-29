import os
import secrets
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from config import MAX_CHAT_HISTORY, USER_DBS_DIR, GEMINI_API_KEY, ENABLE_DETAILED_LOGGING
from logger import log_user_input, log_info, log_error, log_section
from db.users_db import init_users_db, check_user_exists, create_new_user, get_privacy_status, update_privacy_acceptance, get_user_name
from db.user_db import init_user_db, add_to_chat_history, get_chat_history
from ai.gemini_api import call_gemini_api
from ai.prompting import get_system_prompt
from ai.ai_actions import execute_ai_actions
from utils.date_parser import parse_date_from_text
from utils.formatter import format_transaction_results

app = Flask(__name__)

init_users_db()

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '').replace('whatsapp:', '').replace('+','')
    log_user_input(from_number, incoming_msg)

    resp = MessagingResponse()
    msg = resp.message()

    # Ensure user db exists
    init_user_db(from_number)

    user = check_user_exists(from_number)
    if not user:
        unique_id = secrets.token_hex(10)
        create_new_user(from_number, unique_id)
        privacy_msg = ("Welcome! Please accept privacy policy by replying YES.")
        msg.body(privacy_msg)
        return str(resp)

    privacy_status = get_privacy_status(from_number)
    if privacy_status == 'no':
        if incoming_msg.lower() in ['yes','y','accept','हाँ','ha']:
            update_privacy_acceptance(from_number, 'yes')
            msg.body('Thanks! You can now use the finance bot.')
        else:
            msg.body('Please reply YES to accept privacy policy.')
        return str(resp)

    add_to_chat_history(from_number, 'user', incoming_msg)

    # Build prompt and call Gemini (if key set)
    current_date = __import__('datetime').datetime.now().strftime('%Y-%m-%d')
    yesterday = (__import__('datetime').datetime.now() - __import__('datetime').timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow = (__import__('datetime').datetime.now() + __import__('datetime').timedelta(days=1)).strftime('%Y-%m-%d')

    system_prompt = get_system_prompt(current_date, yesterday, tomorrow, from_number)
    full_prompt = system_prompt + f"\nUSER MESSAGE: {incoming_msg}\nRespond in JSON."

    if not GEMINI_API_KEY:
        # Fallback simple parser if Gemini not configured
        if 'expense' in incoming_msg.lower() or 'spent' in incoming_msg.lower():
            msg.body('Recorded expense (demo).')
        else:
            msg.body('Demo mode: Gemini API not configured. Set GEMINI_API_KEY to enable AI.')
        add_to_chat_history(from_number, 'assistant', msg.body)
        return str(resp)

    ai_text = call_gemini_api(full_prompt)
    if not ai_text:
        msg.body('Sorry, AI unavailable.')
        return str(resp)

    # Try to extract JSON from ai_text
    import re, json
    m = re.search(r'\{.*\}', ai_text, re.DOTALL)
    if not m:
        msg.body('Could not parse AI response.')
        return str(resp)
    try:
        actions_json = json.loads(m.group(0))
    except Exception as e:
        msg.body('AI returned invalid JSON.')
        return str(resp)

    results = execute_ai_actions(from_number, actions_json)
    response_text = actions_json.get('response_text','Done!')
    formatted = format_transaction_results(results)
    if formatted:
        response_text += "\n" + formatted

    add_to_chat_history(from_number, 'assistant', response_text)
    msg.body(response_text)
    return str(resp)

@app.route('/')
def home():
    return 'Finance Bot - OK'

if __name__ == '__main__':
    print('Starting server on http://0.0.0.0:5000')
    app.run(host='0.0.0.0', port=5000, debug=True)
