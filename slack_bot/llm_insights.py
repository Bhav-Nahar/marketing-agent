import logging
from config import GROQ_API_KEY
from groq import Groq

logger = logging.getLogger(__name__)

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def generate_wow_insights(current_data, previous_data, wow_changes):
    """
    Uses Llama 3 on Groq to generate brief week-over-week insights.
    """
    if not client:
        return "⚠️ Groq API key not configured. Unable to generate LLM insights."

    prompt = f"""
    You are an expert Meta Ads analyst. Review this Week-over-Week performance summary and provide 3 concise bullet points.
    Your output MUST be a Slack-friendly list. Do not use markdown headers, just simple bullet points.
    Identify what is improving/declining, flag anything urgent, and give a specific actionable recommendation.

    Current 7 Days:
    Spend: ${current_data.get('spend', 0):.2f}
    CTR: {current_data.get('ctr', 0):.2f}%
    ROAS: {current_data.get('roas', 0):.2f}
    CPC: ${current_data.get('cpc', 0):.2f}

    Week-over-Week Changes:
    Spend Change: {wow_changes.get('spend', 0):.1f}%
    CTR Change: {wow_changes.get('ctr', 0):.1f}%
    ROAS Change: {wow_changes.get('roas', 0):.1f}%
    CPC Change: {wow_changes.get('cpc', 0):.1f}%
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a concise, highly analytical Meta Ads expert writing directly for Slack."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            temperature=0.3
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        return f"⚠️ Failed to generate AI insights: {str(e)}"

def generate_daily_insights(daily_data):
    """
    Uses Llama 3 on Groq to generate brief insights on daily anomalies for the last 7 days.
    """
    if not client:
        return "⚠️ Groq API key not configured. Unable to generate LLM insights."

    # Format daily data for the prompt (limit to last 7 days)
    recent_days = sorted(daily_data, key=lambda x: x.get('date_start', ''))[-7:]
    
    daily_summary = ""
    for d in recent_days:
        spend = float(d.get('spend', 0))
        impressions = int(d.get('impressions', 0))
        clicks = int(d.get('clicks', 0))
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        date_start = d.get('date_start', 'Unknown')
        daily_summary += f"{date_start}: Spend ${spend:.2f}, CTR {ctr:.2f}%\n"

    prompt = f"""
    You are an expert Meta Ads analyst. Review this daily breakdown for the last 7 days and provide 2 concise bullet points spotting any anomalies (e.g., performance dropping on a specific day).
    Keep it extremely brief and Slack-friendly.

    Daily Data:
    {daily_summary}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a concise, highly analytical Meta Ads expert writing directly for Slack."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=250,
            temperature=0.3
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        return f"⚠️ Failed to generate AI insights: {str(e)}"
