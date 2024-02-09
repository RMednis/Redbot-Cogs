from datetime import datetime, timedelta

import geopy
import zoneinfo
import logging

from geopy.geocoders import GeoNames
from geopy.adapters import AioHTTPAdapter

log = logging.getLogger("red.mednis-cogs.timezones")


async def city_to_timezone(city: str, apikey: str) -> tuple[str, str]:
    if apikey == "":
        raise ValueError("No API key found")

    try:
        async with GeoNames(
                username=apikey,
                adapter_factory=AioHTTPAdapter,
        ) as geolocator:
            location = await geolocator.geocode(query=city, exactly_one=True)

            if location is None:
                raise ValueError("No location found")

            timezone = await geolocator.reverse_timezone(query=location.point)
            return str(timezone), str(location)

    except geopy.exc.GeocoderTimedOut:
        log.error("Geocoder Timed Out")
        raise ValueError("Geocoder Timed Out")

    except geopy.exc.GeocoderAuthenticationFailure:
        log.error("Geocoder Authentication Failure")
        raise ValueError("Geocoder Authentication Failure")


async def check_timezone(iana_name: str) -> bool:
    if iana_name in zoneinfo.available_timezones():
        return True
    else:
        return False


async def get_time_object(iana_name: str) -> datetime:
    dt = datetime.now(zoneinfo.ZoneInfo(iana_name))
    return dt


async def get_time_str(iana_name: str) -> str:
    dt = await get_time_object(iana_name)
    time = dt.strftime("%A %d %B %Y %I:%M")
    return time


async def timezone_to_utc(iana_name: str) -> str:
    # Create a timezone object
    timezone = zoneinfo.ZoneInfo(iana_name)

    current_time_in_timezone = datetime.now(timezone)

    # Format the time to get the UTC offset
    utc_offset = current_time_in_timezone.strftime('%z')
    utc_offset = utc_offset[:3] + ":" + utc_offset[3:]

    return utc_offset


async def dst_status(iana_name: str) -> str:
    timezone = zoneinfo.ZoneInfo(iana_name)
    dt = datetime.now(timezone)
    if timezone.dst(dt):
        return " 🔂"
    else:
        return ""


async def timezone_difference(iana_name1: str, iana_name2: str) -> str:
    utc_now = datetime.now(zoneinfo.ZoneInfo("UTC"))

    datetime1 = utc_now.astimezone(zoneinfo.ZoneInfo(iana_name1))
    datetime2 = utc_now.astimezone(zoneinfo.ZoneInfo(iana_name2))

    time_difference = datetime2 - datetime1

    # Format the time difference
    hours, remainder = divmod(abs(time_difference).seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    # Figure out if the time difference is positive or negative using total_seconds()
    if time_difference.total_seconds() < 0:
        return f"is `{hours}:{minutes}` behind"
    elif time_difference.total_seconds() > 0:
        return f"is `{hours}:{minutes}` ahead of"
    else:
        return "is the same time as"

