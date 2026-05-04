import json
import os
from typing import Dict, List, Any
from openai import OpenAI

class GA4LLMRouter:
    """
    Intelligent router that uses an LLM to decide which GA4 metrics and dimensions 
    are required to fulfill a specific analytical goal.
    """

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        # Use OpenAI client for DeepSeek (as it is OpenAI-compatible)
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model

    def get_query_params(self, goal: str) -> Dict[str, Any]:
        """
        Takes a human-readable goal and returns structured GA4 parameters.
        Example goal: "Tell me how our organic traffic performed yesterday"
        """
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_ga4_params",
                    "description": "Extract dimensions and metrics for a GA4 data query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dimensions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "GA4 dimensions (e.g., 'date', 'sessionSource', 'sessionDefaultChannelGroup')"
                            },
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "GA4 metrics (e.g., 'sessions', 'totalRevenue', 'conversions')"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date in YYYY-MM-DD or relative like '7daysAgo'"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date in YYYY-MM-DD or relative like 'today'"
                            }
                        },
                        "required": ["dimensions", "metrics", "start_date", "end_date"]
                    }
                }
            }
        ]

        messages = [
            {"role": "system", "content": "You are a senior data analyst specialized in GA4. Map the user's request to the correct GA4 API dimensions and metrics."},
            {"role": "user", "content": goal}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "get_ga4_params"}}
        )

        # Parse the tool call
        tool_call = response.choices[0].message.tool_calls[0]
        return json.loads(tool_call.function.arguments)
