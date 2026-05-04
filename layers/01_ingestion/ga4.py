import os
from typing import Any, Dict, List, Optional
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2.credentials import Credentials
from layers.01_ingestion.base_connector import BaseConnector

class GA4Connector(BaseConnector):
    """
    GA4 Connector that uses OAuth 2.0 Refresh Tokens for scalable, multi-tenant ingestion.
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.client: Optional[BetaAnalyticsDataClient] = None
        self.property_id: Optional[str] = None

    def authenticate(self, refresh_token: str, property_id: str) -> BetaAnalyticsDataClient:
        """
        Rebuilds Google Credentials from a Refresh Token and initializes the GA4 Client.
        """
        creds = Credentials(
            token=None,  # Access token will be automatically refreshed
            refresh_token=refresh_token,
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        self.client = BetaAnalyticsDataClient(credentials=creds)
        self.property_id = property_id
        return self.client

    def fetch_data(self, 
                   metrics: List[str], 
                   dimensions: List[str], 
                   start_date: str = "yesterday", 
                   end_date: str = "today") -> List[Dict[str, Any]]:
        """
        Dynamically executes a RunReportRequest against the GA4 Data API.
        """
        if not self.client or not self.property_id:
            raise Exception("GA4 Connector not authenticated. Call authenticate() first.")

        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )

        response = self.client.run_report(request)
        return self._parse_response(response)

    def test_connection(self) -> bool:
        """
        Validates the connection by attempting a minimal metadata fetch.
        """
        try:
            # Simple metadata fetch to check if property is accessible
            self.client.get_metadata(name=f"properties/{self.property_id}/metadata")
            return True
        except Exception as e:
            print(f"GA4 Connection Test Failed: {e}")
            return False

    def _parse_response(self, response) -> List[Dict[str, Any]]:
        """
        Parses the raw GA4 RunReportResponse into a flat list of dictionaries.
        """
        results = []
        dimension_headers = [header.name for header in response.dimension_headers]
        metric_headers = [header.name for header in response.metric_headers]

        for row in response.rows:
            record = {}
            for i, val in enumerate(row.dimension_values):
                record[dimension_headers[i]] = val.value
            for i, val in enumerate(row.metric_values):
                # Try to convert numeric values where possible
                try:
                    record[metric_headers[i]] = float(val.value) if '.' in val.value else int(val.value)
                except ValueError:
                    record[metric_headers[i]] = val.value
            results.append(record)
        
        return results
