import json
from datetime import datetime
from config import ENABLE_DETAILED_LOGGING

def log_section(title):
    if ENABLE_DETAILED_LOGGING:
        print("\n" + "="*80)
        print(title)
        print("="*80)

def log_info(tag, message, indent=0):
    if ENABLE_DETAILED_LOGGING:
        print("  " * indent + f"[{tag}] {message}")

def log_json(tag, data, indent=0):
    if ENABLE_DETAILED_LOGGING:
        print("  " * indent + f"[{tag}]")
        print(json.dumps(data, indent=2, ensure_ascii=False))

def log_user_input(phone, message):
    log_section(f"INCOMING MESSAGE FROM {phone}")
    log_info("Message", message, 1)
    log_info("Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1)

def log_ai_request(prompt):
    log_section("AI REQUEST")
    print(prompt[:800])

def log_ai_response(response):
    log_section("AI RAW RESPONSE")
    print(response)

def log_error(msg, e=None):
    log_section("ERROR")
    log_info("Message", msg)
    if e:
        log_info("Exception", str(e))
