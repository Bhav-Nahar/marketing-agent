import logging
from slack_bolt.adapter.socket_mode import SocketModeHandler
from core.config import SLACK_APP_TOKEN, SLACK_BOT_TOKEN
from bot.app import app
from core.scheduler import init_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Missing Slack tokens. Check your .env file.")
        exit(1)
        
    logger.info("Initializing Scheduler...")
    init_scheduler()
    
    logger.info("Starting Slack bot Phase 3 with Socket Mode...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
