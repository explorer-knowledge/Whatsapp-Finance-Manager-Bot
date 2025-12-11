# FinTech Bot

**Tagline:** *Never forget any payment again.*

---

## Project Overview

FinTech Bot (a.k.a. FinMind) is an AI-powered personal finance assistant built on WhatsApp using Twilio. It records and organizes salary, expenses, loans, repayments and savings through natural chat messages, then provides summaries, reminders and smart insights.

This repo contains the backend webhook (Flask + Python), basic frontend dashboard (HTML/CSS/JS + Tailwind), and integration glue for Twilio WhatsApp messaging.

---

## To use our bot directly with the help of whatsapp chat

1. Save the mobile number in your contact list.
   ``` +1 415 523 8886  ```

2. Type ``` join automobile-thy ``` in the chat with the above saved number

3. Now you can start with simple greetings.

## To Deploy the bot

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

4. Install ngrok and run ``` ngrok http 5000```

5. Twilio setup -> Go to twilio console -> messaging -> sandbox settings.

6. Paste the URL that you obtained from ngrok as : https://xxxx.ngrok-free.app/webhook.

7. Message to the number ```+1 415 523 8886``` and message the join code provided by twilio

---

## Key Features

* Record salary, expenses, loans, and repayments via WhatsApp messages.
* Persistent memory of conversations and transactions.
* Natural language understanding to extract amounts, dates, and parties.
* Loan tracking and outstanding calculations.
* Monthly summaries and quick balance checks via chat.
* Privacy-first: encrypted storage and user isolation.

---

## Demo (example messages)

* `My salary 1st May: 40000`
* `Paid rent 8000`
* `Lent Rohan 1500`
* `Owed by Kriti: 500`
* `Show this month's summary`

The bot replies with structured confirmations and stored entries, then can provide totals, outstanding loans, and personalized advice.

---

## Tech Stack

* Backend: Python, Flask
* Messaging: Twilio WhatsApp API
* Frontend: HTML, CSS, JavaScript, Tailwind CSS (dashboard)
* NLP: Lightweight parsing + rule-based extraction (extendable to transformer models)
* Storage: Encrypted database (eg. PostgreSQL / SQLite + application-level encryption)

---

## Architecture

1. **WhatsApp (User)** → 2. **Twilio** → 3. **Flask Webhook** → 4. **NLP + Business Logic** → 5. **Encrypted DB** → 6. **Dashboard**

* Twilio forwards incoming WhatsApp messages to our Flask webhook.
* Webhook extracts user ID and message text and forwards to the NLP module.
* NLP extracts entities (amounts, types, dates, counterparty) and creates/updates records.
* Responses are sent back to the user through Twilio API.


## Usage

* Start a chat with the bot on WhatsApp.
* Send natural sentences describing transactions.
* For structured commands (optional):

  * `summary [month]`
  * `loans`
  * `balance`

---

## Security & Privacy

* All sensitive values are encrypted before storage using a long random string
* Each WhatsApp user is scoped to their own records — no cross-account access.
* Do not store unencrypted secrets in the repo.

---

## Challenges We Faced

* Webhook configuration and stability with Twilio.
* Accurate NLP extraction for casual, mixed-language messages.
* Initial server crashes and scaling edge-cases.
* Handling audio messages and voice-to-text conversion (work in progress).

---

## Accomplishments

* Functional WhatsApp bot that records and recalls transactions.
* Loan tracking and automated outstanding calculations.
* Privacy-preserving encrypted storage and user separation.
* Intelligent advice based on salary and spending patterns.

---

## What We Learned

* End-to-end integration of Twilio and Flask webhooks.
* Designing rule-based NLP for finance use-cases and when to replace with ML models.
* Importance of encryption and secure key management in fintech apps.
* Team collaboration and rapid iteration under limited time.

---

## Roadmap / What's Next

* Add voice message support and automatic transcription.
* Improve NLP to handle multi-language (Hinglish) inputs and slang.
* Implement visual analytics and monthly reports on the dashboard.
* Explore optional UPI/bank API integration (with strong security and user consent).

---

## Contact

Project team:  FinTech Bot
Email: `team@example.com` (replace with real contact)

---

*Thank you for checking out FinTech Bot. We built this because we kept forgetting pocket payments — now our chat remembers for us.*
