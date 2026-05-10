from __future__ import annotations

from typing import Optional, Dict, Type
from pydantic import BaseModel

from datetime import date, datetime


# ------------------------------------------------------------------ #
#  1. fb_ads_campaigns_asset
# ------------------------------------------------------------------ #
class FacebookAdsCampaignsAsset(BaseModel):
    account_id: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    objective: Optional[str] = None
    start_time: Optional[str] = None
    stop_time: Optional[str] = None
    daily_budget: Optional[str] = None
    lifetime_budget: Optional[str] = None
    bid_strategy: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None

    __datetime_fields__ = ["created_time", "updated_time"]


# ------------------------------------------------------------------ #
#  2. fb_ads_adsets_asset
# ------------------------------------------------------------------ #
class FacebookAdsAdsetsAsset(BaseModel):
    account_id: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    campaign_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    daily_budget: Optional[str] = None
    lifetime_budget: Optional[str] = None
    optimization_goal: Optional[str] = None
    promoted_object: Optional[str] = None  # JSON
    billing_event: Optional[str] = None
    bid_amount: Optional[str] = None
    bid_strategy: Optional[str] = None
    attribution_setting: Optional[str] = None
    targeting: Optional[str] = None  # JSON
    attribution_spec: Optional[str] = None  # JSON
    is_dynamic_creative: Optional[bool] = None
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None

    __json_fields__ = [
        "promoted_object",
        "targeting",
        "attribution_spec",
        "bid_amount",
    ]
    __datetime_fields__ = ["created_time", "updated_time"]


# ------------------------------------------------------------------ #
#  3. fb_ads_ads_asset
# ------------------------------------------------------------------ #
class FacebookAdsAdsAsset(BaseModel):
    account_id: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    adset_id: Optional[str] = None
    campaign_id: Optional[str] = None
    creative: Optional[str] = None  # JSON
    targeting: Optional[str] = None  # JSON
    tracking_specs: Optional[str] = None  # JSON
    conversion_specs: Optional[str] = None  # JSON
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None

    __json_fields__ = [
        "creative",
        "targeting",
        "tracking_specs",
        "conversion_specs",
    ]
    __datetime_fields__ = ["created_time", "updated_time"]


# ------------------------------------------------------------------ #
#  4. fb_ads_adcreatives_asset
# ------------------------------------------------------------------ #
class FacebookAdsAdcreativesAsset(BaseModel):
    account_id: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    image_hash: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    call_to_action_type: Optional[str] = None
    object_type: Optional[str] = None
    object_story_spec: Optional[str] = None
    link_url: Optional[str] = None
    instagram_permalink_url: Optional[str] = None
    asset_feed_spec: Optional[str] = None
    video_id: Optional[str] = None
    url_tags: Optional[str] = None
    object_url: Optional[str] = None
    product_set_id: Optional[str] = None
    template_url: Optional[str] = None
    template_url_spec: Optional[str] = None
    use_page_actor_override: Optional[bool] = None
    applink_treatment: Optional[str] = None
    branded_content_sponsor_page_id: Optional[str] = None
    effective_object_story_id: Optional[str] = None
    object_id: Optional[str] = None
    object_story_id: Optional[str] = None
    actor_id: Optional[str] = None
    adlabels: Optional[str] = None
    authorization_category: Optional[str] = None
    dynamic_ad_voice: Optional[str] = None
    image_crops: Optional[str] = None
    degrees_of_freedom_spec: Optional[str] = None
    categorization_criteria: Optional[str] = None
    instagram_user_id: Optional[str] = None
    branded_content: Optional[str] = None
    call_to_action: Optional[str] = None
    effective_instagram_media_id: Optional[str] = None
    bundle_folder_id: Optional[str] = None
    effective_authorization_category: Optional[str] = None
    facebook_branded_content: Optional[str] = None
    product_data: Optional[str] = None
    dynamic_images_object: Optional[str] = None

    __json_fields__ = [
        "object_story_spec",
        "asset_feed_spec",
        "template_url_spec",
        "adlabels",
        "image_crops",
        "degrees_of_freedom_spec",
        "categorization_criteria",
        "branded_content",
        "call_to_action",
        "facebook_branded_content",
        "product_data",
        "dynamic_images_object",
    ]


