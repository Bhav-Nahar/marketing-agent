import dlt
from typing import Iterator, Dict
import logging
import os
from dlt.common import pendulum
from plugins.connectors.facebook_ads.core.models import FACEBOOK_ADS_MODELS
from helpers.dlt.utils import dlt_utils
from helpers.common.date_utils import ensure_date, convert_date_string_to_datetime
from plugins.connectors.facebook_ads.core.client import FacebookClient

logger = logging.getLogger(__name__)


def generate_date_chunks(
    start: pendulum.Date, end: pendulum.Date, days: int = 7
) -> Iterator[Dict[str, str]]:
    while start <= end:
        chunk_end = min(start.add(days=days - 1), end)
        yield {"since": start.to_date_string(), "until": chunk_end.to_date_string()}
        start = chunk_end.add(days=1)


@dlt.source(name="facebook_ads", max_table_nesting=0)
def create_facebook_ads_source(**kwargs):
    access_token = os.getenv("DLT_SOURCES__FACEBOOK_ADS__LONG_LIVED_ACCESS__TOKEN")
    account_id = os.getenv("DLT_SOURCES__FACEBOOK_ADS__ACCOUNT__ID")

    if not access_token or not account_id:
        raise ValueError("Missing Facebook Ads credentials")

    client = FacebookClient(access_token, account_id)
    rest_config = kwargs.get("rest_config", {})
    pipeline = kwargs.get("pipeline_instance")
    is_backfill = kwargs.get("is_backfill", False)
    dlt_resources = []
    for resource_config in rest_config.get("resources", []):
        name = resource_config["name"]
        endpoint = resource_config["endpoint"]
        schema_key = resource_config.get("schema_model")
        columns = FACEBOOK_ADS_MODELS.get(schema_key) if schema_key else None
        is_insights = "/insights" in endpoint.get("path", "")

        if is_insights:
            dlt_resources.append(
                create_insights_resource(
                    client,
                    resource_config,
                    columns,
                    pipeline=pipeline,
                    is_backfill=is_backfill,
                )
            )
        else:
            dlt_resources.append(
                create_asset_resource(
                    client,
                    resource_config,
                    columns,
                    pipeline=pipeline,
                    is_backfill=is_backfill,
                )
            )

    return dlt_resources


def create_insights_resource(client, config, columns, pipeline=None, is_backfill=False):
    name = config.get("name")
    table_name = config.get("table_name")
    partition_config = config.get("partition")
    endpoint = config.get("endpoint", {})
    params = endpoint.get("params", {})
    inc = endpoint.get("incremental", {})

    cursor_path = inc.get("cursor_path", "date_start")
    lag = inc.get("lag", 7)
    initial_value = inc.get("initial_value", None)
    end_value = inc.get("end_value", None)
    primary_key = config.get("primary_key", [])

    fields = [f.strip() for f in params.get("fields", "").split(",")]
    action_windows = [
        a.strip()
        for a in params.get("action_attribution_windows", "").split(",")
        if a.strip()
    ]
    breakdowns = [
        b.strip() for b in params.get("breakdowns", "").split(",") if b.strip()
    ]

    write_disp = config.get("write_disposition", "append")
    start_dt = ensure_date(initial_value)
    end_dt = ensure_date(end_value) if end_value else None
    effective_lag = dlt_utils.get_effective_lag(
        resource_name=name, cursor_path=cursor_path, base_lag=lag, pipeline=pipeline
    )

    @dlt.resource(
        name=name,
        table_name=table_name,
        primary_key=primary_key,
        columns=columns,
        write_disposition=write_disp,
        parallelized=False,
        schema_contract={
            "columns": "evolve",
            "tables": "evolve",
            "data_type": "freeze",
        },
    )
    def insights_resource(
        report_date=dlt.sources.incremental(
            cursor_path=cursor_path,
            initial_value=start_dt,
            end_value=end_dt,
            lag=effective_lag,
            last_value_func=max,
            on_cursor_value_missing="include",
        )
    ):
        actual_start = report_date.last_value if report_date.last_value else start_dt
        current = pendulum.now().date()
        max_end = actual_start.add(months=2)
        final_end = min(current, max_end, end_dt) if end_dt else min(current, max_end)

        logger.info(f"📅 {name}: {actual_start} to {final_end}")

        for dr in generate_date_chunks(actual_start, final_end, 7):
            try:
                records = client.run_async_insights_job(
                    date_range=dr,
                    fields=fields,
                    level=params.get("level", "ad"),
                    breakdowns=breakdowns or None,
                    action_attribution_windows=action_windows,
                )
                if records:
                    logger.info(
                        f"{name}: {len(records)} records for {dr['since']} to {dr['until']}"
                    )
                    yield from records
                else:
                    if not end_dt:
                        dlt_utils.move_incremental_cursor_forward(
                            cursor_path=cursor_path,
                            forward_value=ensure_date(dr["until"]),
                            is_backfill=is_backfill,
                        )
            except Exception as e:
                logger.error(f"Error processing {dr}: {e}")

    transformed = insights_resource.add_map(
        lambda r: dlt_utils.transform_record(r, columns)
    )
    return dlt_utils.apply_partition_to_resource(transformed, partition_config, name)


