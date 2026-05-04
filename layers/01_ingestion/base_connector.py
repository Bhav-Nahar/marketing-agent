from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseConnector(ABC):
    """
    Abstract Base Class for all marketing data connectors (GA4, Google Ads, Meta, Shopify).
    Each connector must implement its own authentication and fetching logic.
    """

    @abstractmethod
    def authenticate(self, credentials_data: Dict[str, Any]) -> Any:
        """
        Authenticates with the platform's API using provided credentials.
        Returns the platform-specific credentials/client object.
        """
        pass

    @abstractmethod
    def fetch_data(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetches data based on the provided configuration (metrics, dimensions, date range).
        Returns a list of standardized dictionaries representing the fetched records.
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Tests the connection to the API to ensure authentication is working correctly.
        """
        pass