# ------------------------------------------------------------------ #
#  5. fb_ads_age_gender_metrics
# ------------------------------------------------------------------ #
class FacebookAdsAgeGenderMetrics(BaseModel):
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    reach: Optional[str] = None
    frequency: Optional[str] = None
    cpm: Optional[str] = None
    cpc: Optional[str] = None
    ctr: Optional[str] = None
    actions: Optional[str] = None  # JSON
    conversions: Optional[str] = None  # JSON
    age: Optional[str] = None
    gender: Optional[str] = None
    video_avg_time_watched_actions: Optional[str] = None  # JSON
    video_p25_watched_actions: Optional[str] = None  # JSON
    video_p50_watched_actions: Optional[str] = None  # JSON
    video_p75_watched_actions: Optional[str] = None  # JSON
    video_p100_watched_actions: Optional[str] = None  # JSON
    video_play_actions: Optional[str] = None  # JSON
    unique_clicks: Optional[str] = None
    inline_link_clicks: Optional[str] = None
    inline_post_engagement: Optional[str] = None
    outbound_clicks: Optional[str] = None
    action_values: Optional[str] = None

    __json_fields__ = [
        "actions",
        "conversions",
        "action_values",
        "outbound_clicks",
        "video_avg_time_watched_actions",
        "video_p25_watched_actions",
        "video_p50_watched_actions",
        "video_p75_watched_actions",
        "video_p100_watched_actions",
        "video_play_actions",
    ]
    __date_fields__ = ["date_start", "date_stop"]


# ------------------------------------------------------------------ #
#  6. fb_ads_platform_metrics
# ------------------------------------------------------------------ #
class FacebookAdsPlatformMetrics(BaseModel):
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    reach: Optional[str] = None
    frequency: Optional[str] = None
    cpm: Optional[str] = None
    cpc: Optional[str] = None
    ctr: Optional[str] = None
    publisher_platform: Optional[str] = None
    platform_position: Optional[str] = None
    impression_device: Optional[str] = None
    unique_clicks: Optional[str] = None
    video_30_sec_watched_actions: Optional[str] = None
    video_play_actions: Optional[str] = None
    video_play_curve_actions: Optional[str] = None
    video_p100_watched_actions: Optional[str] = None
    video_avg_time_watched_actions: Optional[str] = None
    video_p25_watched_actions: Optional[str] = None
    video_p50_watched_actions: Optional[str] = None
    video_p75_watched_actions: Optional[str] = None
    video_p95_watched_actions: Optional[str] = None
    inline_post_engagement: Optional[str] = None
    inline_link_clicks: Optional[str] = None
    actions: Optional[str] = None  # JSON
    action_values: Optional[str] = None  # JSON
    website_ctr: Optional[str] = None  # JSON
    outbound_clicks: Optional[str] = None  # JSON
    purchase_roas: Optional[str] = None  # JSON
    cost_per_action_type: Optional[str] = None  # JSON
    objective: Optional[str] = None

    # Flattened Action Metrics
    purchases: Optional[int] = None
    add_to_cart: Optional[int] = None
    initiate_checkout: Optional[int] = None
    view_content: Optional[int] = None
    landing_page_view: Optional[int] = None
    link_click: Optional[int] = None
    video_view: Optional[int] = None
    add_payment_info: Optional[int] = None

    # Flattened Action Values
    purchase_value: Optional[float] = None
    add_to_cart_value: Optional[float] = None
    view_content_value: Optional[float] = None

    # Flattened Costs
    cost_per_purchase: Optional[float] = None
    cost_per_add_to_cart: Optional[float] = None
    cost_per_initiate_checkout: Optional[float] = None
    cost_per_outbound_click: Optional[float] = None
    cost_per_inline_link_click: Optional[float] = None
    cost_per_unique_click: Optional[float] = None
    cost_per_landing_page_view: Optional[float] = None
    cost_per_view_content: Optional[float] = None

    __json_fields__ = [
        "video_30_sec_watched_actions",
        "video_play_actions",
        "video_play_curve_actions",
        "video_p100_watched_actions",
        "video_avg_time_watched_actions",
        "video_p25_watched_actions",
        "video_p50_watched_actions",
        "video_p75_watched_actions",
        "video_p95_watched_actions",
        "actions",
        "action_values",
        "website_ctr",
        "outbound_clicks",
        "purchase_roas",
        "cost_per_action_type",
    ]
    __date_fields__ = ["date_start", "date_stop"]


