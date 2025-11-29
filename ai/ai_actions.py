import json
from logger import log_error, log_info
from db.user_db import add_income_db, add_expense_db, update_transaction_db, delete_transaction_db, view_transactions_db, get_chat_history, get_active_loans_db, add_loan_db, calculate_loan_interest, get_chat_history as _gh
from db.user_db import get_chat_history as gh

def execute_ai_actions(phone, actions_json):
    results = []
    for action in actions_json.get('actions', []):
        func = action.get('function')
        params = action.get('params', {})
        params['phone'] = phone
        try:
            if func == 'add_income_db':
                results.append(add_income_db(**params))
            elif func == 'add_expense_db':
                results.append(add_expense_db(**params))
            elif func == 'update_transaction_db':
                results.append(update_transaction_db(**params))
            elif func == 'delete_transaction_db':
                results.append(delete_transaction_db(**params))
            elif func == 'view_transactions_db':
                results.append(view_transactions_db(**params))
            elif func == 'add_loan_db':
                results.append(add_loan_db(**params))
            elif func == 'calculate_loan_interest':
                results.append(calculate_loan_interest(**params))
            else:
                results.append({'status':'error','message':f'Unknown function {func}'})
        except TypeError as e:
            log_error('Invalid params', e)
            results.append({'status':'error','message':str(e)})
        except Exception as e:
            log_error('Execution error', e)
            results.append({'status':'error','message':str(e)})
    return results
