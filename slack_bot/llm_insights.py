import logging
import json
import copy
from config import GROQ_API_KEY
from groq import Groq

logger = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

UNIVERSAL_SYSTEM_PROMPT = """
You are a senior Meta Ads media buyer consultant speaking directly to your client. You evaluate performance using a rigid, universal data schema.

1. You MUST speak in a natural, conversational tone. NEVER use terms like "anomaly_flags", "JSON", "array", or "delta numbers". Translate the raw data into plain English insights.
2. FIRST, review the anomalies behind the scenes. 
   - If there is a CRITICAL flag (like zero ROAS or broken pixels), this must be the headline of your analysis. Warn the client directly. Do not recommend creative/audience changes if the pixel is broken.
   - If there are HIGH flags (like frequency doubling or massive ROAS drops), mention them prominently.
3. SECOND, evaluate current performance against the objective KPI expectations using the `priority_lens` as your guide. Do not mention irrelevant metrics (e.g. ROAS on awareness).
4. THIRD, use the baseline delta percentages to explain if the current performance is normal for *this specific objective* in their account. State the actual percentage differences (e.g., "Your CTR is 20% lower than your account average for sales campaigns").

Keep total response under 200 words. Speak as a human expert. Give actionable next steps based ONLY on the numbers.
"""

def round_number(val, is_rate=False):
    if val is None: return None
    try:
        f = float(val)
        if is_rate: return round(f, 3)
        if f >= 0.01 or f <= -0.01: return round(f, 1)
        if f != 0: return round(f, 3)
        return 0.0
    except Exception:
        return val

def round_all_metrics(data):
    if isinstance(data, float):
        if data < 0.01 and data > -0.01:
            return round(data, 3)
        return round(data, 1)
    elif isinstance(data, dict):
        for k, v in list(data.items()):
            if k in ['impressions', 'id', 'campaign_id', 'adset_id', 'ad_id', 'date_start', 'created_time', 'start_time', 'name', 'campaign_name']:
                continue
            data[k] = round_all_metrics(v)
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = round_all_metrics(data[i])
    return data

def limit_top_entities(data, max_items=5):
    if isinstance(data, list) and len(data) > max_items:
        try:
            sorted_data = sorted(data, key=lambda x: float(x.get('spend', 0)) if isinstance(x, dict) else 0, reverse=True)
            dropped_count = len(sorted_data) - max_items
            limited_data = sorted_data[:max_items]
            
            is_ad = any('creative' in d for d in limited_data if isinstance(d, dict))
            note_key = 'dropped_creatives' if is_ad else 'dropped_adsets'
            note_str = f"{dropped_count} creatives not shown" if is_ad else f"{dropped_count} ad sets not shown"
            
            return {
                "items": limited_data,
                note_key: note_str
            }
        except Exception:
            return data
    return data

def trim_time_series(data, days=7):
    time_series_keys = {'daily_data', 'time_series', 'daily_breakdown', 'daily_spend', 'daily_frequency', 'daily_trend'}
    
    def trim_recursive(obj_data):
        if isinstance(obj_data, dict):
            for k, v in list(obj_data.items()):
                if k in time_series_keys and isinstance(v, list):
                    if len(v) > days:
                        try:
                            sorted_v = sorted(v, key=lambda x: x.get('date_start', '') if isinstance(x, dict) else '')
                            obj_data[k] = sorted_v[-days:]
                        except Exception:
                            pass
                else:
                    trim_recursive(v)
        elif isinstance(obj_data, list):
            for item in obj_data:
                trim_recursive(item)
                
    trim_recursive(data)
    return data

def prepare_data_for_llm(data):
    if not data:
        return data
        
    try:
        clean_data = json.loads(json.dumps(data, default=str))
    except Exception:
        clean_data = copy.deepcopy(data)
        
    clean_data = round_all_metrics(clean_data)
    clean_data = limit_top_entities(clean_data, max_items=5)
    clean_data = trim_time_series(clean_data, days=7)
    
    return clean_data

