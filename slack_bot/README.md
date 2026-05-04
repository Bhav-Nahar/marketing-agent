# Meta Ads Slack Bot MVP

A simple Slack bot built with Python and Slack Bolt to fetch and summarize Meta Ads performance via slash commands.

## Setup Instructions

### 1. Project Setup
1. Copy `.env.example` to `.env` and fill in your actual credentials.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

### 2. Slack App Setup
1. Go to [Slack API Apps](https://api.slack.com/apps) and Create New App.
2. In **Socket Mode**, enable Socket Mode and get your App-Level Token (`xapp-...`). Add it to `.env` as `SLACK_APP_TOKEN`.
3. Go to **Slash Commands** and create a new command `/ads`.
4. Go to **OAuth & Permissions** and add the following Bot Token Scopes:
   - `commands`
   - `chat:write`
5. Install the app to your workspace. Get the Bot User OAuth Token (`xoxb-...`) and add it to `.env` as `SLACK_BOT_TOKEN`.

### 3. Meta API Setup
1. Go to the Meta Developer Dashboard, select your App, and set up Marketing API.
2. Generate an access token with `ads_read` permission. Add it to `.env` as `META_ACCESS_TOKEN`.
3. Add your Ad Account ID (including the `act_` prefix) to `.env` as `META_AD_ACCOUNT_ID`.

### 4. Running the Bot
```bash
python app.py
```

### 5. Testing
In your Slack workspace, try typing:
- `/ads help`
- `/ads summary`
- `/ads campaign <campaign_name>`
