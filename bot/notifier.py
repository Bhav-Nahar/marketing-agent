import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from core.config import SLACK_BOT_TOKEN

logger = logging.getLogger(__name__)
client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

def notify_first_run(slack_user_id):
    if not client: return
    try:
        client.chat_postMessage(
            channel=slack_user_id,
            text="Syncing your last 90 days of Meta Ads data… I'll notify you when it's ready. 🚀"
        )
    except SlackApiError as e:
        logger.error(f"Error sending first run notification: {e.response['error']}")

def notify_sync_complete(slack_user_id):
    if not client: return
    try:
        client.chat_postMessage(
            channel=slack_user_id,
            text="✅ Your initial Meta Ads data sync is complete! You can now use `/ads` commands."
        )
    except SlackApiError as e:
        logger.error(f"Error sending sync complete notification: {e.response['error']}")

def notify_missing_credentials(slack_user_id):
    if not client: return
    try:
        client.chat_postMessage(
            channel=slack_user_id,
            text="⚠️ Your Meta Ads account isn't connected yet. Use `/connect` to set it up."
        )
    except SlackApiError as e:
        logger.error(f"Error sending missing credentials notification: {e.response['error']}")

def notify_daily_summary(slack_user_id, spend_delta, top_campaign, anomalies):
    if not client: return
    # Placeholder for daily summary formatted message
    try:
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Daily Meta Ads Summary* 📊"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"• *Spend Delta*: {spend_delta}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"• *Top Campaign*: {top_campaign}"}},
        ]
        if anomalies:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"• *Anomalies*: {anomalies}"}})
            
        client.chat_postMessage(
            channel=slack_user_id,
            text="Daily Meta Ads Summary",
            blocks=blocks
        )
    except SlackApiError as e:
        logger.error(f"Error sending daily summary: {e.response['error']}")
