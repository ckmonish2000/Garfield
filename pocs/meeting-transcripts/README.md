# Meeting Transcripts POC

AI meeting notetaker proof-of-concept using Google Calendar API.

## Setup

1. Create a Google Cloud project and enable the Calendar API
2. Download OAuth credentials and save as `client_secret.json` in this directory
3. Install dependencies:
   ```
   pip install -r requirements.txt
   playwright install
   ```
4. Run the app:
   ```
   python app.py
   ```
5. Open http://localhost:8080 and log in with Google

## How it works

- OAuth flow authenticates with Google and stores tokens in `tokens.json`
- Fetches the next 10 upcoming calendar events
- Detects Google Meet, Zoom, and Teams links from events
- Background scheduler polls for meetings every 60 seconds
- Meeting joiner (Playwright-based) is a placeholder for future implementation
