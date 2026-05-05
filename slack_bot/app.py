import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN

import meta_api
import llm_insights
import formatters

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(token=SLACK_BOT_TOKEN)

@app.command("/ads")
def handle_ads_command(ack, respond, command):
    # Acknowledge command request immediately
    ack()
    
    text = command.get('text', '').strip()
    logger.info(f"Received /ads command with text: '{text}'")

    if not text or text.lower() == "help":
        respond(blocks=formatters.format_help_blocks())
        return

    if text.lower() == "summary":
        respond("📊 Fetching Week-over-Week summary and analyzing with AI... This might take a few seconds.")
        
        # 1. Fetch 14-day daily data
        daily_data, error = meta_api.fetch_account_data_14d()
        if error:
            respond(f"⚠️ Error fetching summary: {error}")
            return
            
        # 2. Fetch top 5 campaigns for last 7 days
        top_campaigns_raw, error = meta_api.fetch_campaign_summary()
            
        # 3. Calculate WoW metrics
        current, previous, changes = meta_api.calculate_wow_metrics(daily_data)
        
        # 4. Generate LLM Insights
        llm_text = llm_insights.generate_wow_insights(current, previous, changes)
        
        # 5. Format Block Kit
        blocks = formatters.build_summary_blocks(current, changes, top_campaigns_raw, llm_text)
        respond(blocks=blocks)
        return

    if text.lower() == "daily":
        respond("📅 Fetching daily breakdown for the last 7 days...")
        daily_data, error = meta_api.fetch_account_data_14d()
        if error:
            respond(f"⚠️ Error fetching daily data: {error}")
            return
            
        llm_text = llm_insights.generate_daily_insights(daily_data)
        blocks = formatters.build_daily_blocks(daily_data, llm_text)
        respond(blocks=blocks)
        return

    if text.lower().startswith("campaign "):
        campaign_name = text[9:].strip()
        if not campaign_name:
            respond("Please provide a campaign name. Example: `/ads campaign summer_sale`")
            return
            
        respond(f"Fetching data for campaign '{campaign_name}'...")
        # Since Phase 2 prioritizes account-level WoW and daily, we just reuse the 14d logic 
        # to give a simple summary of the requested campaign.
        daily_data, error = meta_api.fetch_campaign_data_14d(campaign_name)
        if error:
            respond(f"⚠️ Error fetching campaign data: {error}")
            return
            
        if not daily_data:
            respond(f"No data found for campaign matching `{campaign_name}`.")
            return
            
        current, previous, changes = meta_api.calculate_wow_metrics(daily_data)
        llm_text = llm_insights.generate_wow_insights(current, previous, changes)
        blocks = formatters.build_summary_blocks(current, changes, None, llm_text)
        respond(blocks=blocks)
        return

    # Unrecognized
    respond(blocks=formatters.format_help_blocks())

if __name__ == "__main__":
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Missing Slack tokens. Check your .env file.")
        exit(1)
        
    logger.info("Starting Slack bot Phase 2 with Socket Mode...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