def extract_funnel_metrics(data_list):
    if not isinstance(data_list, list):
        if isinstance(data_list, dict) and 'items' in data_list:
            data_list = data_list['items']
        else:
            data_list = [data_list]
            
    add_to_cart = 0
    initiate_checkout = 0
    purchase = 0
    clicks = 0
    
    for item in data_list:
        if not isinstance(item, dict): continue
        clicks += int(item.get('clicks', 0))
        for action in item.get('actions', []):
            if action.get('action_type') == 'add_to_cart':
                add_to_cart += int(action.get('value', 0))
            elif action.get('action_type') == 'initiate_checkout':
                initiate_checkout += int(action.get('value', 0))
            elif action.get('action_type') == 'purchase':
                purchase += int(action.get('value', 0))
                
    if add_to_cart == 0 and initiate_checkout == 0 and purchase == 0:
        return None
        
    atc_rate = (add_to_cart / clicks) if clicks > 0 else 0
    checkout_rate = (initiate_checkout / add_to_cart) if add_to_cart > 0 else 0
    purchase_rate = (purchase / initiate_checkout) if initiate_checkout > 0 else 0
    
    return {
        "add_to_cart": add_to_cart,
        "initiate_checkout": initiate_checkout,
        "purchase": purchase,
        "atc_rate": atc_rate,
        "checkout_rate": checkout_rate,
        "purchase_rate": purchase_rate
    }

def compute_baseline(historical_data, campaign_age_days=None):
    if not historical_data or not isinstance(historical_data, list):
        return {"baseline_available": False, "baseline_data_quality": "unavailable"}
        
    campaigns_count = len(historical_data)
    
    if campaigns_count < 1:
        return {"baseline_available": False, "baseline_data_quality": "insufficient"}
        
    quality = "stable" if campaigns_count >= 3 else "limited"
    
    import statistics
    
    def get_median(key):
        vals = []
        for d in historical_data:
            try:
                v = float(d.get(key, 0))
                if v > 0: vals.append(v)
            except Exception: pass
        return statistics.median(vals) if vals else 0.0
        
    roas_vals = []
    for d in historical_data:
        r_val = 0
        for r in d.get('purchase_roas', []):
            if r.get('action_type') == 'purchase':
                r_val = float(r.get('value', 0))
        if r_val > 0: roas_vals.append(r_val)
        
    roas_baseline = statistics.median(roas_vals) if roas_vals else None
    
    baseline = {
        "baseline_available": True,
        "baseline_data_quality": quality,
        "window_days": 30,
        "ctr_baseline": round_number(get_median('ctr')),
        "cpm_baseline": round_number(get_median('cpm')),
        "frequency_baseline": round_number(get_median('frequency')),
        "roas_baseline": round_number(roas_baseline)
    }
    
    funnel = extract_funnel_metrics(historical_data)
    if funnel:
        baseline["atc_rate_baseline"] = round_number(funnel.get('atc_rate'), True)
        baseline["checkout_rate_baseline"] = round_number(funnel.get('checkout_rate'), True)
        baseline["purchase_rate_baseline"] = round_number(funnel.get('purchase_rate'), True)
        
    return baseline

def compute_deltas(current_metrics, baseline):
    if not baseline.get('baseline_available'):
        return None
        
    deltas = {}
    def calc_delta(curr, base):
        if curr is None or base is None or base == 0: return None
        return round_number(((curr - base) / base) * 100)
        
    deltas["ctr_delta_pct"] = calc_delta(current_metrics.get('ctr'), baseline.get('ctr_baseline'))
    deltas["cpm_delta_pct"] = calc_delta(current_metrics.get('cpm'), baseline.get('cpm_baseline'))
    deltas["frequency_delta_pct"] = calc_delta(current_metrics.get('frequency'), baseline.get('frequency_baseline'))
    deltas["roas_delta_pct"] = calc_delta(current_metrics.get('roas'), baseline.get('roas_baseline'))
    
    if 'atc_rate' in current_metrics and 'atc_rate_baseline' in baseline:
        deltas["atc_rate_delta_pct"] = calc_delta(current_metrics.get('atc_rate'), baseline.get('atc_rate_baseline'))
        deltas["checkout_rate_delta_pct"] = calc_delta(current_metrics.get('checkout_rate'), baseline.get('checkout_rate_baseline'))
        deltas["purchase_rate_delta_pct"] = calc_delta(current_metrics.get('purchase_rate'), baseline.get('purchase_rate_baseline'))
        
    return deltas

