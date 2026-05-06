import logging
import json
import copy
from config import GROQ_API_KEY
from groq import Groq

logger = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

PHASE_3_SYSTEM_PROMPT = """
You are an expert Meta Ads media buyer with 10 years of experience managing ToFu, MoFu, and BoFu campaigns. You never evaluate a metric in isolation. You always trace performance problems across campaign -> ad set -> creative levels using timeline data and control logic to find one true root cause with a stated confidence level.

Before writing any insight complete all steps below in order. Do not skip any step.

STEP 1 — MAP RELATIONSHIPS
- Which creatives run in which ad sets?
- What is the audience profile per ad set?
- How is budget distributed?
- What is the frequency trend per ad set?

STEP 2 — TIMELINE CHECK
- Check age of campaigns/adsets/ads.
- Identify when changes happened. Timing correlation = strong causal signal.

STEP 3 — FREQUENCY SPLIT DIAGNOSIS
- Low CTR + Freq < 2.5: CREATIVE problem. Fix: replace creative. Do not expand audience.
- Low CTR + Freq > 3.5: FATIGUE problem. Fix: expand audience. Test creative on fresh segment.
- Low CTR + Freq 2.5-3.5: Ambiguous. Test one change at a time. Confidence: MEDIUM.

STEP 4 — CONTROL LOGIC
- Check A (Same creative across audiences): Fails in all -> Creative problem. Fails in one -> Audience problem.
- Check B (Same audience across creatives): All fail -> Audience problem. One fails -> Creative problem.

STEP 5 — STATE ONE PRIMARY ROOT CAUSE WITH CONFIDENCE LEVEL
PRIMARY CAUSE: [creative weakness / audience fatigue / audience mismatch / budget misallocation / learning phase / placement mismatch / creative-fatigue compound]
CONFIDENCE: [HIGH / MEDIUM / LOW]
REASON FOR CONFIDENCE LEVEL: [one sentence]
EVIDENCE:
-> Timeline: [...]
-> Campaign: [...]
-> Ad Set: [...]
-> Creative: [...]
-> Freq split: [...]
WHAT THIS RULES OUT: [...]

STEP 6 — RANK RECOMMENDATIONS
🔴 Fix first (root cause): [...]
⚠️ Fix second (supporting): [...]
💡 Watch (monitor): [...]
🚫 Do not: [...]

OBJECTIVE -> KPI MAPPING RULES:
- OUTCOME_AWARENESS / VIDEO_VIEWS: Judge by ThruPlay Rate, CPM, Frequency, Reach. Never mention ROAS/CPC.
- OUTCOME_TRAFFIC: Judge by CTR, CPC. Never mention ROAS.
- OUTCOME_ENGAGEMENT: Judge by Engagement Rate, CPE, Reach.
- OUTCOME_LEADS: Judge by CPL, Lead Volume. Never mention ROAS.
- OUTCOME_SALES: Judge by ROAS, CPA. High CPC is ok if ROAS > 2.0x.

LEARNING PHASE RULE:
If Learning Phase Active = True, DO NOT recommend pausing or changing targets. Recommend: Monitor for 3-5 more days.

OUTPUT FORMAT: Keep total response under 220 words. This is a Slack message. Every sentence must reference specific numbers. No generic statements. Use the exact formatting headers from Step 5 and Step 6.
"""

def filter_metrics_by_objective(data, objective):
    if not isinstance(data, (dict, list)):
        return data

    if not objective:
        logger.warning("Unknown objective, skipping metric filter")
        return data

    obj = str(objective).upper()
    keys_to_remove = set()

    if obj in ['OUTCOME_AWARENESS', 'VIDEO_VIEWS']:
        keys_to_remove = {'roas', 'cpc', 'cost_per_result', 'conversions', 'action_values', 'purchase_value'}
    elif obj == 'OUTCOME_TRAFFIC':
        keys_to_remove = {'roas', 'conversions', 'action_values', 'purchase_value', 'thruplay_rate'}
    elif obj == 'OUTCOME_LEADS':
        keys_to_remove = {'roas', 'thruplay_rate', 'purchase_value'}
    elif obj in ['OUTCOME_SALES', 'OUTCOME_CONVERSIONS']:
        keys_to_remove = {'thruplay_rate'}
    elif obj == 'OUTCOME_ENGAGEMENT':
        keys_to_remove = {'roas', 'cpc', 'cpa', 'conversions', 'thruplay_rate'}
    else:
        logger.warning("Unknown objective, skipping metric filter")
        return data

    def remove_keys(obj_data):
        if isinstance(obj_data, dict):
            for k in list(obj_data.keys()):
                if k in keys_to_remove:
                    obj_data.pop(k, None)
                else:
                    remove_keys(obj_data[k])
        elif isinstance(obj_data, list):
            for item in obj_data:
                remove_keys(item)

    remove_keys(data)
    return data

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

