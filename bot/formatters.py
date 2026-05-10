def _get_trend_icon(pct_change, is_good_metric=True):
    if pct_change >= 5: return "✅" if is_good_metric else "🔴"
    elif pct_change <= -5: return "🔴" if is_good_metric else "✅"
    else: return "⚠️"

def format_help_blocks():
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Available Meta Ads Commands:*\n• `/connect` - 🔌 Connect your Meta Ads Account to the Bot\n• `/ads campaigns` - 📋 List all campaigns\n• `/ads summary` - 📊 Show Week-over-Week account summary\n• `/ads daily` - 📅 Show daily breakdown for the last 7 days\n• `/ads campaign <name>` - 🎯 Show blended campaign numbers + AI Diagnosis\n• `/ads adsets <name>` - 📦 Show ad set drill-down + AI Diagnosis\n• `/ads creatives <name>` - 🎨 Show creatives drill-down + AI Diagnosis\n• `/ads help` - ℹ️ Show this message"
            }
        }
    ]

def build_summary_blocks(current, wow_changes, top_campaigns_raw, llm_insights):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📊 Week-over-Week Summary", "emoji": True}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Account Performance (Last 7 Days vs Previous)*\n\n"
                        f"• *Spend:* ₹{current.get('spend', 0):.2f}  `{wow_changes.get('spend', 0):+.1f}%`\n"
                        f"• *CTR:* {current.get('ctr', 0):.2f}%  `{wow_changes.get('ctr', 0):+.1f}%` {_get_trend_icon(wow_changes.get('ctr', 0), True)}\n"
                        f"• *CPC:* ₹{current.get('cpc', 0):.2f}  `{wow_changes.get('cpc', 0):+.1f}%` {_get_trend_icon(wow_changes.get('cpc', 0), False)}\n"
                        f"• *ROAS:* {current.get('roas', 0):.2f}  `{wow_changes.get('roas', 0):+.1f}%` {_get_trend_icon(wow_changes.get('roas', 0), True)}\n"
            }
        },
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*🤖 AI Insights:*\n{llm_insights}"}},
        {"type": "divider"}
    ]
    return blocks

def build_daily_blocks(daily_data, llm_insights):
    recent_days = sorted(daily_data, key=lambda x: x.get('date_start', ''))[-7:]
    blocks = [{"type": "header", "text": {"type": "plain_text", "text": "📅 Daily Breakdown", "emoji": True}}]
    
    table_text = "*Date* | *Spend* | *CTR* | *ROAS*\n"
    for d in recent_days:
        date = d.get('date_start', 'Unknown')
        spend = float(d.get('spend', 0) or 0)
        impressions = int(d.get('impressions', 0) or 0)
        clicks = int(d.get('clicks', 0) or 0)
        purchase_value = float(d.get('purchase_value', 0) or 0)
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        roas = (purchase_value / spend) if spend > 0 else 0
        table_text += f"`{date}` | ₹{spend:.2f} | {ctr:.2f}% | {roas:.2f}\n"

    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": table_text}})
    blocks.append({"type": "divider"})
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*🤖 Daily AI Insights:*\n{llm_insights}"}})
    return blocks

def build_adset_blocks(campaign_meta, adsets, llm_insights):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"📦 Ad Sets — {campaign_meta.get('name')}", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"Objective: {campaign_meta.get('objective')} | Buying Type: {campaign_meta.get('buying_type')}"}},
        {"type": "divider"}
    ]
    
    for a in adsets:
        name = a.get('name', 'Unknown')
        spend = float(a.get('spend', 0) or 0)
        spend_pct = a.get('spend_pct', 0)
        ctr = float(a.get('ctr', 0) or 0)
        freq = float(a.get('frequency', 0) or 0)
        purchase_value = float(a.get('purchase_value', 0) or 0)
        purchases = int(a.get('purchases', 0) or 0)
        roas = (purchase_value / spend) if spend > 0 else 0
        opt_goal = a.get('optimization_goal', '')
        bid_strategy = a.get('bid_strategy', '')
                
        ctr_icon = "✅" if ctr >= 2.0 else "⚠️" if ctr >= 1.0 else "🔴"
        freq_icon = "✅" if freq <= 2.5 else "⚠️" if freq <= 3.5 else "🔴"
        spend_icon = "🔴" if spend_pct > 50 and roas < 1.0 else ""
        
        adset_text = f"*{name}*\n"
        adset_text += f"Spend: ₹{spend:.2f} ({spend_pct:.1f}%) {spend_icon} | CTR: {ctr:.2f}% {ctr_icon} | Freq: {freq:.2f} {freq_icon}\n"
        adset_text += f"ROAS: {roas:.2f} | Purchases: {purchases}"
        if opt_goal:
            adset_text += f" | Goal: {opt_goal}"
        if bid_strategy:
            adset_text += f" | Bid: {bid_strategy}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": adset_text
            }
        })
        
    blocks.append({"type": "divider"})
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"{llm_insights}"}})
    return blocks

