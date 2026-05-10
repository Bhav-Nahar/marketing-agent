import logging
import os
import dlt
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db.store import get_all_users, update_last_sync
from sync.extractor import create_facebook_ads_source

logger = logging.getLogger(__name__)

_scheduler = None

# TODO (Deferred Features for MVP):
# - Conversion window breakdowns (1d_view, 7d_click split) -> requires separate insights job with action_report_time
# - Creative metadata (creative_id, thumbnail, body, headline) -> requires adcreatives resource setup
# - Ad-level attribution window splits -> low priority

# For MVP we provide a default rest_config that fetches the core tables
DEFAULT_REST_CONFIG = {
    "resources": [
        {
            "name": "fb_ads_campaigns",
            "table_name": "campaigns",
            "endpoint": {"path": "/campaigns", "params": {"fields": "id,name,status,objective,start_time,stop_time,daily_budget,lifetime_budget,bid_strategy"}},
            "schema_model": "FacebookAdsCampaignsAsset"
        },
        {
            "name": "fb_ads_adsets",
            "table_name": "adsets",
            "endpoint": {"path": "/adsets", "params": {"fields": "id,name,status,campaign_id,start_time,end_time,daily_budget,lifetime_budget,bid_strategy,bid_amount,optimization_goal,attribution_setting"}},
            "schema_model": "FacebookAdsAdsetsAsset"
        },
        {
            "name": "fb_ads_ads",
            "table_name": "ads",
            "endpoint": {"path": "/ads", "params": {"fields": "id,name,status,adset_id,campaign_id,creative"}},
            "schema_model": "FacebookAdsAdsAsset"
        },
        {
            "name": "fb_ads_insights",
            "table_name": "insights",
            "endpoint": {
                "path": "/insights", 
                "params": {"fields": "campaign_id,campaign_name,adset_id,adset_name,ad_id,ad_name,objective,impressions,clicks,spend,reach,frequency,cpc,cpm,ctr,actions,action_values,conversions,purchase_roas,outbound_clicks,cost_per_action_type"},
                "incremental": {"cursor_path": "date_start", "lag": 0}
            },
            "schema_model": "FacebookAdsPlatformMetrics"
        }
    ]
}

def run_sync_for_user(slack_user_id, ad_account_id, token, is_first_run=False):
    try:
        from bot.notifier import notify_first_run, notify_sync_complete
        
        if is_first_run:
            notify_first_run(slack_user_id)
            
        os.environ["DLT_SOURCES__FACEBOOK_ADS__LONG_LIVED_ACCESS__TOKEN"] = token
        os.environ["DLT_SOURCES__FACEBOOK_ADS__ACCOUNT__ID"] = ad_account_id
        
        # dlt pipeline destination -> local duckdb instance per user
        pipeline = dlt.pipeline(
            pipeline_name=f"fb_ads_{slack_user_id}",
            destination="duckdb",
            dataset_name=f"meta_ads_{ad_account_id.replace('act_', '')}"
        )
        
        source = create_facebook_ads_source(rest_config=DEFAULT_REST_CONFIG)
        load_info = pipeline.run(source)
        logger.info(f"Pipeline run for {slack_user_id} completed. Load info: {load_info}")
        
        update_last_sync(slack_user_id)
        
        if is_first_run:
            notify_sync_complete(slack_user_id)
            
    except Exception as e:
        logger.error(f"Error running sync for {slack_user_id}: {e}")

def daily_sync_job():
    logger.info("Starting daily sync for all users...")
    users = get_all_users()
    for user in users:
        run_sync_for_user(
            user["slack_user_id"], 
            user["ad_account_id"], 
            user["long_lived_token"]
        )

def init_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(daily_sync_job, CronTrigger(hour=9, minute=0))
        _scheduler.start()
        logger.info("Scheduler initialized. Daily syncs will run at 09:00 UTC.")