def generate_anomaly_flags(context, metrics, funnel, baseline, deltas):
    flags = []
    obj = str(context.get('objective', '')).upper()
    spend = metrics.get('spend', 0)
    roas = metrics.get('roas', 0)
    conversions = metrics.get('conversions', 0)
    
    if obj in ['OUTCOME_SALES', 'OUTCOME_CONVERSIONS']:
        if roas == 0.00 and spend > 100:
            flags.append("zero_roas_on_sales_campaign")
        if conversions == 0 and spend > 500:
            flags.append("pixel_may_be_broken")
        if not funnel or funnel.get('purchase', 0) == 0:
            flags.append("pixel_events_missing_on_sales_campaign")
            
    if obj == 'OUTCOME_LEADS':
        if conversions == 0 and spend > 100:
            flags.append("lead_event_missing_on_leads_campaign")
            
    freq = metrics.get('frequency', 0)
    if freq > 4.5:
        flags.append("frequency_critical")
        
    if deltas:
        f_delta = deltas.get('frequency_delta_pct')
        if f_delta and f_delta > 100:
            flags.append("frequency_doubled_vs_baseline")
            
        ctr_delta = deltas.get('ctr_delta_pct')
        if ctr_delta and ctr_delta < -40 and baseline.get('baseline_data_quality') == 'stable':
            flags.append("ctr_dropped_40pct_vs_baseline")
            
        roas_delta = deltas.get('roas_delta_pct')
        if roas_delta and roas_delta < -50 and baseline.get('baseline_data_quality') == 'stable':
            flags.append("roas_dropped_50pct_vs_baseline")
            
        cpm_delta = deltas.get('cpm_delta_pct')
        if cpm_delta and cpm_delta > 60:
            flags.append("cpm_spiked_60pct_vs_baseline")
            
    if context.get('learning_phase'):
        flags.append("learning_phase_active")
        
    return flags

def build_llm_payload(campaign_meta, adsets_data, account_baseline_data):
    # adsets_data is pre-processed by prepare_data_for_llm
    if isinstance(adsets_data, dict) and 'items' in adsets_data:
        adset_list = adsets_data['items']
        dropped_adsets_count = int(adsets_data.get('dropped_adsets', '0').split()[0]) if 'dropped_adsets' in adsets_data else None
    else:
        adset_list = adsets_data if isinstance(adsets_data, list) else [adsets_data]
        dropped_adsets_count = None

    obj = str(campaign_meta.get('objective', '')).upper()
    funnel_stage = 'unknown'
    if obj in ['OUTCOME_AWARENESS', 'VIDEO_VIEWS']: funnel_stage = 'tofu'
    elif obj in ['OUTCOME_TRAFFIC', 'OUTCOME_ENGAGEMENT']: funnel_stage = 'tofu_mofu'
    elif obj == 'OUTCOME_LEADS': funnel_stage = 'mofu_bofu'
    elif obj in ['OUTCOME_SALES', 'OUTCOME_APP_PROMOTES', 'OUTCOME_CONVERSIONS']: funnel_stage = 'bofu'
    
    lens = "ctr and cpc"
    if obj in ['OUTCOME_AWARENESS', 'VIDEO_VIEWS']: lens = "thruplay_rate and reach"
    elif obj == 'OUTCOME_ENGAGEMENT': lens = "engagement_rate and cpe"
    elif obj == 'OUTCOME_LEADS': lens = "cost_per_lead and lead_volume"
    elif obj in ['OUTCOME_SALES', 'OUTCOME_CONVERSIONS']: lens = "roas and cost_per_purchase"
    elif obj == 'OUTCOME_APP_PROMOTES': lens = "cost_per_install"
    
    budget_dist = []
    for a in sorted(adset_list, key=lambda x: float(x.get('spend', 0)), reverse=True)[:5]:
        budget_dist.append({
            "name": str(a.get('name')),
            "spend": round_number(a.get('spend', 0)),
            "spend_pct": round_number(a.get('spend_pct', 0))
        })
            
    context = {
        "objective": obj,
        "optimization_goal": str(adset_list[0].get('optimization_goal', '')) if adset_list else 'unknown',
        "funnel_stage": funnel_stage,
        "campaign_age_days": int(campaign_meta.get('age_days', 0)),
        "learning_phase": bool(adset_list[0].get('is_learning')) if adset_list else False,
        "learning_phase_reason": str(adset_list[0].get('learning_reason')) if adset_list else None,
        "geo": "mixed",
        "audience_type": "mixed",
        "priority_lens": lens,
        "budget_distribution": budget_dist,
        "dropped_adsets_count": dropped_adsets_count
    }
    
    spend = sum(float(a.get('spend', 0)) for a in adset_list)
    impressions = sum(int(a.get('impressions', 0)) for a in adset_list)
    clicks = sum(int(a.get('clicks', 0)) for a in adset_list)
    reach = sum(int(a.get('reach', 0)) for a in adset_list)
    
    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    cpc = (spend / clicks) if clicks > 0 else 0
    cpm = (spend / impressions * 1000) if impressions > 0 else 0
    freq = (impressions / reach) if reach > 0 else 0
    
    roas = 0
    for a in adset_list:
        for r in a.get('purchase_roas', []):
            if r.get('action_type') == 'purchase':
                roas = max(roas, float(r.get('value', 0)))
                
    conversions = 0
    for a in adset_list:
        for act in a.get('actions', []):
            if act.get('action_type') == 'purchase':
                conversions += int(act.get('value', 0))
                
    cost_per_result = (spend / conversions) if conversions > 0 else 0
    
    metrics = {
        "spend": round_number(spend),
        "impressions": impressions,
        "clicks": clicks,
        "ctr": round_number(ctr),
        "cpc": round_number(cpc),
        "cpm": round_number(cpm),
        "frequency": round_number(freq),
        "reach": reach,
        "conversions": conversions,
        "cost_per_result": round_number(cost_per_result),
        "roas": round_number(roas)
    }
    
    is_video = any('VIDEO' in str(a.get('optimization_goal', '')) for a in adset_list) or context['objective'] in ['VIDEO_VIEWS']
    if is_video:
        thruplays = 0
        for a in adset_list:
            for act in a.get('video_thruplay_watched_actions', []):
                if act.get('action_type') == 'video_view':
                    thruplays += int(act.get('value', 0))
        metrics['thruplay_rate'] = round_number((thruplays / impressions * 100) if impressions > 0 else 0)
        
    metrics = {k: v for k, v in metrics.items() if v is not None}
    
    funnel = extract_funnel_metrics(adset_list)
    if funnel:
        funnel = {k: round_number(v, is_rate=True) if 'rate' in k else v for k, v in funnel.items()}
        metrics.update({k: v for k, v in funnel.items() if 'rate' in k})
    
    baseline = compute_baseline(account_baseline_data, context['campaign_age_days'])
    deltas = compute_deltas(metrics, baseline)
    flags = generate_anomaly_flags(context, metrics, funnel, baseline, deltas)
    
    context["baseline_data_quality"] = baseline.get("baseline_data_quality", "unavailable")
    
    payload = {
        "context": context,
        "metrics": metrics
    }
    if funnel:
        payload["funnel_metrics"] = funnel
    if baseline.get('baseline_available'):
        payload["baseline"] = baseline
        if deltas:
            payload["delta"] = deltas
    payload["anomaly_flags"] = flags
    
    return payload

