from datetime import datetime, timedelta
import re

def parse_date_from_text(date_text, current_date):
    date_text_lower = date_text.lower().strip()
    current_dt = datetime.strptime(current_date, "%Y-%m-%d")
    if date_text_lower in ['today','aaj']:
        return current_date
    if date_text_lower in ['yesterday','kal']:
        return (current_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    if date_text_lower in ['tomorrow']:
        return (current_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    days_ago_match = re.search(r'(\d+)\s*days?\s*ago', date_text_lower)
    if days_ago_match:
        days = int(days_ago_match.group(1))
        return (current_dt - timedelta(days=days)).strftime("%Y-%m-%d")
    for fmt in ['%Y-%m-%d','%d/%m/%Y','%d-%m-%Y']:
        try:
            return datetime.strptime(date_text, fmt).strftime('%Y-%m-%d')
        except:
            pass
    return current_date
