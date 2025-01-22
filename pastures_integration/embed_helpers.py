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
        return self.set_footer(text="GP Logger 2.0.0", icon_url=logo)

    def pastures_thumbnail(self, image=logo):
        return self.set_thumbnail(url=image)

    def embed_caller(self, user: discord.Member):
        self.add_field(name="Performed by:", value=f"**{user.display_name}** - `{user.id}`", inline=False)
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


async def ping_embed(name: str, ip: str, key: str):
    error = ""
    data = ""

    embed = customEmbed(title=f"`{name}` - Ping Status",
                        description="Server response speed to RCON commands, this is done locally and does not "
                                    "guarantee that the server is reachable from the outside!"
                                    f"\n**Internal IP:** `{ip}`",
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


# The actual embeds we post in situations!
async def whitelist_list(server: str, ip: str, key: str, color):
    try:
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist list")
        players = await minecraft_helpers.whitelisted_players(response)

    except RuntimeError as err:
        return await error_embed("Error!", err)

    description = f"{players['count']} player(s) whitelisted!"

    embed = customEmbed(title=f"`{server}` - Whitelist",
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


async def whitelist_remove(ip: str, key: str, username: str, server: str, user: discord.Member = None):
    try:
        username = username.lower()
        name = await minecraft_helpers.check_name(username)
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist remove {name}")
        await minecraft_helpers.whitelist_remove_success(response)

        embed = customEmbed(title=f"`{server}` - Player removed from whitelist!",
                            description=f":green_circle: Successfully removed player `{name}` from the whitelist!",
                            timestamp=datetime.datetime.utcnow(),
                            colour=0x7BC950).pastures_footer()

        if user:
            embed.embed_caller(user)

        return embed

    except RuntimeError as err:

        # If the error needs to be formatted with the username
        if "%s" in str(err):
            return await error_embed(f"{server} - Whitelist Error!", str(err) % f"`{username}`")

        # Else, just return the error
        return await error_embed(f"{server} - Whitelist Error!", err)


async def whitelist_add(ip: str, key: str, username: str, server: str, user: discord.Member= None):
    try:
        username = username.lower()
        name = await minecraft_helpers.check_name(username)
        response = await minecraft_helpers.run_rcon_command(ip, key, f"whitelist add {name}")

        await minecraft_helpers.whitelist_success(response)

        embed = customEmbed(title=f"`{server}` - Player Whitelisted!",
                                description=f":green_circle:  Successfully whitelisted player `{name}`",
                                timestamp=datetime.datetime.utcnow(),
                                colour=0x7BC950).pastures_footer()
        if user:
            embed.embed_caller(user)
        return embed

    except RuntimeError as err:
        # If the error needs to be formatted with the username
        if "%s" in str(err):
            errorembed = await error_embed(f"`{server}` - Whitelist Error!", str(err) % f"`{username}`")
            if user:
                errorembed.embed_caller(user)
            return errorembed

        # Else, just return the error
        errorembed = await error_embed(f"`{server}` - Whitelist Error!", err)
        if user:
            errorembed.embed_caller(user)
        return errorembed

async def online_player_status(config: dict, ip: str, key: str, message: str):
    embed = config["config"]["embed"]
    color = embed["color"]
    image = embed["image"]
    title = embed["title"]
    description = embed["description"]
    show_ip = embed["show_ip"]
    public_ip = embed["public_ip"]
    words = embed["messages"]

    # Get the stored channel and message id
    return await online_players(ip, key, message, color, image, title, description, words, show_ip, public_ip)


async def online_players(ip: str, key: str, message: str, color, image: str, title: str, description: str, words: list[str],
                         show_ip: bool, public_ip: str):
    try:
        data = await minecraft_helpers.run_rcon_command(ip, key, "list")

    # General catch for any errors that might occur
    except RuntimeError as err:
        return await error_embed("Problem Connecting to server!", err, color)

    # Catch for timeouts
    except asyncio.TimeoutError:
        return await error_embed("Problem Connecting to server!", "Network timeout error!", color)

    players = await minecraft_helpers.player_count(data)
    pmax = players["max"]
    pcur = players["current"]
    words = random.choice(words)

    # The description of the embed, based on the player count and adds a random word from the list
    description = str.format(description, pcur=pcur,pmax=pmax, messages=words)

    embed = customEmbed(title=title,
                        description=description,
                        timestamp=datetime.datetime.utcnow(),
                        colour=color) \
        .pastures_footer() \
        .pastures_thumbnail(image)

    player_name_string = ""
    for name in players["names"]:
        player_name_string += f"`{name}`\n"

    if show_ip:
        embed.add_field(name="Address:", value=f"`{public_ip}`", inline=False)

    embed.add_field(name="Currently Online:",
                    value=player_name_string + f"\n{message}")

    return embed

