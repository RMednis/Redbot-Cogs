import asyncio
import datetime
import logging
import random
import time
from typing import Union

import discord

from pastures_integration import minecraft_helpers

log = logging.getLogger("red.mednis-cogs.pastures_integration")

logo = "https://file.mednis.network/static_assets/main-logo-mini.png"


class customEmbed(discord.Embed):
    def pastures_footer(self):
        return self.set_footer(text="GP Logger 1.3.4", icon_url=logo)

    def pastures_thumbnail(self, image=logo):
        return self.set_thumbnail(url=image)

    def embed_caller(self, user: discord.Member):
        self.add_field(name="_Performed by:_", value=user.display_name)
        return


async def error_embed(title: str, error: Union[Exception, str], colour=0xe74c3c):
    if title == "":
        title = "General Error"

    if error == "":
        error = "Something went wrong and didnt return an error message!"

    # If the error contains a newline, split it and format it properly
    if "\n" in str(error):
        text = str(error).split("\n", 1)

        return customEmbed(title=title, description=f":red_circle:  **{text[0]}** \n\n{text[1]}",
                           timestamp=datetime.datetime.utcnow(), colour=colour).pastures_footer()


    # Make a custom embed with the error
    return customEmbed(title=title, description=f":red_circle:  **{error}**",
                       timestamp=datetime.datetime.utcnow(), colour=colour).pastures_footer()


async def ping_embed(ip: str, key: str):
    error = ""
    data = ""

    embed = customEmbed(title="Server Ping Status",
                        description="Server response speed to RCON commands, this is done locally and does not "
                                    "guarantee that the server is reachable from the outside!"
                                    f"\n**Server IP:** `{ip}`",
                        colour=0x7BC950,
                        timestamp=datetime.datetime.utcnow()).pastures_footer()

    try:
        start_time = time.time()
        data = await minecraft_helpers.run_rcon_command(ip, key, "list")
        end_time = time.time()
    except RuntimeError as err:
        error = err
        end_time = time.time()
    except asyncio.TimeoutError:
        error = "Network/Server timeout! (Response took >2 seconds)"
        end_time = time.time()

    time_delta = (datetime.datetime.fromtimestamp(end_time) - datetime.datetime.fromtimestamp(
        start_time)).total_seconds() * 1000

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
                       colour=0x7BC950) \
        .pastures_footer()


# The actual embeds we post in situations!
async def whitelist_list(ip: str, key: str, color):
    try:
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist list")
        players = await minecraft_helpers.whitelisted_players(response)

    except RuntimeError as err:
        return await error_embed("Error!", err)

    description = f"{players['count']} player(s) whitelisted!"

    embed = customEmbed(title="Whitelist",
                        description=description,
                        timestamp=datetime.datetime.utcnow(),
                        colour=color) \
        .pastures_footer()

    player_name_string = ""
    for name in players["names"]:
        player_name_string += f"`{name}`\n"

    embed.add_field(name="Whitelisted players",
                    value=player_name_string)
    return embed


async def whitelist_remove(ip: str, key: str, username: str):
    try:
        username = username.lower()
        name = await minecraft_helpers.check_name(username)
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist remove {name}")
        await minecraft_helpers.whitelist_remove_success(response)

        embed = customEmbed(title=f"Player removed from whitelist!",
                            description=f":green_circle: Successfully removed player `{name}` from the whitelist!",
                            timestamp=datetime.datetime.utcnow(),
                            colour=0x7BC950).pastures_footer()
        return embed

    except RuntimeError as err:

        # If the error needs to be formatted with the username
        if "%s" in str(err):
            return await error_embed("Whitelist Error!", str(err) % f"`{username}`")

        # Else, just return the error
        return await error_embed("Whitelist Error!", err)


async def whitelist_add(ip: str, key: str, username: str):
    try:
        username = username.lower()
        name = await minecraft_helpers.check_name(username)
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist add {name}")

        await minecraft_helpers.whitelist_success(response)

        embed = customEmbed(title="Player Whitelisted!",
                                description=f":green_circle:  Successfully whitelisted player `{name}`",
                                timestamp=datetime.datetime.utcnow(),
                                colour=0x7BC950).pastures_footer()
        return embed

    except RuntimeError as err:
        # If the error needs to be formatted with the username
        if "%s" in str(err):
            return await error_embed("Whitelist Error!", str(err) % f"`{username}`")

        # Else, just return the error
        return await error_embed("Whitelist Error!", err)


async def online_players(ip: str, key: str, message: str, color, image, text: str, words: list[str]):
    try:
        data = await minecraft_helpers.run_rcon_command(ip, key, "list")

    # General catch for any errors that might occur
    except RuntimeError as err:
        return await error_embed("Problem Connecting to server!", err, color)

    # Catch for timeouts
    except asyncio.TimeoutError:
        return await error_embed("Problem Connecting to server!", "Network timeout error!", color)

    players = await minecraft_helpers.player_count(data)

    # The description of the embed, based on the player count and adds a random word from the list
    description = f"{players['current']}/{players['max']} People {random.choice(words)}!"

    embed = customEmbed(title=text,
                        description=description,
                        timestamp=datetime.datetime.utcnow(),
                        colour=color) \
        .pastures_footer() \
        .pastures_thumbnail(image)

    player_name_string = ""
    for name in players["names"]:
        player_name_string += f"`{name}`\n"

    embed.add_field(name="Currently Online:",
                    value=player_name_string + f"\n{message}")

    return embed
