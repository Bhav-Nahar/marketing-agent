from typing import Dict, List, Optional
import json
import time
import logging
import random
import requests
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adreportrun import AdReportRun
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)

MAX_WAIT_TIME = 300
POLL_INTERVAL = 2
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2
TRANSIENT_ERROR_CODES = [2, 4, 17, 32, 613]
MAX_INSIGHTS_MONTHS = 37


def retry_on_facebook_error(func):
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except FacebookRequestError as e:
                error_data = (
                    e.api_error_message() if hasattr(e, "api_error_message") else str(e)
                )
                is_transient = (
                    (
                        hasattr(e, "api_error_code")
                        and e.api_error_code() in TRANSIENT_ERROR_CODES
                    )
                    or "is_transient" in str(error_data)
                    or "temporarily" in str(error_data).lower()
                )
                if is_transient and attempt < MAX_RETRIES - 1:
                    delay = BASE_RETRY_DELAY * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"Transient error, retrying in {delay:.2f}s: {error_data}"
                    )
                    time.sleep(delay)
                    continue
                logger.error(
                    f"Facebook API error after {attempt + 1} attempts: {error_data}"
                )
                if is_transient:
                    return []
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
        return []

    return wrapper


class FacebookClient:
    @staticmethod
    def get_access_token(
        app_id: str, app_secret: str, current_token: str, api_version: str = "v23.0"
    ) -> str:
        if not all([app_id, app_secret, current_token]):
            raise ValueError(
                "Missing Facebook credentials: app_id, app_secret, and current_token required"
            )

        try:
            token_info = FacebookClient._validate_token(
                current_token, app_id, app_secret, api_version
            )
            is_valid = token_info.get("is_valid", False)
            expires_at = token_info.get("expires_at", 0)

            current_time = int(time.time())
            expires_soon = expires_at > 0 and (expires_at - current_time) < (
                7 * 24 * 60 * 60
            )

            if is_valid and not expires_soon:
                logger.info("✅ Current Facebook token is valid")
                return current_token

            logger.info("🔄 Exchanging Facebook token...")
            response = requests.get(
                f"https://graph.facebook.com/{api_version}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": current_token,
                },
                timeout=30,
            )
            response.raise_for_status()
            token_data = response.json()

            if "access_token" not in token_data:
                raise ValueError("No access_token found in Facebook response")

            logger.info(
                f"✅ Got long-lived token (expires in: {token_data.get('expires_in', 'Unknown')}s)"
            )
            return token_data["access_token"]

        except Exception as e:
            logger.error(f"❌ Failed to process Facebook token: {e}")
            raise

    @staticmethod
    def _validate_token(
        access_token: str, app_id: str, app_secret: str, api_version: str
    ) -> Dict[str, any]:
        try:
            logger.info("🔍 Validating Facebook access token...")

            app_response = requests.get(
                f"https://graph.facebook.com/{api_version}/oauth/access_token",
                params={
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "grant_type": "client_credentials",
                },
                timeout=30,
            )
            app_response.raise_for_status()
            app_access_token = app_response.json()["access_token"]

            debug_response = requests.get(
                f"https://graph.facebook.com/{api_version}/debug_token",
                params={"input_token": access_token, "access_token": app_access_token},
                timeout=30,
            )
            debug_response.raise_for_status()
            debug_data = debug_response.json()

            if "data" not in debug_data:
                raise ValueError("Invalid debug_token response format")

            token_info = debug_data["data"]
            logger.info(
                f"✅ Token valid: {token_info.get('is_valid')}, expires: {token_info.get('expires_at')}"
            )
            return token_info

        except Exception as e:
            logger.error(f"❌ Failed to validate Facebook token: {e}")
            raise

    def __init__(self, access_token: str, account_id: str):
        FacebookAdsApi.init(access_token=access_token, api_version="v24.0")
        self.account_id = (
            f"act_{account_id}" if not account_id.startswith("act_") else account_id
        )
        self.ad_account = AdAccount(self.account_id)
        self._access_token = access_token
        self._creative_ids_cache = set()

    def _get_account_id(self) -> str:
        return self.account_id.replace("act_", "")

    @staticmethod
    def _to_unix_timestamp(date_str: str) -> int:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp())

    _ALL_STATUSES = [
        "ACTIVE",
        "PAUSED",
        "ARCHIVED",
        "PENDING_REVIEW",
        "DISAPPROVED",
        "PREAPPROVED",
        "PENDING_BILLING_INFO",
        "CAMPAIGN_PAUSED",
        "ADSET_PAUSED",
        "IN_PROCESS",
        "WITH_ISSUES",
    ]

    def _build_date_filter(self, since_date: str, until_date: str = None) -> Dict:
        params = {
            "effective_status": self._ALL_STATUSES,
        }
        if since_date:
            filters = [
                {
                    "field": "updated_time",
                    "operator": "GREATER_THAN",
                    "value": self._to_unix_timestamp(since_date),
                }
            ]
            if until_date:
                filters.append(
                    {
                        "field": "updated_time",
                        "operator": "LESS_THAN",
                        "value": self._to_unix_timestamp(until_date),
                    }
                )
            params["filtering"] = filters
        return params

    def _fetch_objects(self, fetch_func, fields: List[str], params: Dict) -> List[Dict]:
        results = []
        for obj in fetch_func(fields=fields, params=params):
            data = obj.export_all_data()
            data["account_id"] = self._get_account_id()
            results.append(data)
        return results

    @retry_on_facebook_error
    def get_campaigns(
        self, since_date: str = None, fields: List[str] = None, until_date: str = None
    ) -> List[Dict]:
        return self._fetch_objects(
            self.ad_account.get_campaigns,
            fields,
            self._build_date_filter(since_date, until_date),
        )

    @retry_on_facebook_error
    def get_adsets(
        self, since_date: str = None, fields: List[str] = None, until_date: str = None
    ) -> List[Dict]:
        return self._fetch_objects(
            self.ad_account.get_ad_sets,
            fields,
            self._build_date_filter(since_date, until_date),
        )

    @retry_on_facebook_error
    def get_ads(
        self, since_date: str = None, fields: List[str] = None, until_date: str = None
    ) -> List[Dict]:
        results = self._fetch_objects(
            self.ad_account.get_ads,
            fields,
            self._build_date_filter(since_date, until_date),
        )
        for ad in results:
            creative = ad.get("creative")
            if isinstance(creative, dict) and creative.get("id"):
                creative_id = str(creative["id"]).strip()
                if creative_id and creative_id.lower() != "none":
                    self._creative_ids_cache.add(creative_id)
        return results

    def get_all_adcreatives(
        self, fields: List[str] = None, prefetch_batch_size: int = 200
    ):
        count = 0
        buffer: List[Dict] = []

        def _flush_buffer(buf: List[Dict]):
            for item in buf:
                try:
                    self._enrich_creative_with_media(item)
                    yield item
                except Exception as e:
                    logger.error(f"Error enriching creative: {e}")

        try:
            for obj in self.ad_account.get_ad_creatives(fields=fields, params={}):
                try:
                    data = obj.export_all_data()
                    data["account_id"] = self._get_account_id()
                    buffer.append(data)
                    count += 1
                    if count % 100 == 0:
                        logger.info(f"Fetched {count} ad creatives so far...")

                    if len(buffer) >= prefetch_batch_size:
                        yield from _flush_buffer(buffer)
                        buffer = []

                except Exception as e:
                    logger.error(f"Error processing creative: {e}")
                    continue

            if buffer:
                yield from _flush_buffer(buffer)

        except FacebookRequestError as e:
            logger.error(f"Facebook API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    @retry_on_facebook_error
    def get_image_permalink(self, image_hash: str) -> Optional[str]:
        try:
            images = self.ad_account.get_ad_images(
                fields=["permalink_url"], params={"hashes": [image_hash]}
            )
            for img in images:
                return img.export_all_data().get("permalink_url")
        except Exception as e:
            logger.warning(f"Failed to get image permalink {image_hash}: {e}")
        return None

    @retry_on_facebook_error
    def get_image_permalinks_bulk(self, image_hashes: List[str]) -> Dict[str, str]:
        if not image_hashes:
            return {}

        hash_to_permalink = {}
        try:
            images = self.ad_account.get_ad_images(
                fields=["hash", "permalink_url"], params={"hashes": image_hashes}
            )
            for img in images:
                img_data = img.export_all_data()
                img_hash = img_data.get("hash")
                permalink = img_data.get("permalink_url")
                if img_hash and permalink:
                    hash_to_permalink[img_hash] = permalink
        except Exception as e:
            logger.warning(f"Failed to get bulk image permalinks: {e}")

        return hash_to_permalink

    def _get_adaptive_sleep(self, response, base_sleep: float = 1.0) -> float:
        try:
            if hasattr(response, "headers") and callable(response.headers):
                headers = response.headers()
            else:
                headers = getattr(response, "headers", {}) or {}

            max_pct = 0.0

            ad_usage = headers.get("x-ad-account-usage") or headers.get(
                "X-Ad-Account-Usage"
            )
            if ad_usage:
                max_pct = max(
                    max_pct, float(json.loads(ad_usage).get("acc_id_util_pct", 0))
                )

            app_usage = headers.get("x-app-usage") or headers.get("X-App-Usage")
            if app_usage:
                data = json.loads(app_usage)
                max_pct = max(
                    max_pct,
                    float(
                        max(
                            data.get("call_count", 0),
                            data.get("total_cputime", 0),
                            data.get("total_time", 0),
                        )
                    ),
                )

            buc_usage = headers.get("x-business-use-case-usage") or headers.get(
                "X-Business-Use-Case-Usage"
            )
            if buc_usage:
                for account_data in json.loads(buc_usage).values():
                    if isinstance(account_data, list):
                        for item in account_data:
                            max_pct = max(
                                max_pct,
                                float(
                                    max(
                                        item.get("call_count", 0),
                                        item.get("total_cputime", 0),
                                        item.get("total_time", 0),
                                    )
                                ),
                            )

            if max_pct >= 90:
                sleep_time = 10.0
            elif max_pct >= 80:
                sleep_time = 5.0
            elif max_pct >= 60:
                sleep_time = 2.0
            else:
                sleep_time = base_sleep

            if sleep_time > base_sleep:
                logger.warning(
                    f"Rate limit at {max_pct:.0f}% — adaptive sleep {sleep_time}s"
                )

            return sleep_time
        except Exception:
            return base_sleep

    def _extract_image_hash_from_root(self, data: Dict) -> List[str]:
        return [data["image_hash"]] if data.get("image_hash") else []

    def _extract_image_hashes_from_asset_feed_spec(
        self, asset_feed_spec: Dict
    ) -> List[str]:
        hashes = []
        images = asset_feed_spec.get("images", [])
        if isinstance(images, list):
            for img in images:
                if isinstance(img, dict) and img.get("hash"):
                    hashes.append(img["hash"])
        return hashes

    def _extract_image_hashes_from_story_spec(self, story_spec: Dict) -> List[str]:
        hashes = []

        link_data = story_spec.get("link_data", {})
        if isinstance(link_data, dict) and link_data.get("image_hash"):
            hashes.append(link_data["image_hash"])

        child_attachments = story_spec.get("child_attachments", [])
        if isinstance(child_attachments, list):
            for child in child_attachments:
                if isinstance(child, dict) and child.get("image_hash"):
                    hashes.append(child["image_hash"])

        if isinstance(link_data, dict):
            link_data_children = link_data.get("child_attachments", [])
            if isinstance(link_data_children, list):
                for child in link_data_children:
                    if isinstance(child, dict) and child.get("image_hash"):
                        hashes.append(child["image_hash"])

        return hashes

    def _extract_all_image_hashes(self, data: Dict) -> List[str]:
        all_hashes = []

        all_hashes.extend(self._extract_image_hash_from_root(data))

        asset_feed_spec = data.get("asset_feed_spec")
        if asset_feed_spec:
            try:
                if isinstance(asset_feed_spec, str):
                    asset_feed_spec = json.loads(asset_feed_spec)
                if isinstance(asset_feed_spec, dict):
                    all_hashes.extend(
                        self._extract_image_hashes_from_asset_feed_spec(asset_feed_spec)
                    )
            except Exception as e:
                logger.warning(f"Failed to parse asset_feed_spec: {e}")

        story_spec = data.get("object_story_spec")
        if isinstance(story_spec, dict):
            all_hashes.extend(self._extract_image_hashes_from_story_spec(story_spec))

        return list(set(all_hashes))

    def _enrich_with_image_permalinks(
        self, data: Dict, image_hashes: List[str]
    ) -> None:
        if not image_hashes:
            return

        try:
            hash_to_permalink = self.get_image_permalinks_bulk(image_hashes)
            dynamic_images = [
                {"hash": h, "permalink": hash_to_permalink.get(h, "")}
                for h in image_hashes
            ]
            data["dynamic_images_object"] = json.dumps(dynamic_images)
        except Exception as e:
            logger.warning(f"Failed to fetch bulk image permalinks: {e}")

    def _enrich_with_link_picture(self, data: Dict, story_spec: Dict) -> None:
        try:
            link_picture = story_spec.get("link_data", {}).get("picture")
            if link_picture:
                data["link_image_url"] = link_picture
        except Exception as e:
            logger.warning(f"Failed to enrich link picture: {e}")

    def _enrich_creative_with_media(self, data: Dict) -> None:
        image_hashes = self._extract_all_image_hashes(data)
        self._enrich_with_image_permalinks(data, image_hashes)

        story_spec = data.get("object_story_spec")
        if isinstance(story_spec, dict):
            self._enrich_with_link_picture(data, story_spec)

    def get_creative_ids_from_ads(self) -> List[str]:
        if self._creative_ids_cache:
            return list(self._creative_ids_cache)
        self.get_ads(fields=["id", "creative"])
        return list(self._creative_ids_cache)

    def _fetch_creative_batch(
        self, api, batch_ids: List[str], fields: List[str]
    ) -> dict:
        """Fetch a batch of creatives, halving the batch on payload-too-large (code 1) errors."""
        if not batch_ids:
            return {}
        try:
            response = api.call(
                "GET",
                (),
                params={"ids": ",".join(batch_ids), "fields": ",".join(fields)},
            )
            return response.json()
        except Exception as e:
            err_str = str(e)
            is_payload_too_large = (
                '"code": 1' in err_str or '"code":1' in err_str
            ) and "reduce the amount of data" in err_str
            if is_payload_too_large and len(batch_ids) > 1:
                half = max(1, len(batch_ids) // 2)
                logger.warning(
                    f"Payload too large for {len(batch_ids)} creatives — retrying as {half} + {len(batch_ids) - half}"
                )
                result = {}
                result.update(self._fetch_creative_batch(api, batch_ids[:half], fields))
                result.update(self._fetch_creative_batch(api, batch_ids[half:], fields))
                return result
            raise

    def get_adcreatives_by_ids(
        self, creative_ids: List[str], fields: List[str], batch_size: int = 10
    ):
        if not creative_ids:
            return

        creative_ids = [
            cid
            for cid in creative_ids
            if cid and str(cid).strip() and str(cid).strip().lower() != "none"
        ]

        if not creative_ids:
            logger.warning("No valid creative IDs found after filtering")
            return

        api = FacebookAdsApi.get_default_api()
        all_creatives = []
        total_batches = (len(creative_ids) + batch_size - 1) // batch_size
        logger.info(
            f"Fetching {len(creative_ids)} ad creatives across {total_batches} batches (batch_size={batch_size})"
        )

        for i in range(0, len(creative_ids), batch_size):
            batch_ids = [
                bid
                for bid in creative_ids[i : i + batch_size]
                if bid and str(bid).strip()
            ]
            if not batch_ids:
                logger.warning(f"Empty batch at index {i}, skipping")
                continue

            batch_num = i // batch_size + 1
            try:
                data_map = self._fetch_creative_batch(api, batch_ids, fields)
                for creative_data in data_map.values():
                    creative_data["account_id"] = self._get_account_id()
                    all_creatives.append(creative_data)
            except Exception as e:
                logger.warning(f"Batch {batch_num}/{total_batches} fetch failed: {e}")

            if batch_num % 25 == 0 or batch_num == total_batches:
                logger.info(
                    f"Creative fetch progress: {batch_num}/{total_batches} batches done ({len(all_creatives)} creatives so far)"
                )

            if i + batch_size < len(creative_ids):
                time.sleep(1.5)

        logger.info(f"Fetched {len(all_creatives)} creatives, enriching with media now")

        results = []
        for creative_data in all_creatives:
            self._enrich_creative_with_media(creative_data)
            results.append(creative_data)
        if results:
            yield results
        logger.info(f"Retrieved {len(results)} ad creatives by ID")

    def _enforce_max_insights_date(
        self, date_range: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        min_date = (datetime.now() - timedelta(days=MAX_INSIGHTS_MONTHS * 30)).strftime(
            "%Y-%m-%d"
        )
        since = date_range.get("since", "")
        until = date_range.get("until", "")

        if until and until < min_date:
            return None

        if since and since < min_date:
            date_range = {**date_range, "since": min_date}
        return date_range

    @retry_on_facebook_error
    def run_async_insights_job(
        self, date_range: Dict[str, str], fields: List[str], **params
    ) -> List[Dict]:
        date_range = self._enforce_max_insights_date(date_range)
        if date_range is None:
            return []
        job_params = {
            "time_range": date_range,
            "time_increment": 1,
            "fields": fields,
            **params,
        }
        async_job = self.ad_account.get_insights(params=job_params, is_async=True)
        job_id = (
            async_job.get_id()
            if hasattr(async_job, "get_id")
            else async_job["report_run_id"]
        )

        report_run = AdReportRun(job_id)
        wait_time = 0
        while wait_time < MAX_WAIT_TIME:
            time.sleep(POLL_INTERVAL)
            wait_time += POLL_INTERVAL
            report_run.api_get(fields=["async_status", "async_percent_completion"])
            status = report_run.get("async_status")
            if status == "Job Completed":
                break
            if status in ["Job Failed", "Job Skipped"]:
                logger.warning(f"Job {job_id} {status}")
                return []

        if wait_time >= MAX_WAIT_TIME:
            logger.error(f"Job {job_id} timed out")
            return []

        results = []
        for insight in report_run.get_insights():
            data = insight.export_all_data()
            data["account_id"] = self._get_account_id()
            results.append(data)
        return results
