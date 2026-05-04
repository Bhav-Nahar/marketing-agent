import os
import json
from dotenv import load_dotenv
from layers.01_ingestion.orchestrator import IngestionOrchestrator

def main():
    # Load environment variables
    load_dotenv()
    
    # Required secrets from .env
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    llm_api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # Brand details for testing (fill these in your .env for a real test)
    brand_id = os.getenv("DEFAULT_BRAND_ID", "test_brand")
    property_id = os.getenv("DEFAULT_GA4_PROPERTY_ID")
    refresh_token = os.getenv("DEFAULT_GA4_REFRESH_TOKEN")

    if not all([client_id, client_secret, llm_api_key]):
        print("Error: Missing core credentials in .env file (CLIENT_ID, CLIENT_SECRET, or DEEPSEEK_API_KEY)")
        return

    # Initialize Orchestrator
    orchestrator = IngestionOrchestrator(
        google_client_id=client_id,
        google_client_secret=client_secret,
        llm_api_key=llm_api_key
    )

    # Example analytical goals
    test_goals = [
        "What was our daily session count and revenue for the last 7 days?",
        "Show me traffic source performance (sessions, bounce rate, revenue) for yesterday"
    ]

    for goal in test_goals:
        print("\n" + "="*50)
        print(f"TESTING GOAL: {goal}")
        print("="*50)
        
        try:
            # Note: This will only work if you have a valid REFRESH_TOKEN and PROPERTY_ID in .env
            if not property_id or not refresh_token:
                print("Skipping actual API call: PROPERTY_ID or REFRESH_TOKEN not provided in .env")
                # Just test the LLM routing part
                params = orchestrator.router.get_query_params(goal)
                print(f"[LLM ONLY TEST] Parameters: {json.dumps(params, indent=2)}")
            else:
                results = orchestrator.run_ga4_ingestion(
                    brand_id=brand_id,
                    property_id=property_id,
                    refresh_token=refresh_token,
                    goal=goal
                )
                print(f"Sample Result: {results[0] if results else 'No data'}")
        except Exception as e:
            print(f"Error during test: {e}")

if __name__ == "__main__":
    main()
