def format_help_message():
    return (
        "*Available Commands:*\n"
        "• `/ads summary` - Show last 7 days summary for all campaigns\n"
        "• `/ads campaign <name>` - Show metrics for the matching campaign\n"
        "• `/ads help` - Show this message"
    )

def _extract_metric(item, key, default="0"):
    """Helper to safely extract metrics from Meta API dict"""
    return item.get(key, default)

def _get_purchases(item):
    """Helper to extract purchases from actions array"""
    actions = item.get('actions', [])
    for action in actions:
        if action.get('action_type') == 'purchase':
            return action.get('value', '0')
    return "0"

def _get_roas(item):
    """Helper to extract purchase ROAS"""
    roas_list = item.get('purchase_roas', [])
    for roas in roas_list:
        if roas.get('action_type') == 'purchase':
            return roas.get('value', '0.00')
    return "N/A"

def _generate_recommendation(spend, roas, ctr):
    """Generate a simple recommendation based on basic metrics"""
    try:
        spend_val = float(spend)
        roas_val = float(roas) if roas != "N/A" else 0.0
        ctr_val = float(ctr) if ctr != "N/A" else 0.0

        if spend_val > 100 and roas_val > 2.0:
            return "📈 *Recommendation:* This campaign looks strong (ROAS > 2), consider scaling."
        elif spend_val > 50 and roas_val < 1.0 and roas != "N/A":
            return "⚠️ *Recommendation:* This campaign is weak (ROAS < 1), consider pausing or reducing budget."
        elif ctr_val > 2.0:
            return "💡 *Recommendation:* Good engagement (CTR > 2%), but monitor conversions."
        
    except ValueError:
        pass
    
    return ""

def _format_campaign_item(item):
    """Format a single campaign's data into markdown"""
    name = item.get('campaign_name', 'Unknown Campaign')
    spend = _extract_metric(item, 'spend', "0.00")
    impressions = _extract_metric(item, 'impressions')
    clicks = _extract_metric(item, 'clicks')
    cpc = _extract_metric(item, 'cpc', "N/A")
    ctr = _extract_metric(item, 'ctr', "N/A")
    
    purchases = _get_purchases(item)
    roas = _get_roas(item)
    
    recommendation = _generate_recommendation(spend, roas, ctr)

    blocks = [
        f"*{name}*",
        f"• *Spend:* ₹{spend}",
        f"• *Impressions:* {impressions}",
        f"• *Clicks:* {clicks} (CTR: {ctr}%)",
        f"• *CPC:* ₹{cpc}",
        f"• *Purchases:* {purchases}",
        f"• *ROAS:* {roas}"
    ]
    
    if recommendation:
        blocks.append(recommendation)
        
    return "\n".join(blocks)

def format_summary_message(data):
    """Format the account summary response"""
    if not data:
        return "No campaign data found for the last 7 days."
        
    header = "📊 *Last 7 Days - Account Summary*\n\n"
    
    # In a real MVP, if there are many campaigns, we might just show top 5 by spend
    # But for now, we'll format all returned campaigns (or limit to a reasonable number)
    max_campaigns = 5
    items = []
    
    # Sort data by spend descending if possible
    try:
        sorted_data = sorted(data, key=lambda x: float(x.get('spend', 0)), reverse=True)
    except (ValueError, TypeError):
        sorted_data = data
        
    for item in sorted_data[:max_campaigns]:
        items.append(_format_campaign_item(item))
        
    message = header + "\n\n---\n\n".join(items)
    
    if len(data) > max_campaigns:
        message += f"\n\n_...and {len(data) - max_campaigns} more campaigns. Use `/ads campaign <name>` for specifics._"
        
    return message

def format_campaign_message(campaign_name, data):
    """Format the single campaign response"""
    if not data:
        return f"No data found for campaign matching: `{campaign_name}` in the last 7 days."
        
    header = f"🎯 *Campaign Search: '{campaign_name}' (Last 7 Days)*\n\n"
    
    items = []
    for item in data:
        items.append(_format_campaign_item(item))
        
    return header + "\n\n---\n\n".join(items)
