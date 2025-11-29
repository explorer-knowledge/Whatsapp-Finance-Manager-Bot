def format_transaction_results(results):
    out = ''
    for result in results:
        if isinstance(result, dict):
            if 'message' in result:
                out += f"{result.get('message')}\n"
            if 'transaction_id' in result:
                out += f"ID: {result['transaction_id']}\n"
            if 'loan_id' in result:
                out += f"Loan ID: {result['loan_id']}\n"
    return out
