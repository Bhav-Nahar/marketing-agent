from typing import Dict, Any
from .credentials import FacebookAdsCredentials

class FacebookAdsPlugin:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def validate_config(self) -> bool:
        return True

    def process_credentials(self) -> Dict[str, Any]:
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
        
        # In the MVP we skip validation and directly use the token
        long_lived_token = credentials.long_lived_token or credentials.access_token

        lookback_days = source.get("lookbackDays", 7) or 7
        start_date = source.get("startDate")
        end_date = source.get("endDate")
        is_first_time_run = source.get("isFirstTimeRun")

        incremental_first_run = (
            str(is_first_time_run).lower() if is_first_time_run is not None else None
        )

        env_vars = {
            "DLT_SOURCES__FACEBOOK_ADS__ACCESS__TOKEN": credentials.access_token,
            "DLT_SOURCES__FACEBOOK_ADS__ACCOUNT__ID": ad_account_id,
            "DLT_SOURCES__FACEBOOK_ADS__CLIENT__ID": credentials.app_id,
            "DLT_SOURCES__FACEBOOK_ADS__CLIENT__SECRET": credentials.app_secret,
            "DLT_SOURCES__FACEBOOK_ADS__API_VERSION": api_version,
            "DLT_SOURCES__FACEBOOK_ADS__LONG_LIVED_ACCESS__TOKEN": long_lived_token,
            "DLT_SOURCES__FACEBOOK_ADS__ATTRIBUTION_WINDOW_DAYS_LAG": lookback_days,
            "DLT_SOURCES__FACEBOOK_ADS__INCREMENTAL_START_DATE": start_date or "2023-01-01",
            "DLT_SOURCES__FACEBOOK_ADS__INCREMENTAL_END_DATE": end_date,
            "DLT_SOURCES__FACEBOOK_ADS__INCREMENTAL_IS_FIRST_TIME_RUN": incremental_first_run,
        }

        return env_vars