# ------------------------------------------------------------------ #
#  7. fb_ads_region_metrics
# ------------------------------------------------------------------ #
class FacebookAdsRegionMetrics(BaseModel):
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    reach: Optional[str] = None
    frequency: Optional[str] = None
    cpm: Optional[str] = None
    cpc: Optional[str] = None
    ctr: Optional[str] = None
    actions: Optional[str] = None  # JSON
    conversions: Optional[str] = None  # JSON
    region: Optional[str] = None
    unique_clicks: Optional[str] = None
    inline_link_clicks: Optional[str] = None
    inline_post_engagement: Optional[str] = None
    outbound_clicks: Optional[str] = None  # JSON

    __json_fields__ = ["actions", "conversions", "outbound_clicks"]
    __date_fields__ = ["date_start", "date_stop"]


# ------------------------------------------------------------------ #
#  8. fb_ads_product_metrics
# ------------------------------------------------------------------ #
class FacebookAdsProductMetrics(BaseModel):
    campaign_id: Optional[str] = None
    date_start: Optional[date] = None
    adset_id: Optional[str] = None
    ad_id: Optional[str] = None
    account_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_name: Optional[str] = None
    ad_name: Optional[str] = None
    date_stop: Optional[date] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    reach: Optional[str] = None
    frequency: Optional[str] = None
    cpm: Optional[str] = None
    cpc: Optional[str] = None
    ctr: Optional[str] = None
    actions: Optional[str] = None  # JSON
    conversions: Optional[str] = None  # JSON
    product_id: Optional[str] = None
    inline_link_clicks: Optional[str] = None
    inline_post_engagement: Optional[str] = None
    outbound_clicks: Optional[str] = None
    action_values: Optional[str] = None

    __json_fields__ = [
        "actions",
        "conversions",
        "action_values",
        "outbound_clicks",
    ]
    __date_fields__ = ["date_start", "date_stop"]


# ------------------------------------------------------------------ #
#  9. fb_ads_hourly_audience_metrics
# ------------------------------------------------------------------ #
class FacebookAdsHourlyAudienceMetrics(BaseModel):
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    ctr: Optional[str] = None
    cpc: Optional[str] = None
    cpm: Optional[str] = None
    cpp: Optional[str] = None
    spend: Optional[str] = None
    actions: Optional[str] = None  # JSON
    action_values: Optional[str] = None  # JSON
    cost_per_action_type: Optional[str] = None  # JSON
    website_ctr: Optional[str] = None  # JSON
    inline_link_clicks: Optional[str] = None
    inline_post_engagement: Optional[str] = None
    outbound_clicks: Optional[str] = None  # JSON
    hourly_stats_aggregated_by_audience_time_zone: Optional[str] = None

    __json_fields__ = [
        "actions",
        "action_values",
        "cost_per_action_type",
        "website_ctr",
        "outbound_clicks",
    ]
    __date_fields__ = ["date_start", "date_stop"]


# ------------------------------------------------------------------ #
#  10. fb_ads_hourly_advertiser_metrics
# ------------------------------------------------------------------ #
class FacebookAdsHourlyAdvertiserMetrics(BaseModel):
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    ctr: Optional[str] = None
    cpc: Optional[str] = None
    cpm: Optional[str] = None
    cpp: Optional[str] = None
    spend: Optional[str] = None
    actions: Optional[str] = None  # JSON
    action_values: Optional[str] = None  # JSON
    cost_per_action_type: Optional[str] = None  # JSON
    website_ctr: Optional[str] = None  # JSON
    inline_link_clicks: Optional[str] = None
    inline_post_engagement: Optional[str] = None
    video_30_sec_watched_actions: Optional[str] = None  # JSON
    video_p25_watched_actions: Optional[str] = None  # JSON
    video_p50_watched_actions: Optional[str] = None  # JSON
    video_p75_watched_actions: Optional[str] = None  # JSON
    video_p95_watched_actions: Optional[str] = None  # JSON
    video_p100_watched_actions: Optional[str] = None  # JSON
    video_avg_time_watched_actions: Optional[str] = None  # JSON
    video_play_actions: Optional[str] = None  # JSON
    outbound_clicks: Optional[str] = None  # JSON
    reach: Optional[str] = None
    frequency: Optional[str] = None
    conversions: Optional[str] = None  # JSON
    hour: Optional[str] = None

    __json_fields__ = [
        "actions",
        "action_values",
        "cost_per_action_type",
        "website_ctr",
        "video_30_sec_watched_actions",
        "video_p25_watched_actions",
        "video_p50_watched_actions",
        "video_p75_watched_actions",
        "video_p95_watched_actions",
        "video_p100_watched_actions",
        "video_avg_time_watched_actions",
        "video_play_actions",
        "outbound_clicks",
        "conversions",
    ]
    __date_fields__ = ["date_start", "date_stop"]


