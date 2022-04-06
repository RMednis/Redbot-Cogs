import datetime
import logging
import random

from discord.ext import tasks
from typing import Literal

import discord
from mcrcon import MCRcon
from mcrcon import MCRconException
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter

from pastures_integration import minecraft_helpers

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("red.mednis-cogs.pastures_integration")


class PasturesIntegration(commands.Cog):
    """
    Custom-made whitelisting and player count integration for Greener Pastures.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=92651437657460736,
            force_registration=True,
        )

        default_config = {
            "persistent_channel": "",
            "persistent_message": "",
            "allowed_users": "",
            "allowed_whitelisters": "",
            "host": "",
            "apikey": ""
        }

        self.config.register_guild(**default_config)
        self.update_loop.start()

        log.info("MedsNET Pastures Integration Loaded!")

    @tasks.loop(minutes=1)
    async def update_loop(self):
        """ Main persistent notification update loop! """

        await self.bot.wait_until_ready()
        log.info("Monitoring started!")

        async for guild in AsyncIter(self.bot.guilds):
            log.info("Updating guild: " + str(guild) + " " + str(guild.id))

            guild = self.bot.get_guild(guild.id)
            guild_config = self.config.guild_from_id(guild.id)

            channel_id = await guild_config.persistent_channel()
            message_id = await guild_config.persistent_message()

            ip = await guild_config.host()
            key = await guild_config.apikey()

            if (channel_id != "") and (message_id != ""):
                if (ip != "") and (key != ""):
                    embed = await self.player_embed(ip, key, "_This message updates every minute! :watch:_")
                    try:
                        channel = guild.get_channel(channel_id)
                        message = await channel.fetch_message(message_id)
                        await message.edit(embed=embed)
                        log.info("Updated embed!")

                    except (discord.errors.NotFound, AttributeError):
                        log.warning("Message and/or channel has been deleted. Clearing stored id's!")
                        await guild_config.persistent_channel.set("")
                        await guild_config.persistent_message.set("")

    @commands.group(autohelp=True, aliases=["pst"])
    @commands.admin()
    async def pastures(self, ctx):
        """Discord integration for greener pastures

        Automagic whitelisting, currently online player notifications, and more! (tm)

        **Version:** `1.1.0`
        _Made with <3 by Mednis!_
        """

    @pastures.command(name="config")
    @commands.guildowner()
    async def config(self, ctx, address, key):
        """Configure general server connection information!

        _100% Mednis Only Zone!_

        **address** - Server Address
        **key** - Server API Key
        """

        guild_config = self.config.guild(ctx.guild)
        await guild_config.host.set(address)
        await guild_config.apikey.set(key)

        await ctx.message.delete()  # Yeet the message for safety!
        await ctx.send("**Credentials have been saved!**")

    @pastures.group(autohelp=True, aliases=["emb"])
    @commands.admin()
    async def embed(self, ctx):
        """Persistent notification settings"""

    @embed.command(name="add")
    @commands.admin()
    async def add(self, ctx, channel_input: discord.TextChannel):
        """Add a persistant notification
        **channel** - The channel where the notification should be posted!
        """
        guild_config = self.config.guild(ctx.guild)
        await self.remove(ctx, False)

        # Placeholder message!
        embed = discord.Embed(title="Greener Pastures Server Status",
                              description=f":orange_circle: Please wait while we gather server info!",
                              timestamp=datetime.datetime.utcnow(), colour=0x7BC950) \
            .set_thumbnail(url="https://file.mednis.network/static_assets/main-logo-mini.png") \
            .set_footer(text="GP Logger 1.0",
                        icon_url="https://file.mednis.network/static_assets/main-logo-mini.png")

        # Post the placeholder!
        message = await channel_input.send(embed=embed)

        # Set the new location!
        await guild_config.persistent_channel.set(channel_input.id)
        await guild_config.persistent_message.set(message.id)

    @embed.command(name="remove")
    @commands.admin()
    async def remove(self, ctx, msg=True):
        """Removes the persistent notification"""
        guild_config = self.config.guild(ctx.guild)
        channel_id = await guild_config.persistent_channel()
        message_id = await guild_config.persistent_message()

        if channel_id != "":
            if message_id != "":
                try:
                    channel = ctx.guild.get_channel(channel_id)
                    message = await channel.fetch_message(message_id)
                    await message.delete()
                except discord.errors.NotFound:
                    if msg:
                        await ctx.send("**Persistent message or channel allready deleted!**")

                await guild_config.persistent_message.set("")
            await guild_config.persistent_channel.set("")

        if msg:
            await ctx.send("**Persistent message removed!**")

    @pastures.command(name="players")
    @commands.admin_or_permissions(manage_guild=True)
    async def players(self, ctx):
        guild_config = self.config.guild(ctx.guild)
        ip = await guild_config.host()
        key = await guild_config.apikey()
        embed = await self.player_embed(ip, key, "_This message will not update!_")
        await ctx.send(embed=embed)

    async def player_embed(self, ip, key, message):
        try:
            data = await self.run_rcon_command(ip, key, "list")
        except RuntimeError as err:
            # Error during connecting via RCon

            embed = discord.Embed(title="Greener Pastures Server Status", description=f":red_circle: **{err}**",
                                  timestamp=datetime.datetime.utcnow(), colour=0x7BC950)
            embed.set_thumbnail(url="https://file.mednis.network/static_assets/main-logo-mini.png")
            embed.set_footer(text="GP Logger 1.0",
                             icon_url="https://file.mednis.network/static_assets/main-logo-mini.png")
            return embed

        player_amount = await minecraft_helpers.player_count(data)
        players = await minecraft_helpers.player_online(data)

        randomwords = ["building", "exploring", "vibing", "commiting arson", "bartering", "singing to ABBA", "online",
                       "cooking", "fighting for their lives", "commiting war crimes", "exploring", "hunting", "baking",
                       "trying not to explode", "sometimes exploding", "dungeon hunting", "flying around the place",
                       "looking at the wildlife", "talking to Humphrey"]

        description = f"{player_amount['current']}/{player_amount['max']} People {random.choice(randomwords)}!"

        embed = discord.Embed(title="Greener Pastures Server Status", description=description,
                              timestamp=datetime.datetime.utcnow(), colour=0x7BC950)
        embed.set_thumbnail(url="https://file.mednis.network/static_assets/main-logo-mini.png")
        embed.set_footer(text="GP Logger 1.0",
                         icon_url="https://file.mednis.network/static_assets/main-logo-mini.png")

        player_name_string = ""
        if int(player_amount['current']) > 0:
            for name in players:
                player_name_string += f"`{name}`\n"
        else:
            player_name_string = "`None`\n"

        embed.add_field(name="Currently Online:",
                        value=player_name_string + f"\n{message}")

        return embed



    async def run_rcon_command(self, ip, key, command):
        try:
            with MCRcon(ip, key) as rcon:
                try:
                    response = rcon.command(command)
                    rcon.disconnect()
                except (ConnectionResetError, ConnectionAbortedError):
                    raise RuntimeError("Error Connecting to server!")
                return response
        except (ConnectionRefusedError, MCRconException):
            raise RuntimeError("Error Connecting to server!")

