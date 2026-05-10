from typing import Dict, Any
from plugins.base.plugin import BaseConnectorPlugin


class FacebookAdsPlugin(BaseConnectorPlugin):

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    def validate_config(self) -> bool:
        return True

    def process_credentials(self) -> Dict[str, Any]:
        from plugins.connectors.facebook_ads.core.client import FacebookClient
        from plugins.connectors.facebook_ads.core.credentials import (
            FacebookAdsCredentials,
        )

        source = self.config.get("source", {})
        credentials_dict = source.get("config", {}).get("credentials", {})
        credentials = FacebookAdsCredentials(**credentials_dict)

        api_version = "v23.0"
        ad_account_id = credentials.ad_account_id
        ad_account_id = (
            (
                ad_account_id
                if str(ad_account_id).startswith("act_")
                else f"act_{ad_account_id}"
            )
            if ad_account_id
            else ""
        )
        app_id = credentials.app_id
        app_secret = credentials.app_secret
        access_token = credentials.access_token
        long_lived_token = credentials.long_lived_token

        lookback_days = source.get("lookbackDays", 7) or 7
        start_date = source.get("startDate")
        end_date = source.get("endDate")
        is_first_time_run = source.get("isFirstTimeRun")

        long_lived_token = FacebookClient.get_access_token(
            app_id=app_id,
            app_secret=app_secret,
            current_token=long_lived_token or access_token,
            api_version=api_version,
        )

        incremental_first_run = (
            str(is_first_time_run).lower() if is_first_time_run is not None else None
        )

        env_vars = {
            "DLT_SOURCES__FACEBOOK_ADS__ACCESS__TOKEN": access_token,
            "DLT_SOURCES__FACEBOOK_ADS__ACCOUNT__ID": ad_account_id,
            "DLT_SOURCES__FACEBOOK_ADS__CLIENT__ID": app_id,
            "DLT_SOURCES__FACEBOOK_ADS__CLIENT__SECRET": app_secret,
            "DLT_SOURCES__FACEBOOK_ADS__API_VERSION": api_version,
            "DLT_SOURCES__FACEBOOK_ADS__LONG_LIVED_ACCESS__TOKEN": long_lived_token,
            "DLT_SOURCES__FACEBOOK_ADS__ATTRIBUTION_WINDOW_DAYS_LAG": lookback_days,
            "DLT_SOURCES__FACEBOOK_ADS__INCREMENTAL_START_DATE": start_date
            or "2023-01-01",
            "DLT_SOURCES__FACEBOOK_ADS__INCREMENTAL_END_DATE": end_date,
            "DLT_SOURCES__FACEBOOK_ADS__INCREMENTAL_IS_FIRST_TIME_RUN": incremental_first_run,
        }

        return env_vars
