import discord

from timezones import time_convert

version = "1.0.0"


class TimeEmbed(discord.Embed):
    def version_footer(self):
        return self.set_footer(text=f"Medsbot Timezones v{version}")


def greeting_calculator(hour: int) -> str:
    if 5 <= hour < 12:
        return "☕  Good morning!"
    elif 12 <= hour < 18:
        return "☀️  Good afternoon!"
    elif 18 <= hour < 22:
        return "🌇  Good evening!"
    else:
        return "🌛  Good night!"


def color_calculator(hour: int) -> int:
    if 5 <= hour < 8:
        return 0x8D5273
    elif 8 <= hour < 12:
        return 0xC3727C
    elif 12 <= hour < 18:
        return 0xE8817F
    elif 18 <= hour < 24:
        return 0x5A336E
    else:
        return 0x311f62


async def utc_time(timezone) -> str:
    utc_offset = await time_convert.timezone_to_utc(timezone)
    dst = await time_convert.dst_status(timezone)
    return f"(UTC{utc_offset}{dst})"


async def time_embed(timezone: str, location="") -> TimeEmbed:
    time = await time_convert.get_time_object(timezone)
    utc_offset = await utc_time(timezone)

    if location == "":
        description = (f"The current time in `{timezone} {utc_offset}` is:\n"
                       f"# {time.strftime('%A - %H:%M')}\n"
                       )
    else:
        description = (f"In **{location}** \n"
                       f"the timezone is `{timezone} {utc_offset}`\n"
                       f"The current time is:\n"
                       f"# {time.strftime('%A - %H:%M')}\n"
                       )

    embed = (TimeEmbed(
        title=greeting_calculator(time.hour),
        description=description,
        colour=color_calculator(time.hour))
        .version_footer())
    return embed


async def time_for_person(person: discord.Member, timezone: str) -> TimeEmbed:
    time = await time_convert.get_time_object(timezone)

    description = (f"The current time for {person.mention} `{await utc_time(timezone)}` is:\n"
                   f"# {time.strftime('%A - %H:%M')}\n"
                   )

    embed = (TimeEmbed(
        title=greeting_calculator(time.hour),
        description=description,
        colour=color_calculator(time.hour))
        .version_footer())
    return embed
