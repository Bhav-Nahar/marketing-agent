import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN

import meta_api
import llm_insights
import formatters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(token=SLACK_BOT_TOKEN)

@app.command("/ads")
def handle_ads_command(ack, respond, command):
    ack()
    text = command.get('text', '').strip()
    logger.info(f"Received /ads command with text: '{text}'")

    if not text or text.lower() == "help":
        respond(blocks=formatters.format_help_blocks())
        return

    if text.lower() == "campaigns":
        respond("📋 Fetching all campaigns...")
        camps, err = meta_api.get_all_campaigns()
        if err: return respond(f"⚠️ Error: {err}")
        respond(blocks=formatters.build_campaign_list_blocks(camps))
        return

    # Phase 2 Legacy Commands
    if text.lower() == "summary":
        respond("📊 Fetching Week-over-Week summary...")
        daily_data, err = meta_api.fetch_account_data_14d()
        if err: return respond(f"⚠️ Error: {err}")
        top_camps, _ = meta_api.fetch_campaign_summary()
        curr, prev, chg = meta_api.calculate_wow_metrics(daily_data)
        llm = llm_insights.generate_wow_insights(curr, prev, chg)
        respond(blocks=formatters.build_summary_blocks(curr, chg, top_camps, llm))
        return

    if text.lower() == "daily":
        respond("📅 Fetching daily breakdown...")
        daily_data, err = meta_api.fetch_account_data_14d()
        if err: return respond(f"⚠️ Error: {err}")
        llm = llm_insights.generate_daily_insights(daily_data)
        respond(blocks=formatters.build_daily_blocks(daily_data, llm))
        return

    # Phase 3 Commands
    if text.lower().startswith("campaign "):
        c_name = text[9:].strip()
        respond(f"🎯 Diagnosing campaign '{c_name}' across all levels...")
        
        meta, err = meta_api.get_campaign_metadata(c_name)
        if err or not meta: return respond(f"⚠️ {err}")
        
        adsets, _ = meta_api.fetch_adset_data(meta['id'])
        ads, _ = meta_api.fetch_ad_data(meta['id'])
        
        llm = llm_insights.generate_campaign_diagnosis(meta, adsets, ads)
        respond(blocks=formatters.build_upgraded_campaign_blocks(meta, adsets, ads, llm))
        return

    if text.lower().startswith("adsets "):
        c_name = text[7:].strip()
        respond(f"📦 Fetching Ad Sets for '{c_name}'...")
        
        meta, err = meta_api.get_campaign_metadata(c_name)
        if err or not meta: return respond(f"⚠️ {err}")
        
        adsets, err = meta_api.fetch_adset_data(meta['id'])
        if err: return respond(f"⚠️ {err}")
        
        llm = llm_insights.generate_adset_insights(meta, adsets)
        respond(blocks=formatters.build_adset_blocks(meta, adsets, llm))
        return

    if text.lower().startswith("creatives "):
        c_name = text[10:].strip()
        respond(f"🎨 Fetching Creatives for '{c_name}'...")
        
        meta, err = meta_api.get_campaign_metadata(c_name)
        if err or not meta: return respond(f"⚠️ {err}")
        
        ads, err = meta_api.fetch_ad_data(meta['id'])
        if err: return respond(f"⚠️ {err}")
        
        llm = llm_insights.generate_creative_insights(meta, ads)
        respond(blocks=formatters.build_creative_blocks(meta, ads, llm))
        return

    respond(blocks=formatters.format_help_blocks())

if __name__ == "__main__":
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Missing Slack tokens. Check your .env file.")
        exit(1)
    logger.info("Starting Slack bot Phase 3 with Socket Mode...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
