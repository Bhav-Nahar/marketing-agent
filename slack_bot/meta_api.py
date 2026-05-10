import logging
import datetime
from config import META_ACCESS_TOKEN, META_AD_ACCOUNT_ID
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

logger = logging.getLogger(__name__)

if META_ACCESS_TOKEN:
    FacebookAdsApi.init(access_token=META_ACCESS_TOKEN)

def _get_account():
    if not META_ACCESS_TOKEN or not META_AD_ACCOUNT_ID:
        raise ValueError("Meta API credentials are not configured.")
    account_id = META_AD_ACCOUNT_ID
    if not account_id.startswith('act_'):
        account_id = f"act_{account_id}"
    return AdAccount(account_id)

DEFAULT_INSIGHT_FIELDS = [
    'campaign_id', 'campaign_name', 'adset_id', 'adset_name', 'ad_id', 'ad_name',
    'spend', 'impressions', 'clicks', 'cpc', 'cpm', 'ctr', 'actions', 'purchase_roas',
    'reach', 'frequency', 'cost_per_action_type', 'video_thruplay_watched_actions'
]

def calculate_learning_phase(start_time, conversions, meta_flag):
    """
    Returns (is_learning, reason_string)
    """
    if meta_flag == "LEARNING":
        return True, "Meta learning_stage_info is LEARNING"
    
    if start_time:
        try:
            start_dt = datetime.datetime.strptime(start_time[:10], "%Y-%m-%d")
            age_days = (datetime.datetime.now() - start_dt).days
            if age_days < 7:
                return True, f"Age is {age_days} days (< 7 days)"
        except Exception:
            pass
            
    if conversions < 50:
        return True, f"Conversions ({conversions}) < 50"
        
    return False, "Not in learning phase"

def calculate_budget_distribution(items):
    """
    Adds 'spend_pct' to each item in items based on total spend.
    Flags worst_performer_over_50_pct if the item with worst ROAS/CTR consumes >50% spend.
    """
    total_spend = sum(float(item.get('spend', 0)) for item in items)
    if total_spend == 0:
        return items, False
        
    for item in items:
        spend = float(item.get('spend', 0))
        item['spend_pct'] = (spend / total_spend) * 100 if total_spend > 0 else 0

    worst_performer_over_50_pct = False
    
    # Identify worst performer (lowest ROAS, or lowest CTR if no ROAS)
    if items:
        # Simple worst performer heuristic for budget flag:
        # Sort by ROAS ascending, then CTR ascending
        def sort_key(x):
            roas = 0
            for r in x.get('purchase_roas', []):
                if r.get('action_type') == 'purchase':
                    roas = float(r.get('value', 0))
            ctr = float(x.get('ctr', 0))
            return (roas, ctr)
            
        sorted_items = sorted(items, key=sort_key)
        worst = sorted_items[0]
        if worst.get('spend_pct', 0) > 50:
            worst_performer_over_50_pct = True
            
    return items, worst_performer_over_50_pct

def get_campaign_metadata(campaign_name):
    """
    Finds the campaign ID and fetches its metadata.
    """
    try:
        account = _get_account()
        campaigns = account.get_campaigns(
            fields=['id', 'name', 'objective', 'buying_type', 'status', 'created_time', 'special_ad_categories'],
            params={'filtering': [{'field': 'name', 'operator': 'CONTAIN', 'value': campaign_name}]}
        )
        if not campaigns:
            return None, f"No campaign found matching '{campaign_name}'"
            
        camp = dict(campaigns[0])
        try:
            start_dt = datetime.datetime.strptime(camp.get('created_time', '')[:10], "%Y-%m-%d")
            camp['age_days'] = (datetime.datetime.now() - start_dt).days
        except Exception:
            camp['age_days'] = 0
            
        return camp, None
    except Exception as e:
        return None, str(e)

def fetch_adset_data(campaign_id):
    """
    Fetches ad sets for a campaign, merges with 7-day insights and daily trend.
    """
    try:
        account = _get_account()
        camp = Campaign(campaign_id)
        
        # 1. Fetch Ad Set Metadata
        adsets_raw = camp.get_ad_sets(fields=['id', 'name', 'optimization_goal', 'billing_event', 'targeting', 'start_time', 'budget_remaining', 'learning_stage_info'])
        adsets_meta = {a['id']: dict(a) for a in adsets_raw}
        
        # 2. Fetch 7-day Insights
        insights = account.get_insights(
            params={
                'date_preset': 'last_7d',
                'level': 'adset',
                'fields': DEFAULT_INSIGHT_FIELDS,
                'filtering': [{'field': 'campaign.id', 'operator': 'EQUAL', 'value': campaign_id}]
            }
        )
        
        # 3. Fetch Daily Insights for 7 days
        daily_insights = account.get_insights(
            params={
                'date_preset': 'last_7d',
                'time_increment': 1,
                'level': 'adset',
                'fields': ['adset_id', 'spend', 'frequency']
            }
        )
        
        # Merge
        result = []
        for insight in insights:
            i_dict = dict(insight)
            adset_id = i_dict.get('adset_id')
            meta = adsets_meta.get(adset_id, {})
            
            # Extract conversions for learning phase calc
            conversions = 0
            for action in i_dict.get('actions', []):
                if action.get('action_type') == 'purchase':
                    conversions = int(action.get('value', 0))
                    
            is_learning, lr_reason = calculate_learning_phase(
                meta.get('start_time'), 
                conversions, 
                meta.get('learning_stage_info')
            )
            
            daily_trend = [dict(d) for d in daily_insights if d.get('adset_id') == adset_id]
            
            merged = {**meta, **i_dict, 'is_learning': is_learning, 'learning_reason': lr_reason, 'daily_trend': daily_trend}
            result.append(merged)
            
        # Budget distribution
        result, _ = calculate_budget_distribution(result)
        return result, None
    except Exception as e:
        return None, str(e)

