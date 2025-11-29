import requests
from logger import log_ai_request, log_ai_response, log_error
from config import GEMINI_MODEL_URL

def call_gemini_api(prompt):
    try:
        headers = {'Content-Type':'application/json'}
        data = {
            'contents': [{'parts':[{'text': prompt}]}],
            'generationConfig': {
                'temperature': 0.4,
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': 1024
            }
        }
        log_ai_request(prompt)
        resp = requests.post(GEMINI_MODEL_URL, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if 'candidates' in result and len(result['candidates'])>0:
            text = result['candidates'][0]['content']['parts'][0]['text']
            log_ai_response(text)
            return text
        else:
            log_error('No candidates in Gemini response', result)
            return None
    except requests.exceptions.RequestException as e:
        log_error('Gemini request failed', e)
        return None
