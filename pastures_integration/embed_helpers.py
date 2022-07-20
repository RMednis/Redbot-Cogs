import asyncio
import datetime
import logging
import random
import time
import discord

from pastures_integration import minecraft_helpers

from redbot.core.bot import Red

log = logging.getLogger("red.mednis-cogs.pastures_integration")

logo = "https://file.mednis.network/static_assets/main-logo-mini.png"


class customEmbed(discord.Embed):
    def pastures_footer(self):
        return self.set_footer(text="GP Logger 1.3", icon_url=logo)

    def pastures_thumbnail(self):
        return self.set_thumbnail(url=logo)

    def embed_caller(self, user: discord.Member):
        self.add_field(name="_Performed by:_", value=user.display_name)
        return


async def error_embed(title, error):

    if not title:
        title = "Error"

    if not error:
        error = "Connection/Server error! Trying again :D"

    return customEmbed(title=title, description=f":red_circle:  **{error}**",
                       timestamp=datetime.datetime.utcnow(), colour=0x7BC950).pastures_footer()

async def ping_embed(ip, key):
    error = ""
    data = ""

    embed = customEmbed(title="Server Ping Status",
                        description="Server response speed to RCON commands, this is done locally and does not "
                                    "guarantee that the server is reachable from the outside",
                        colour=0x7BC950,
                        timestamp=datetime.datetime.utcnow()).pastures_footer()

    try:
        start_time = time.time()
        data = await minecraft_helpers.run_rcon_command(ip, key, "list")
        end_time = time.time()
    except (RuntimeError, asyncio.TimeoutError) as err:
        error = err
        end_time = time.time()

    time_delta = (datetime.datetime.fromtimestamp(end_time) - datetime.datetime.fromtimestamp(start_time)).total_seconds() * 1000

    if not error:
        embed.add_field(name=f"Server status: ✅", value=f"Ping time **{time_delta} ms**", inline=False)
        embed.add_field(name="Data", value=f"``{data}``")
    else:
        embed.add_field(name="Server status: ❌", value=f"Ping time **{time_delta} ms**")
        embed.add_field(name="Error", value=f"``{error}``")

    return embed

async def reaction_embed():

    return customEmbed(title="Reaction setup!",
                       description="React to this message with the emote(s) you wish to be used for one-click "
                                   "whitelisting!",
                       colour=0x7BC950)\
        .pastures_footer()

# The actual embeds we post in situations!
async def whitelist_list(ip, key):
    try:
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist list")
        players = await minecraft_helpers.whitelisted_players(response)

    except RuntimeError as err:
        return await error_embed("Error!", err)

    description = f"{players['count']} player(s) whitelisted!"

    embed = customEmbed(title="Whitelist",
                        description=description,
                        timestamp=datetime.datetime.utcnow(),
                        colour=0x7BC950) \
        .pastures_footer()

    player_name_string = ""
    for name in players["names"]:
        player_name_string += f"`{name}`\n"

    embed.add_field(name="Whitelisted players",
                    value=player_name_string)
    return embed


async def whitelist_remove(ip, key, username: str):
    try:
        username = username.lower()
        name = await minecraft_helpers.check_name(username)
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist remove {name}")
        if not await minecraft_helpers.whitelist_remove_success(response):
            raise RuntimeError(f"Player `{name}` was not whitelisted!")

    except RuntimeError as err:
        return await error_embed("Whitelist Error!", err)

    embed = customEmbed(title=f"Player removed from whitelist!",
                        description=f":green_circle: Successfully removed player `{name}` from the whitelist!",
                        timestamp=datetime.datetime.utcnow(),
                        colour=0x7BC950).pastures_footer()
    return embed


async def whitelist_add(ip, key, username: str):
    try:
        username = username.lower()
        name = await minecraft_helpers.check_name(username)
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist add {name}")
        if not await minecraft_helpers.whitelist_success(response):
            raise RuntimeError(f"Player `{name}` already whitelisted!")

    except RuntimeError as err:
        return await error_embed("Whitelist Error!", err)

    embed = customEmbed(title="Player Whitelisted!",
                        description=f":green_circle:  Successfully whitelisted player `{name}`",
                        timestamp=datetime.datetime.utcnow(),
                        colour=0x7BC950).pastures_footer()
    return embed


async def online_players(ip, key, message):
    try:
        data = await minecraft_helpers.run_rcon_command(ip, key, "list")
    except (RuntimeError, asyncio.TimeoutError) as err:
        return await error_embed("Problem Connecting to server!", err)

    players = await minecraft_helpers.player_count(data)

    randomwords = ["building", "exploring", "vibing", "committing arson", "bartering", "singing to ABBA", "online",
                   "cooking", "fighting for their lives", "committing war crimes", "exploring", "hunting", "baking",
                   "trying not to explode", "sometimes exploding", "dungeon hunting", "flying around the place",
                   "talking to Humphrey", "hiding from Moth", "bowing down to King", "going kablooey",
                   "building a city", "exploring the end", "running from Samus", "trading with Gen", "farming with Luke"]

    description = f"{players['current']}/{players['max']} People {random.choice(randomwords)}!"

    embed = customEmbed(title="Greener Pastures Server Status",
                        description=description,
                        timestamp=datetime.datetime.utcnow(),
                        colour=0x7BC950) \
        .pastures_footer() \
        .pastures_thumbnail()

    player_name_string = ""
    for name in players["names"]:
        player_name_string += f"`{name}`\n"

    embed.add_field(name="Currently Online:",
                    value=player_name_string + f"\n{message}")

    return embed
