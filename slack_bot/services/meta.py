import requests
import logging
from config import META_ACCESS_TOKEN, META_AD_ACCOUNT_ID

logger = logging.getLogger(__name__)

META_API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

DEFAULT_FIELDS = "campaign_name,spend,impressions,clicks,cpc,ctr,actions,purchase_roas"

def _make_api_call(params):
    """Helper to make the API call with basic error handling and rate limit checking"""
    if not META_ACCESS_TOKEN or not META_AD_ACCOUNT_ID:
        return None, "Meta API credentials are not configured."

    url = f"{BASE_URL}/{META_AD_ACCOUNT_ID}/insights"
    params['access_token'] = META_ACCESS_TOKEN
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            error_msg = data.get('error', {}).get('message', 'Unknown API Error')
            logger.error(f"Meta API Error: {error_msg}")
            return None, f"Meta API Error: {error_msg}"
            
        return data.get('data', []), None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request Error: {str(e)}")
        return None, f"Request failed: {str(e)}"

def get_account_summary():
    """Fetches the last 7 days summary for all campaigns in the ad account"""
    params = {
        'level': 'campaign',
        'date_preset': 'last_7d',
        'fields': DEFAULT_FIELDS
    }
    return _make_api_call(params)

def get_campaign_summary(campaign_name):
    """Fetches the last 7 days summary for a specific campaign"""
    params = {
        'level': 'campaign',
        'date_preset': 'last_7d',
        'fields': DEFAULT_FIELDS,
        'filtering': f'[{{"field":"campaign.name","operator":"CONTAIN","value":"{campaign_name}"}}]'
    }
    return _make_api_call(params)
