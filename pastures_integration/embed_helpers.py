import datetime
import logging
import random

import discord

from pastures_integration import minecraft_helpers

log = logging.getLogger("red.mednis-cogs.pastures_integration")

logo = "https://file.mednis.network/static_assets/main-logo-mini.png"


class customEmbed(discord.Embed):
    def pastures_footer(self):
        return self.set_footer(text="GP Logger 1.1", icon_url=logo)

    def pastures_thumbnail(self):
        return self.set_thumbnail(url=logo)


async def error_embed(title, error):
    return customEmbed(title=title, description=f":red_circle:  **{error}**",
                       timestamp=datetime.datetime.utcnow(), colour=0x7BC950).pastures_footer()


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
                        description=f":green_circle: Successfully whitelisted player `{name}`",
                        timestamp=datetime.datetime.utcnow(),
                        colour=0x7BC950).pastures_footer()
    return embed


async def online_players(ip, key, message):
    try:
        data = await minecraft_helpers.run_rcon_command(ip, key, "list")
    except RuntimeError as err:
        return await error_embed("Problem Connecting to server!", err)

    players = await minecraft_helpers.player_count(data)

    randomwords = ["building", "exploring", "vibing", "committing arson", "bartering", "singing to ABBA", "online",
                   "cooking", "fighting for their lives", "committing war crimes", "exploring", "hunting", "baking",
                   "trying not to explode", "sometimes exploding", "dungeon hunting", "flying around the place",
                   "looking at the wildlife", "talking to Humphrey"]

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
