from db.user_db import get_chat_history
from db.user_db import get_active_loans_db
from db.users_db import get_user_name

def get_system_prompt(current_date, yesterday, tomorrow, phone):
    recent_transactions = get_chat_history(phone, limit=10)
    transactions_context = "\n".join([f"  {r[0]}: {r[1]}" for r in recent_transactions]) if recent_transactions else 'No transactions yet'
    loans = get_active_loans_db(phone)
    loans_text = '\n'.join([str(l) for l in loans]) if loans else 'No active loans'
    user_name = get_user_name(phone)
    prompt = f"""You are a Finance Manager Bot.
CURRENT DATE: {current_date}
YESTERDAY: {yesterday}
TOMORROW: {tomorrow}
USER: {user_name}
RECENT CHATS:
{transactions_context}

FUNCTIONS:
1. add_income_db(phone,date,amount,category,description)
2. add_expense_db(phone,date,amount,category,description)
3. update_transaction_db(phone,transaction_type,transaction_id,field,new_value)
4. delete_transaction_db(phone,transaction_type,transaction_id)
5. view_transactions_db(phone,transaction_type,start_date,end_date,limit)
6. get_summary_db(phone,start_date,end_date)
7. predict_recurring_expenses_db(phone)
8. add_loan_db(phone,amount,source,date_taken,interest_rate,emi_amount)
9. calculate_loan_interest(phone,amount,interest_rate,tenure_years)
Respond in JSON with 'actions' array and 'response_text'.
"""
    return prompt