# ------------------------------------------------------------------ #
#  11-15. Dynamic Creative breakdown metrics
# ------------------------------------------------------------------ #
class FacebookAdsImageAssetMetrics(BaseModel):
    account_id: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    image_asset: Optional[str] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    actions: Optional[str] = None
    action_values: Optional[str] = None

    __json_fields__ = [
        "image_asset",
        "actions",
        "action_values",
    ]
    __date_fields__ = ["date_start", "date_stop"]


class FacebookAdsBodyAssetMetrics(BaseModel):
    account_id: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    body_asset: Optional[str] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    actions: Optional[str] = None
    action_values: Optional[str] = None

    __json_fields__ = [
        "body_asset",
        "actions",
        "action_values",
    ]
    __date_fields__ = ["date_start", "date_stop"]


class FacebookAdsTitleAssetMetrics(BaseModel):
    account_id: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    title_asset: Optional[str] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    actions: Optional[str] = None
    action_values: Optional[str] = None

    __json_fields__ = [
        "title_asset",
        "actions",
        "action_values",
    ]
    __date_fields__ = ["date_start", "date_stop"]


class FacebookAdsVideoAssetMetrics(BaseModel):
    account_id: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    video_asset: Optional[str] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    actions: Optional[str] = None
    action_values: Optional[str] = None

    __json_fields__ = [
        "video_asset",
        "actions",
        "action_values",
    ]
    __date_fields__ = ["date_start", "date_stop"]


class FacebookAdsDescriptionAssetMetrics(BaseModel):
    account_id: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    date_start: Optional[date] = None
    date_stop: Optional[date] = None
    description_asset: Optional[str] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    spend: Optional[str] = None
    actions: Optional[str] = None
    action_values: Optional[str] = None

    __json_fields__ = [
        "description_asset",
        "actions",
        "action_values",
    ]
    __date_fields__ = ["date_start", "date_stop"]


# ------------------------------------------------------------------ #
#  model registry
# ------------------------------------------------------------------ #
FACEBOOK_ADS_MODELS: Dict[str, Type[BaseModel]] = {
    "FacebookAdsCampaignsAsset": FacebookAdsCampaignsAsset,
    "FacebookAdsAdsetsAsset": FacebookAdsAdsetsAsset,
    "FacebookAdsAdsAsset": FacebookAdsAdsAsset,
    "FacebookAdsAdcreativesAsset": FacebookAdsAdcreativesAsset,
    "FacebookAdsAgeGenderMetrics": FacebookAdsAgeGenderMetrics,
    "FacebookAdsPlatformMetrics": FacebookAdsPlatformMetrics,
    "FacebookAdsRegionMetrics": FacebookAdsRegionMetrics,
    "FacebookAdsProductMetrics": FacebookAdsProductMetrics,
    "FacebookAdsHourlyAudienceMetrics": FacebookAdsHourlyAudienceMetrics,
    "FacebookAdsHourlyAdvertiserMetrics": FacebookAdsHourlyAdvertiserMetrics,
    "FacebookAdsImageAssetMetrics": FacebookAdsImageAssetMetrics,
    "FacebookAdsBodyAssetMetrics": FacebookAdsBodyAssetMetrics,
    "FacebookAdsTitleAssetMetrics": FacebookAdsTitleAssetMetrics,
    "FacebookAdsVideoAssetMetrics": FacebookAdsVideoAssetMetrics,
    "FacebookAdsDescriptionAssetMetrics": FacebookAdsDescriptionAssetMetrics,
}
