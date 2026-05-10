import logging
import datetime
import duckdb
import json
import os
from db.store import get_user_state

logger = logging.getLogger(__name__)

# Path to project root where DuckDB files are stored
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _query_db(user_id, query, params=None):
    try:
        user = get_user_state(user_id)
        if not user or not user.get('ad_account_id'):
            logger.error(f"No user state found for {user_id}")
            return []
        
        db_path = os.path.join(PROJECT_ROOT, f"fb_ads_{user_id}.duckdb")
        if not os.path.exists(db_path):
            logger.error(f"DuckDB file not found: {db_path}")
            return []
        
        ad_account_id = user['ad_account_id'].replace('act_', '')
        schema = f"meta_ads_{ad_account_id}"
        
        # Prefix all bare table names with the schema
        # DuckDB stores dlt data under a named schema, not the default 'main' schema
        full_query = f"SET search_path = '{schema}'; {query}"
        
        con = duckdb.connect(db_path, read_only=True)
        try:
            result = con.execute(full_query, params or [])
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            logger.info(f"Query returned {len(rows)} rows for user {user_id}")
            return [dict(zip(columns, row)) for row in rows]
        finally:
            con.close()
    except Exception as e:
        logger.error(f"DB Error for user {user_id}: {e}")
        return []

def calculate_learning_phase(start_time, conversions, meta_flag):
    if meta_flag == "LEARNING":
        return True, "Meta learning_stage_info is LEARNING"
    if start_time:
        try:
            start_dt = datetime.datetime.strptime(str(start_time)[:10], "%Y-%m-%d")
            age_days = (datetime.datetime.now() - start_dt).days
            if age_days < 7:
                return True, f"Age is {age_days} days (< 7 days)"
        except:
            pass
    if (conversions or 0) < 50:
        return True, f"Conversions ({conversions}) < 50"
    return False, "Not in learning phase"

def calculate_budget_distribution(items):
    total_spend = sum(float(item.get('spend', 0) or 0) for item in items)
    if total_spend == 0:
        return items, False
    for item in items:
        spend = float(item.get('spend', 0) or 0)
        item['spend_pct'] = (spend / total_spend) * 100
    
    worst_performer_over_50_pct = False
    if items:
        def sort_key(x):
            spend = float(x.get('spend', 0) or 0)
            purchase_value = float(x.get('purchase_value', 0) or 0)
            roas = purchase_value / spend if spend > 0 else 0
            ctr = float(x.get('ctr', 0) or 0)
            return (roas, ctr)
        sorted_items = sorted(items, key=sort_key)
        worst = sorted_items[0]
        if worst.get('spend_pct', 0) > 50:
            worst_performer_over_50_pct = True
    return items, worst_performer_over_50_pct

def get_all_campaigns(user_id):
    query = """
    SELECT DISTINCT campaign_id as id, campaign_name as name, 'ACTIVE' as status 
    FROM insights 
    WHERE campaign_name IS NOT NULL
    ORDER BY campaign_name
    LIMIT 50
    """
    res = _query_db(user_id, query)
    return res, None if res else "No campaigns found or sync not completed."

def get_campaign_metadata(user_id, campaign_name):
    query = """
    SELECT DISTINCT campaign_id as id, campaign_name as name, objective, 'ACTIVE' as status,
           MIN(date_start) as created_time
    FROM insights 
    WHERE campaign_name ILIKE ?
    GROUP BY campaign_id, campaign_name, objective
    LIMIT 1
    """
    res = _query_db(user_id, query, [f"%{campaign_name}%"])
    if not res:
        return None, f"No campaign found matching '{campaign_name}'"
    camp = res[0]
    try:
        start_dt = datetime.datetime.strptime(str(camp.get('created_time', ''))[:10], "%Y-%m-%d")
        camp['age_days'] = (datetime.datetime.now() - start_dt).days
    except:
        camp['age_days'] = 0
    return camp, None