def create_asset_resource(client, config, columns, pipeline=None, is_backfill=False):
    name = config.get("name")
    table_name = config.get("table_name")
    partition_config = config.get("partition")
    endpoint = config.get("endpoint", {})
    params = endpoint.get("params", {})
    inc = endpoint.get("incremental", {})

    cursor_path = inc.get("cursor_path", "updated_time")
    lag = inc.get("lag", 7)
    initial_value = inc.get("initial_value")
    end_value = inc.get("end_value")
    primary_key = config.get("primary_key", ["id"])
    fields = [f.strip() for f in params.get("fields", "").split(",") if f.strip()]
    write_disp = config.get("write_disposition", "append")

    is_adcreatives = "adcreatives" in name or "ad_creatives" in name

    adcreatives_creative_ids = []
    if is_adcreatives:
        cached_ids = client.get_creative_ids_from_ads()
        if cached_ids:
            adcreatives_creative_ids = cached_ids
            logger.info(
                f"Using {len(adcreatives_creative_ids)} creative IDs from ads resource cache"
            )
        else:
            logger.warning("No creative IDs found from ads resource")

    if is_adcreatives:
        cursor_path = None

    effective_lag = dlt_utils.get_effective_lag(
        resource_name=name, cursor_path=cursor_path, base_lag=lag, pipeline=pipeline
    )
    start_dt = convert_date_string_to_datetime(initial_value)
    end_dt = convert_date_string_to_datetime(end_value)

    if cursor_path and not is_adcreatives:

        @dlt.resource(
            name=name,
            table_name=table_name,
            primary_key=primary_key,
            columns=columns,
            write_disposition=write_disp,
        )
        def asset_resource(
            updated_at=dlt.sources.incremental(
                cursor_path,
                initial_value=start_dt,
                end_value=end_dt,
                lag=effective_lag,
                last_value_func=max,
                on_cursor_value_missing="include",
            ),
        ):
            since = (
                updated_at.last_value.strftime("%Y-%m-%d")
                if updated_at.last_value
                else start_dt.strftime("%Y-%m-%d")
            )
            until = end_dt.strftime("%Y-%m-%d") if end_dt else None

            logger.info(f"📅 {name}: {since} to {until or 'now'}")

            if "campaigns" in name:
                records = client.get_campaigns(since, fields, until_date=until)
            elif "adsets" in name:
                records = client.get_adsets(since, fields, until_date=until)
            elif "ads" in name:
                records = client.get_ads(since, fields, until_date=until)
            else:
                records = []

            count = 0
            for item in records:
                yield item
                count += 1

            logger.info(f"📊 {name}: {count} records")

            if count == 0 and not end_dt:
                dlt_utils.move_incremental_cursor_forward(
                    cursor_path=cursor_path,
                    forward_value=convert_date_string_to_datetime(since),
                    is_backfill=is_backfill,
                )

    else:

        @dlt.resource(
            name=name,
            table_name=table_name,
            primary_key=primary_key,
            columns=columns,
            write_disposition=write_disp,
        )
        def asset_resource():
            if is_adcreatives:
                if not adcreatives_creative_ids:
                    logger.warning(
                        "No creative IDs available, skipping fetch to avoid rate limits"
                    )
                    return

                logger.info(f"Fetching {len(adcreatives_creative_ids)} ad creatives")
                for batch in client.get_adcreatives_by_ids(
                    adcreatives_creative_ids, fields
                ):
                    yield from batch

    transformed = asset_resource.add_map(
        lambda r: dlt_utils.transform_record(r, columns), insert_at=1
    )
    return dlt_utils.apply_partition_to_resource(transformed, partition_config, name)