def build_creative_blocks(campaign_meta, ads, llm_insights):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🎨 Creatives — {campaign_meta.get('name')}", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"Objective: {campaign_meta.get('objective')}"}},
        {"type": "divider"}
    ]
    
    for a in ads:
        name = a.get('name', 'Unknown')
        spend = float(a.get('spend', 0))
        spend_pct = a.get('spend_pct', 0)
        ctr = float(a.get('ctr', 0))
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{name}*\n"
                        f"Spend: ₹{spend:.2f} ({spend_pct:.1f}%) | CTR: {ctr:.2f}%"
            }
        })
        
    blocks.append({"type": "divider"})
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"{llm_insights}"}})
    return blocks

def build_upgraded_campaign_blocks(campaign_meta, adsets, ads, llm_insights):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🎯 Campaign Diagnosis — {campaign_meta.get('name')}", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"Objective: {campaign_meta.get('objective')} | Age: {campaign_meta.get('age_days')} days"}},
        {"type": "divider"}
    ]
    
    # Aggregate metrics from adsets (using flattened columns)
    spend = sum(float(a.get('spend', 0) or 0) for a in adsets)
    impressions = sum(int(a.get('impressions', 0) or 0) for a in adsets)
    clicks = sum(int(a.get('clicks', 0) or 0) for a in adsets)
    purchases = sum(int(a.get('purchases', 0) or 0) for a in adsets)
    purchase_value = sum(float(a.get('purchase_value', 0) or 0) for a in adsets)
    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    cpc = spend / clicks if clicks > 0 else 0
    cpm = spend / impressions * 1000 if impressions > 0 else 0
    roas = (purchase_value / spend) if spend > 0 else 0
    cpr = spend / purchases if purchases > 0 else 0
    
    metrics_str = f"• *Spend:* ₹{spend:.2f}  |  *CPM:* ₹{cpm:.2f}\n"
    metrics_str += f"• *CTR:* {ctr:.2f}%  |  *CPC:* ₹{cpc:.2f}\n"
    
    obj = str(campaign_meta.get('objective', '')).upper()
    if obj in ['OUTCOME_SALES', 'OUTCOME_CONVERSIONS']:
        metrics_str += f"• *ROAS:* {roas:.2f}  |  *Purchases:* {purchases}  |  *Cost/Purchase:* ₹{cpr:.2f}\n"
    elif obj == 'OUTCOME_LEADS':
        metrics_str += f"• *Leads:* {purchases}  |  *Cost/Lead:* ₹{cpr:.2f}\n"
        
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": metrics_str
        }
    })
    
    # Top Ad Set
    if adsets:
        try:
            sorted_adsets = sorted(adsets, key=lambda x: float(x.get('spend', 0)), reverse=True)
            top_adset = sorted_adsets[0]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔥 Top Ad Set:*\n{top_adset.get('name')} - {top_adset.get('spend_pct', 0):.1f}% of budget"
                }
            })
        except Exception:
            pass
            
    blocks.append({"type": "divider"})
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"{llm_insights}"}})
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"🔍 *Drill down further:*\n`/ads adsets {campaign_meta.get('name')}`\n`/ads creatives {campaign_meta.get('name')}`"
            }
        ]
    })
    return blocks

def build_campaign_list_blocks(campaigns):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📋 All Campaigns", "emoji": True}},
        {"type": "divider"}
    ]
    
    if not campaigns:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "No campaigns found."}})
        return blocks
        
    camp_text = ""
    for c in campaigns:
        status = c.get('effective_status', c.get('status', 'UNKNOWN'))
        icon = "🟢" if status == "ACTIVE" else "⏸️"
        camp_text += f"{icon} *{c.get('name', 'Unknown')}* (`{status}`)\n"
        
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": camp_text}})
    return blocks
