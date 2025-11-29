# Finance Manager Bot 

An AI powered personal finance manager that works dorectly on whatsapp .
It uses google gemini ai to interprete natural language message for tracking income , expenses and loans .

## To use our bot directly with the help of whatsapp chat

1. Save the mobile number
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

## Notes
- The code uses a simplified split of the original file.
- Per-user sqlite DBs are saved in `user_dbs/`.
- The original monolithic script is preserved at `original/final.py`.
