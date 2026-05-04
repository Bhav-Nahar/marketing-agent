import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from services.meta import get_account_summary, get_campaign_summary
from services.formatter import format_help_message, format_summary_message, format_campaign_message

# Set up simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Slack app
app = App(token=SLACK_BOT_TOKEN)

@app.command("/ads")
def handle_ads_command(ack, respond, command):
    # Acknowledge command request immediately
    ack()
    
    text = command.get('text', '').strip()
    logger.info(f"Received /ads command with text: '{text}'")

    if not text or text.lower() == "help":
        respond(format_help_message())
        return

    if text.lower() == "summary":
        respond("Fetching your last 7 days ad summary...")
        data, error = get_account_summary()
        if error:
            respond(f"⚠️ Error fetching summary: {error}")
        else:
            respond(format_summary_message(data))
        return

    if text.lower().startswith("campaign "):
        campaign_name = text[9:].strip()
        if not campaign_name:
            respond("Please provide a campaign name. Example: `/ads campaign summer_sale`")
            return
            
        respond(f"Fetching data for campaign '{campaign_name}'...")
        data, error = get_campaign_summary(campaign_name)
        if error:
            respond(f"⚠️ Error fetching campaign data: {error}")
        else:
            respond(format_campaign_message(campaign_name, data))
        return

    # If the command is unrecognized
    respond(f"Unknown command: `{text}`\n" + format_help_message())

if __name__ == "__main__":
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Missing Slack tokens. Check your .env file.")
        exit(1)
        
    logger.info("Starting Slack bot in Socket Mode...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