def fetch_ad_data(campaign_id):
    """
    Fetches ad data, metadata, and cross-level performance.
    """
    try:
        account = _get_account()
        camp = Campaign(campaign_id)
        
        # 1. Ad Metadata
        ads_raw = camp.get_ads(fields=['id', 'name', 'creative', 'created_time', 'adset_id'])
        ads_meta = {}
        for a in ads_raw:
            a_dict = dict(a)
            # Try to get creative object type if available. It requires a separate fetch usually, 
            # but we use what we can get.
            ads_meta[a['id']] = a_dict
            
        # 2. Insights
        insights = account.get_insights(
            params={
                'date_preset': 'last_7d',
                'level': 'ad',
                'fields': DEFAULT_INSIGHT_FIELDS,
                'filtering': [{'field': 'campaign.id', 'operator': 'EQUAL', 'value': campaign_id}]
            }
        )
        
        result = []
        for insight in insights:
            i_dict = dict(insight)
            ad_id = i_dict.get('ad_id')
            meta = ads_meta.get(ad_id, {})
            
            merged = {**meta, **i_dict}
            result.append(merged)
            
        # Calculate cross-adset performance for control logic
        # Map creative_id -> list of adsets it runs in with CTR and ROAS
        creative_map = {}
        for r in result:
            creative_id = r.get('creative', {}).get('id')
            if not creative_id:
                continue
            if creative_id not in creative_map:
                creative_map[creative_id] = []
            
            roas = 0
            for ro in r.get('purchase_roas', []):
                if ro.get('action_type') == 'purchase':
                    roas = float(ro.get('value', 0))
                    
            creative_map[creative_id].append({
                'adset_id': r.get('adset_id'),
                'ctr': r.get('ctr', 0),
                'roas': roas
            })
            
        for r in result:
            c_id = r.get('creative', {}).get('id')
            r['cross_adset_performance'] = creative_map.get(c_id, [])
            
        result, _ = calculate_budget_distribution(result)
        return result, None
    except Exception as e:
        return None, str(e)


# Legacy functions for account WoW and daily commands (From Phase 2)
def fetch_account_data_14d():
    try:
        account = _get_account()
        insights = account.get_insights(
            params={
                'date_preset': 'last_14d',
                'time_increment': 1,
                'level': 'account',
                'fields': ['spend', 'impressions', 'clicks', 'cpc', 'cpm', 'ctr', 'actions', 'purchase_roas']
            }
        )
        return [dict(i) for i in insights], None
    except Exception as e:
        return None, str(e)

def fetch_campaign_summary():
    try:
        account = _get_account()
        insights = account.get_insights(
            params={
                'date_preset': 'last_7d',
                'level': 'campaign',
                'fields': ['campaign_name', 'spend', 'impressions', 'clicks', 'cpc', 'cpm', 'ctr', 'actions', 'purchase_roas']
            }
        )
        return [dict(i) for i in insights], None
    except Exception as e:
        return None, str(e)

def fetch_bifurcated_baseline(objective):
    """
    Fetches 30-day aggregate data for all campaigns matching the objective to compute median benchmarks.
    """
    try:
        account = _get_account()
        insights = account.get_insights(
            params={
                'date_preset': 'last_30d',
                'level': 'campaign',
                'filtering': [{'field': 'campaign.objective', 'operator': 'IN', 'value': [objective]}],
                'fields': ['campaign_id', 'spend', 'impressions', 'clicks', 'cpc', 'cpm', 'ctr', 'reach', 'frequency', 'actions', 'purchase_roas']
            }
        )
        return [dict(i) for i in insights], None
    except Exception as e:
        return None, str(e)

def calculate_wow_metrics(daily_data):
    if not daily_data or len(daily_data) == 0:
        return {}, {}, {}
    sorted_data = sorted(daily_data, key=lambda x: x.get('date_start', ''))
    midpoint = len(sorted_data) // 2
    previous_days = sorted_data[:midpoint]
    current_days = sorted_data[midpoint:]

    def aggregate(days):
        spend = sum(float(d.get('spend', 0)) for d in days)
        impressions = sum(int(d.get('impressions', 0)) for d in days)
        clicks = sum(int(d.get('clicks', 0)) for d in days)
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cpc = (spend / clicks) if clicks > 0 else 0
        cpm = (spend / impressions * 1000) if impressions > 0 else 0
        
        roas_values = []
        for d in days:
            for r in d.get('purchase_roas', []):
                if r.get('action_type') == 'purchase':
                    roas_values.append(float(r.get('value', 0)))
        
        avg_roas = sum(roas_values) / len(roas_values) if roas_values else 0
        return {'spend': spend, 'impressions': impressions, 'clicks': clicks, 'ctr': ctr, 'cpc': cpc, 'cpm': cpm, 'roas': avg_roas}

    current = aggregate(current_days)
    previous = aggregate(previous_days)

    def calc_pct(curr, prev):
        if prev == 0: return 100.0 if curr > 0 else 0.0
        return ((curr - prev) / prev) * 100

    changes = {k: calc_pct(current[k], previous[k]) for k in current.keys()}
    return current, previous, changes

def get_all_campaigns():
    """
    Fetches a list of all campaigns for easy lookup.
    """
    try:
        account = _get_account()
        campaigns = account.get_campaigns(
            fields=['id', 'name', 'status', 'effective_status'],
            params={'limit': 50}
        )
        return [dict(c) for c in campaigns], None
    except Exception as e:
        return None, str(e)