def generate_campaign_diagnosis(campaign_meta, adset_data, account_baseline_data):
    if not client: return "⚠️ Groq API key not configured."
    
    clean_adsets = prepare_data_for_llm(adset_data)
    
    try:
        payload = build_llm_payload(campaign_meta, clean_adsets, account_baseline_data)
        prompt = json.dumps(payload, indent=2)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": UNIVERSAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=500,
            temperature=0.1
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        return f"⚠️ Failed to generate AI insights: {str(e)}"

def generate_adset_insights(campaign_meta, adset_data, account_baseline_data=None):
    if not client: return "⚠️ Groq API key not configured."
    clean_adsets = prepare_data_for_llm(adset_data)
    try:
        payload = build_llm_payload(campaign_meta, clean_adsets, account_baseline_data)
        prompt = json.dumps(payload, indent=2)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": UNIVERSAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            temperature=0.1
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        return f"⚠️ Failed to generate AI insights: {str(e)}"

def generate_creative_insights(campaign_meta, ad_data, account_baseline_data=None):
    if not client: return "⚠️ Groq API key not configured."
    clean_ads = prepare_data_for_llm(ad_data)
    try:
        payload = build_llm_payload(campaign_meta, clean_ads, account_baseline_data)
        prompt = json.dumps(payload, indent=2)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": UNIVERSAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            temperature=0.1
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        return f"⚠️ Failed to generate AI insights: {str(e)}"

# Legacy
def generate_wow_insights(current_data, previous_data, wow_changes, campaign_meta=None):
    if not client: return "⚠️ Groq API key not configured."
    prompt = f"Current 7 Days:\n{json.dumps(prepare_data_for_llm(current_data))}\n\nChanges:\n{json.dumps(prepare_data_for_llm(wow_changes))}"
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": "You are an expert."}, {"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", max_tokens=300, temperature=0.3
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e: return f"⚠️ Failed to generate AI insights: {str(e)}"

def generate_daily_insights(daily_data, campaign_meta=None):
    if not client: return "⚠️ Groq API key not configured."
    prompt = f"Daily Data:\n{json.dumps(prepare_data_for_llm(daily_data), indent=2)}"
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": "You are an expert."}, {"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", max_tokens=250, temperature=0.3
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e: return f"⚠️ Failed to generate AI insights: {str(e)}"
