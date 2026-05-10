import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from core.config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN

from api import meta_api
from llm import llm_insights
from bot import formatters
from core.scheduler import init_scheduler
from db.store import upsert_user_state, get_user_state
from bot.notifier import notify_missing_credentials
import threading

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

    # MVP Check: Ensure user is connected before running ads commands
    user_state = get_user_state(command['user_id'])
    if not user_state:
        notify_missing_credentials(command['user_id'])
        return

    if text.lower() == "campaigns":
        respond("📋 Fetching all campaigns...")
        camps, err = meta_api.get_all_campaigns(command['user_id'])
        if err: return respond(f"⚠️ Error: {err}")
        respond(blocks=formatters.build_campaign_list_blocks(camps))
        return

    # Phase 2 Legacy Commands
    if text.lower() == "summary":
        respond("📊 Fetching Week-over-Week summary...")
        daily_data, err = meta_api.fetch_account_data_14d(command['user_id'])
        if err: return respond(f"⚠️ Error: {err}")
        top_camps, _ = meta_api.fetch_campaign_summary(command['user_id'])
        curr, prev, chg = meta_api.calculate_wow_metrics(daily_data)
        llm = llm_insights.generate_wow_insights(curr, prev, chg)
        respond(blocks=formatters.build_summary_blocks(curr, chg, top_camps, llm))
        return

    if text.lower() == "daily":
        respond("📅 Fetching daily breakdown...")
        daily_data, err = meta_api.fetch_account_data_14d(command['user_id'])
        if err: return respond(f"⚠️ Error: {err}")
        llm = llm_insights.generate_daily_insights(daily_data)
        respond(blocks=formatters.build_daily_blocks(daily_data, llm))
        return

    # Phase 3 Commands
    if text.lower().startswith("campaign "):
        c_name = text[9:].strip()
        respond(f"🎯 Diagnosing campaign '{c_name}' across all levels...")
        
        meta, err = meta_api.get_campaign_metadata(command['user_id'], c_name)
        if err or not meta: return respond(f"⚠️ {err}")
        
        adsets, _ = meta_api.fetch_adset_data(command['user_id'], meta['id'])
        ads, _ = meta_api.fetch_ad_data(command['user_id'], meta['id'])
        baseline, _ = meta_api.fetch_bifurcated_baseline(command['user_id'], meta.get('objective', 'UNKNOWN'))
        
        llm = llm_insights.generate_campaign_diagnosis(meta, adsets, baseline)
        respond(blocks=formatters.build_upgraded_campaign_blocks(meta, adsets, ads, llm))
        return

    if text.lower().startswith("adsets "):
        c_name = text[7:].strip()
        respond(f"📦 Fetching Ad Sets for '{c_name}'...")
        
        meta, err = meta_api.get_campaign_metadata(command['user_id'], c_name)
        if err or not meta: return respond(f"⚠️ {err}")
        
        adsets, err = meta_api.fetch_adset_data(command['user_id'], meta['id'])
        if err: return respond(f"⚠️ {err}")
        
        baseline, _ = meta_api.fetch_bifurcated_baseline(command['user_id'], meta.get('objective', 'UNKNOWN'))
        llm = llm_insights.generate_adset_insights(meta, adsets, baseline)
        respond(blocks=formatters.build_adset_blocks(meta, adsets, llm))
        return

    if text.lower().startswith("creatives "):
        c_name = text[10:].strip()
        respond(f"🎨 Fetching Creatives for '{c_name}'...")
        
        meta, err = meta_api.get_campaign_metadata(command['user_id'], c_name)
        if err or not meta: return respond(f"⚠️ {err}")
        
        ads, err = meta_api.fetch_ad_data(command['user_id'], meta['id'])
        if err: return respond(f"⚠️ {err}")
        
        baseline, _ = meta_api.fetch_bifurcated_baseline(command['user_id'], meta.get('objective', 'UNKNOWN'))
        llm = llm_insights.generate_creative_insights(meta, ads, baseline)
        respond(blocks=formatters.build_creative_blocks(meta, ads, llm))
        return

    respond(blocks=formatters.format_help_blocks())

@app.command("/connect")
def handle_connect_command(ack, respond, command):
    ack()
    user_id = command['user_id']
    
    # In a real app, this would trigger an OAuth flow. 
    # For MVP, we'll mock it by saving the environment variables to the state store.
    from core.config import META_ACCESS_TOKEN, META_AD_ACCOUNT_ID
    if META_ACCESS_TOKEN and META_AD_ACCOUNT_ID:
        # Check if first run
        is_first_run = get_user_state(user_id) is None
        
        upsert_user_state(user_id, META_AD_ACCOUNT_ID, META_ACCESS_TOKEN)
        respond("✅ Connected to Meta Ads successfully! (Using environment variables for MVP)")
        
        # Trigger background sync
        from core.scheduler import run_sync_for_user
        threading.Thread(target=run_sync_for_user, args=(user_id, META_AD_ACCOUNT_ID, META_ACCESS_TOKEN, is_first_run)).start()
    else:
        respond("⚠️ Please set META_ACCESS_TOKEN and META_AD_ACCOUNT_ID in your .env file to mock the connection.")