def fetch_adset_data(user_id, campaign_id):
    query = """
    SELECT 
        adset_id as id, adset_name as name, 'ACTIVE' as status, MIN(date_start) as start_time,
        '' as optimization_goal, '' as attribution_setting, '' as bid_strategy, '' as bid_amount, '' as daily_budget,
        SUM(spend) as spend, SUM(impressions) as impressions, SUM(clicks) as clicks,
        AVG(ctr) as ctr, AVG(cpc) as cpc, SUM(purchases) as purchases, SUM(purchase_value) as purchase_value
    FROM insights
    WHERE campaign_id = ?
    GROUP BY adset_id, adset_name
    """
    res = _query_db(user_id, query, [campaign_id])
    for row in res:
        purchases = row.get('purchases', 0) or 0
        is_learning, lr_reason = calculate_learning_phase(row.get('start_time'), purchases, "")
        row['is_learning'] = is_learning
        row['learning_reason'] = lr_reason
        row['daily_trend'] = []
        
    res, _ = calculate_budget_distribution(res)
    return res, None

def fetch_ad_data(user_id, campaign_id):
    query = """
    SELECT 
        ad_id as id, ad_name as name, 'ACTIVE' as status, '' as creative, adset_id,
        SUM(spend) as spend, SUM(impressions) as impressions, SUM(clicks) as clicks,
        AVG(ctr) as ctr, AVG(cpc) as cpc, SUM(purchases) as purchases, SUM(purchase_value) as purchase_value
    FROM insights
    WHERE campaign_id = ?
    GROUP BY ad_id, ad_name, adset_id
    """
    res = _query_db(user_id, query, [campaign_id])
    
    for r in res:
        r['cross_adset_performance'] = [] 
        if isinstance(r.get('creative'), str):
            try:
                r['creative'] = json.loads(r['creative'])
            except:
                pass
                
    res, _ = calculate_budget_distribution(res)
    return res, None

def fetch_account_data_14d(user_id):
    query = """
    SELECT date_start, 
           SUM(spend) as spend, SUM(impressions) as impressions, SUM(clicks) as clicks,
           SUM(purchases) as purchases, SUM(purchase_value) as purchase_value
    FROM insights
    WHERE CAST(date_start AS DATE) >= current_date - INTERVAL 14 DAY
    GROUP BY date_start
    ORDER BY date_start
    """
    res = _query_db(user_id, query)
    return res, None

def fetch_campaign_summary(user_id):
    query = """
    SELECT campaign_name, SUM(spend) as spend, SUM(impressions) as impressions,
           SUM(clicks) as clicks, SUM(purchases) as purchases, SUM(purchase_value) as purchase_value
    FROM insights
    WHERE CAST(date_start AS DATE) >= current_date - INTERVAL 7 DAY
    GROUP BY campaign_name
    """
    res = _query_db(user_id, query)
    return res, None

def fetch_bifurcated_baseline(user_id, objective):
    query = """
    SELECT campaign_id, SUM(spend) as spend, SUM(impressions) as impressions,
           SUM(clicks) as clicks, SUM(purchases) as purchases, SUM(purchase_value) as purchase_value
    FROM insights
    WHERE objective = ? AND CAST(date_start AS DATE) >= current_date - INTERVAL 30 DAY
    GROUP BY campaign_id
    """
    res = _query_db(user_id, query, [objective])
    return res, None

def calculate_wow_metrics(daily_data):
    if not daily_data or len(daily_data) == 0:
        return {}, {}, {}
    sorted_data = sorted(daily_data, key=lambda x: str(x.get('date_start', '')))
    midpoint = len(sorted_data) // 2
    previous_days = sorted_data[:midpoint]
    current_days = sorted_data[midpoint:]

    def aggregate(days):
        spend = sum(float(d.get('spend', 0) or 0) for d in days)
        impressions = sum(int(d.get('impressions', 0) or 0) for d in days)
        clicks = sum(int(d.get('clicks', 0) or 0) for d in days)
        purchases = sum(int(d.get('purchases', 0) or 0) for d in days)
        purchase_value = sum(float(d.get('purchase_value', 0) or 0) for d in days)
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cpc = (spend / clicks) if clicks > 0 else 0
        cpm = (spend / impressions * 1000) if impressions > 0 else 0
        roas = (purchase_value / spend) if spend > 0 else 0
        return {'spend': spend, 'impressions': impressions, 'clicks': clicks, 'purchases': purchases, 'purchase_value': purchase_value, 'ctr': ctr, 'cpc': cpc, 'cpm': cpm, 'roas': roas}

    current = aggregate(current_days)
    previous = aggregate(previous_days)

    def calc_pct(curr, prev):
        if prev == 0: return 100.0 if curr > 0 else 0.0
        return ((curr - prev) / prev) * 100

    changes = {k: calc_pct(current[k], previous[k]) for k in current.keys()}
    return current, previous, changes
