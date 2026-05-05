import logging
from config import META_ACCESS_TOKEN, META_AD_ACCOUNT_ID
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

logger = logging.getLogger(__name__)

# Initialize Facebook SDK
if META_ACCESS_TOKEN:
    FacebookAdsApi.init(access_token=META_ACCESS_TOKEN)

def _get_account():
    if not META_ACCESS_TOKEN or not META_AD_ACCOUNT_ID:
        raise ValueError("Meta API credentials are not configured.")
        
    account_id = META_AD_ACCOUNT_ID
    if not account_id.startswith('act_'):
        account_id = f"act_{account_id}"
        
    return AdAccount(account_id)

DEFAULT_FIELDS = [
    'campaign_name',
    'spend',
    'impressions',
    'clicks',
    'cpc',
    'cpm',
    'ctr',
    'actions',
    'purchase_roas'
]

def fetch_account_data_14d():
    """
    Fetches the last 14 days of account-level data broken down by day.
    Returns a list of daily dictionaries.
    """
    try:
        account = _get_account()
        insights = account.get_insights(
            params={
                'date_preset': 'last_14d',
                'time_increment': 1,
                'level': 'account',
                'fields': DEFAULT_FIELDS
            }
        )
        return [dict(i) for i in insights], None
    except Exception as e:
        logger.error(f"Meta API Error (14d account): {str(e)}")
        return None, str(e)

def fetch_campaign_data_14d(campaign_name):
    """
    Fetches the last 14 days of specific campaign data broken down by day.
    """
    try:
        account = _get_account()
        insights = account.get_insights(
            params={
                'date_preset': 'last_14d',
                'time_increment': 1,
                'level': 'campaign',
                'fields': DEFAULT_FIELDS,
                'filtering': [{'field': 'campaign.name', 'operator': 'CONTAIN', 'value': campaign_name}]
            }
        )
        return [dict(i) for i in insights], None
    except Exception as e:
        logger.error(f"Meta API Error (14d campaign): {str(e)}")
        return None, str(e)

def fetch_campaign_summary():
    """
    Fetches the last 7 days summary for all campaigns in the ad account (for the top 5 ranking).
    """
    try:
        account = _get_account()
        insights = account.get_insights(
            params={
                'date_preset': 'last_7d',
                'level': 'campaign',
                'fields': DEFAULT_FIELDS
            }
        )
        return [dict(i) for i in insights], None
    except Exception as e:
        logger.error(f"Meta API Error (campaign summary): {str(e)}")
        return None, str(e)

def calculate_wow_metrics(daily_data):
    """
    Takes 14 days of daily data and aggregates them into current (last 7 days) 
    and previous (first 7 days of the 14-day window).
    Returns (current_totals, previous_totals, percentage_changes).
    """
    if not daily_data or len(daily_data) == 0:
        return {}, {}, {}

    # Sort by date ascending to ensure we have oldest to newest
    sorted_data = sorted(daily_data, key=lambda x: x.get('date_start', ''))
    
    # We requested last_14d. The first half is previous, second half is current.
    # Note: If fewer than 14 days exist, we just split in half roughly.
    midpoint = len(sorted_data) // 2
    previous_days = sorted_data[:midpoint]
    current_days = sorted_data[midpoint:]

    def aggregate(days):
        spend = sum(float(d.get('spend', 0)) for d in days)
        impressions = sum(int(d.get('impressions', 0)) for d in days)
        clicks = sum(int(d.get('clicks', 0)) for d in days)
        
        # Calculate derived metrics to be accurate (don't sum ratios)
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cpc = (spend / clicks) if clicks > 0 else 0
        cpm = (spend / impressions * 1000) if impressions > 0 else 0
        
        # Roas is trickier to aggregate properly without conversion values, 
        # so we will just take the average of the available days for simplicity in MVP.
        roas_values = []
        for d in days:
            roas_list = d.get('purchase_roas', [])
            for r in roas_list:
                if r.get('action_type') == 'purchase':
                    roas_values.append(float(r.get('value', 0)))
        
        avg_roas = sum(roas_values) / len(roas_values) if roas_values else 0

        return {
            'spend': spend,
            'impressions': impressions,
            'clicks': clicks,
            'ctr': ctr,
            'cpc': cpc,
            'cpm': cpm,
            'roas': avg_roas
        }

    current = aggregate(current_days)
    previous = aggregate(previous_days)

    def calc_pct(curr, prev):
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return ((curr - prev) / prev) * 100

    changes = {k: calc_pct(current[k], previous[k]) for k in current.keys()}

    return current, previous, changes
