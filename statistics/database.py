import logging

from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from collections import defaultdict

log = logging.getLogger("red.mednis-cogs.statistics.database")

client: InfluxDBClientAsync
bucket: str
org: str
write_api: InfluxDBClientAsync.write_api


async def activate_client(address: str, bucket_str: str, token_str: str, org_str: str):
    global client, write_api, bucket, org

    client = InfluxDBClientAsync(url=address, token=token_str, org=org_str)
    write_api = client.write_api()

    bucket = bucket_str
    org = org_str

    await client.ping()


async def write_vc_stats(guild_id: int, channel_id: int, channel_name: str, member_count: int, members: list):
    id_string = ""
    name_string = ""
    for member in members:
        id_string += f"{member.id},"
        name_string += f"{member.name},"

    data_point = (
        Point("voice_channel_stats")
        .tag("guild_id", guild_id)
        .tag("channel_id", channel_id)
        .tag("channel_name", channel_name)
        .field("member_count", member_count)
        .field("member_ids", id_string)
        .field("member_names", name_string)
    )

    try:
        await write_api.write(bucket=bucket, org=org, record=str(data_point))

    except Exception as e:
        log.error(f"Failed to write data point to database: {e}")
        log.error(f"Data point: {data_point}")


async def write_message_stats(message_cache: defaultdict, channel_name_cache: defaultdict):
    data = []

    for guild_id, channels in message_cache.items():

        for channel_id, message_count in channels.items():

            data_point = (
                Point("message_stats")
                .tag("guild_id", guild_id)
                .tag("channel_id", channel_id)
                .field("message_count", message_count)
            )

            if channel_id in channel_name_cache[guild_id]:
                data_point = data_point.tag("channel_name", channel_name_cache[guild_id][channel_id])

            data.append(data_point)

    try:
        await write_api.write(bucket=bucket, org=org, record=data)
    except Exception as e:
        log.error(f"Failed to write data points to database: {e}")
        log.error(f"Data points: {data}")


# Write general data points
async def write_data_point(measurement: str, tag: dict, data: dict):
    data_point = Point(measurement)

    for tag_key, tag_value in tag.items():
        data_point = data_point.tag(tag_key, tag_value)

    for data_key, data_value in data.items():
        data_point = data_point.field(data_key, data_value)

    try:
        await write_api.write(bucket=bucket, org=org, record=str(data_point))
    except Exception as e:
        log.error(f"Failed to write data point: {e}")
        log.error(f"Data point: {data_point}")