def prepare_data_for_llm(data, objective):
    if not data:
        return data
        
    try:
        clean_data = json.loads(json.dumps(data, default=str))
    except Exception:
        clean_data = copy.deepcopy(data)
        
    clean_data = filter_metrics_by_objective(clean_data, objective)
    clean_data = round_all_metrics(clean_data)
    clean_data = limit_top_entities(clean_data, max_items=5)
    clean_data = trim_time_series(clean_data, days=7)
    
    return clean_data

def _build_context_str(campaign_meta):
    if not campaign_meta:
        return "Campaign Metadata: Not available\n"
    
    return f"""
    Campaign Context:
    Name: {campaign_meta.get('name')}
    Objective: {campaign_meta.get('objective')}
    Buying Type: {campaign_meta.get('buying_type')}
    Age: {campaign_meta.get('age_days')} days
    """

def generate_adset_insights(campaign_meta, adset_data):
    if not client: return "⚠️ Groq API key not configured."
    
    objective = campaign_meta.get('objective') if campaign_meta else None
    clean_data = prepare_data_for_llm(adset_data, objective)
    prompt = _build_context_str(campaign_meta) + "\nAd Set Data:\n" + json.dumps(clean_data, indent=2)
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": PHASE_3_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            temperature=0.2
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        return f"⚠️ Failed to generate AI insights: {str(e)}"

def generate_creative_insights(campaign_meta, ad_data):
    if not client: return "⚠️ Groq API key not configured."
    
    objective = campaign_meta.get('objective') if campaign_meta else None
    clean_data = prepare_data_for_llm(ad_data, objective)
    prompt = _build_context_str(campaign_meta) + "\nCreative Data (with cross-adset control logic):\n" + json.dumps(clean_data, indent=2)
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": PHASE_3_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            temperature=0.2
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        return f"⚠️ Failed to generate AI insights: {str(e)}"

def generate_campaign_diagnosis(campaign_meta, adset_data, ad_data):
    if not client: return "⚠️ Groq API key not configured."
    
    objective = campaign_meta.get('objective') if campaign_meta else None
    clean_adsets = prepare_data_for_llm(adset_data, objective)
    clean_ads = prepare_data_for_llm(ad_data, objective)
    
    prompt = _build_context_str(campaign_meta) + "\nAd Set Data:\n" + json.dumps(clean_adsets, indent=2) + "\nCreative Data:\n" + json.dumps(clean_ads, indent=2)
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": PHASE_3_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            temperature=0.2
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        return f"⚠️ Failed to generate AI insights: {str(e)}"

# Legacy Phase 2 
def generate_wow_insights(current_data, previous_data, wow_changes, campaign_meta=None):
    if not client: return "⚠️ Groq API key not configured."
    
    objective = campaign_meta.get('objective') if campaign_meta else None
    clean_current = prepare_data_for_llm(current_data, objective)
    clean_previous = prepare_data_for_llm(previous_data, objective)
    clean_changes = prepare_data_for_llm(wow_changes, objective)
    
    prompt = f"Current 7 Days:\n{json.dumps(clean_current)}\n\nWeek-over-Week Changes:\n{json.dumps(clean_changes)}"
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a concise Meta Ads expert. Provide 3 bullet points on WoW changes."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            temperature=0.3
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Failed to generate AI insights: {str(e)}"

def generate_daily_insights(daily_data, campaign_meta=None):
    if not client: return "⚠️ Groq API key not configured."
    
    objective = campaign_meta.get('objective') if campaign_meta else None
    clean_data = prepare_data_for_llm(daily_data, objective)
    
    prompt = f"Daily Data:\n{json.dumps(clean_data, indent=2)}"
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a concise Meta Ads expert. Spot anomalies in the 7 day breakdown in 2 bullets."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=250,
            temperature=0.3
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Failed to generate AI insights: {str(e)}"
