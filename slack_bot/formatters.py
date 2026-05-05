def _get_trend_icon(pct_change, is_good_metric=True):
    """Returns an emoji based on percentage change."""
    if pct_change >= 5:
        return "✅" if is_good_metric else "🔴"
    elif pct_change <= -5:
        return "🔴" if is_good_metric else "✅"
    else:
        return "⚠️" # Slight change

def format_help_blocks():
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Available Meta Ads Commands:*\n• `/ads summary` - Show Week-over-Week account summary with AI insights\n• `/ads daily` - Show daily breakdown for the last 7 days\n• `/ads campaign <name>` - Show metrics for a specific campaign\n• `/ads help` - Show this message"
            }
        }
    ]

def build_summary_blocks(current, wow_changes, top_campaigns_raw, llm_insights):
    """Builds a Slack Block Kit JSON array for the WoW summary."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Week-over-Week Meta Ads Summary",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Account Performance (Last 7 Days vs Previous)*\n\n"
                        f"• *Spend:* ${current.get('spend', 0):.2f}  `{wow_changes.get('spend', 0):+.1f}%`\n"
                        f"• *Impressions:* {current.get('impressions', 0):,}  `{wow_changes.get('impressions', 0):+.1f}%`\n"
                        f"• *Clicks:* {current.get('clicks', 0):,}  `{wow_changes.get('clicks', 0):+.1f}%`\n"
                        f"• *CTR:* {current.get('ctr', 0):.2f}%  `{wow_changes.get('ctr', 0):+.1f}%` {_get_trend_icon(wow_changes.get('ctr', 0), True)}\n"
                        f"• *CPC:* ${current.get('cpc', 0):.2f}  `{wow_changes.get('cpc', 0):+.1f}%` {_get_trend_icon(wow_changes.get('cpc', 0), False)}\n"
                        f"• *CPM:* ${current.get('cpm', 0):.2f}  `{wow_changes.get('cpm', 0):+.1f}%` {_get_trend_icon(wow_changes.get('cpm', 0), False)}\n"
                        f"• *ROAS:* {current.get('roas', 0):.2f}  `{wow_changes.get('roas', 0):+.1f}%` {_get_trend_icon(wow_changes.get('roas', 0), True)}\n"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🤖 AI Insights:*\n{llm_insights}"
            }
        },
        {"type": "divider"}
    ]

    # Top 5 Campaigns
    if top_campaigns_raw:
        try:
            sorted_camps = sorted(top_campaigns_raw, key=lambda x: float(x.get('spend', 0)), reverse=True)[:5]
            camp_text = "*Top 5 Campaigns by Spend (Last 7 Days)*\n"
            for c in sorted_camps:
                name = c.get('campaign_name', 'Unknown')
                spend = float(c.get('spend', 0))
                ctr = float(c.get('ctr', 0)) if c.get('ctr') else 0
                camp_text += f"• *{name}*: ${spend:.2f} (CTR: {ctr:.2f}%)\n"
                
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": camp_text
                }
            })
        except Exception:
            pass

    return blocks

def build_daily_blocks(daily_data, llm_insights):
    """Builds a Slack Block Kit array for the daily breakdown."""
    recent_days = sorted(daily_data, key=lambda x: x.get('date_start', ''))[-7:]
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📅 Daily Breakdown (Last 7 Days)",
                "emoji": True
            }
        }
    ]
    
    table_text = "*Date* | *Spend* | *CTR* | *ROAS*\n"
    for d in recent_days:
        date = d.get('date_start', 'Unknown')
        spend = float(d.get('spend', 0))
        impressions = int(d.get('impressions', 0))
        clicks = int(d.get('clicks', 0))
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        
        roas = 0.0
        for r in d.get('purchase_roas', []):
            if r.get('action_type') == 'purchase':
                roas = float(r.get('value', 0))
                break
                
        table_text += f"`{date}` | ${spend:.2f} | {ctr:.2f}% | {roas:.2f}\n"

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": table_text
        }
    })
    
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*🤖 Daily AI Insights:*\n{llm_insights}"
        }
    })
    
    return blocks
