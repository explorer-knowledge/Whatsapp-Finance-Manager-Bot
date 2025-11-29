import re

CATEGORY_KEYWORDS = {
    "Food & Beverage": ["chai","coffee","tea","food","breakfast","lunch","dinner","restaurant","cafe","pizza","burger"],
    "Shopping": ["shopping","clothes","shirt","pant","shoes","dress","mall","online","amazon"],
    "Entertainment": ["party","movie","netflix","subscription","entertainment","fun"],
    "Transport": ["uber","ola","taxi","cab","auto","petrol","fuel","bus","train","flight"],
    "Bills & Utilities": ["electricity","internet","wifi","phone","recharge","water","gas","rent"],
    "Health & Fitness": ["medicine","doctor","hospital","pharmacy","gym","fitness","yoga"],
    "Groceries": ["grocery","vegetables","fruits","milk","kirana"],
    "Salary": ["salary","income","earning"],
    "Investment": ["investment","stock","mutual","sip","fd","gold","crypto"]
}

def determine_category_from_text(text, transaction_type="expense"):
    text_lower = text.lower()
    category_scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text_lower:
                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                    score += 2
                else:
                    score += 1
        if score>0:
            category_scores[category]=score
    if category_scores:
        best = max(category_scores.items(), key=lambda x: x[1])[0]
        if transaction_type=='income':
            if best in ['Salary','Investment']:
                return best
            else:
                return 'Other Income'
        return best
    return 'Other Income' if transaction_type=='income' else 'Other'
