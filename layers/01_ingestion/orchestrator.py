import os
from typing import Dict, Any, List
from layers.01_ingestion.ga4 import GA4Connector
from layers.01_ingestion.llm_classifier import GA4LLMRouter

class IngestionOrchestrator:
    """
    Orchestrates the data ingestion process:
    1. Asks LLM for query parameters based on a goal.
    2. Retrieves brand credentials from database.
    3. Executes the query using the appropriate connector.
    """

    def __init__(self, 
                 google_client_id: str, 
                 google_client_secret: str, 
                 llm_api_key: str):
        self.google_client_id = google_client_id
        self.google_client_secret = google_client_secret
        self.router = GA4LLMRouter(api_key=llm_api_key)

    def run_ga4_ingestion(self, brand_id: str, property_id: str, refresh_token: str, goal: str) -> List[Dict[str, Any]]:
        """
        Executes a GA4 ingestion task driven by an LLM goal.
        """
        # Step 1: Get structured query from LLM
        print(f"[*] Asking LLM for query parameters to fulfill goal: '{goal}'")
        params = self.router.get_query_params(goal)
        print(f"[+] LLM Decision: {params}")

        # Step 2: Initialize Connector
        connector = GA4Connector(
            client_id=self.google_client_id,
            client_secret=self.google_client_secret
        )

        # Step 3: Authenticate
        print(f"[*] Authenticating for brand: {brand_id}")
        connector.authenticate(refresh_token=refresh_token, property_id=property_id)

        # Step 4: Fetch Data
        print(f"[*] Fetching data from GA4 Property: {property_id}")
        data = connector.fetch_data(
            metrics=params['metrics'],
            dimensions=params['dimensions'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        print(f"[+] Successfully fetched {len(data)} rows.")
        return data
