import datetime
import logging


from discord.ext import tasks
from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter

from pastures_integration import embed_helpers

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

        default_guild_config = {
            # Data for the player/server message
            "persistent_channel": "",
            "persistent_message": "",

            # Data for the whitelisting functions
            "whitelisted_role": "",
            "moderation_role": "",
            "logging_channel": "",
            "whitelist_channel": "",

            # Data for Rcon
            "host": "",
            "apikey": ""
        }

        self.config.register_guild(**default_guild_config)
        self.update_loop.start()

        log.info("MedsNET Pastures Integration Loaded!")

    def __unload(self):
        # Stop the loop after unload!
        self.update_loop.stop()

    def cog_unload(self):
        self.__unload()

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
                    embed = await embed_helpers.online_players(ip, key, "_This message updates every minute! :watch:_")
                    try:
                        channel = guild.get_channel(channel_id)
                        message = await channel.fetch_message(message_id)
                        await message.edit(embed=embed)
                        log.info("Updated embed!")

                    except (discord.errors.NotFound, AttributeError) as err:
                        log.warning("Message and/or channel has been deleted. Clearing stored id's!")
                        log.warning("Error: ", err)
                        await guild_config.persistent_channel.set("")
                        await guild_config.persistent_message.set("")

                    except discord.HTTPException as HttpErr:
                        log.error("Error editing message: ", HttpErr)

    @commands.group(autohelp=True, aliases=["pst"])
    @commands.admin()
    async def pastures(self, ctx):
        """Discord integration for greener pastures

        Automagic whitelisting, currently online player notifications, and more! (tm)

        **Version:** `1.1.0`
        _Made with <3 by Mednis!_
        """

    @pastures.group(autohelp=True, aliases=["cfg"])
    @commands.admin()
    async def config(self, ctx):
        """
        Configure pastures integration settings!

        """

    @config.command(name="creds")
    @commands.guildowner()
    async def creds(self, ctx, address, key):
        """Server Connection Credentials
        _100% Mednis Only Zone!_

        **address** - Server Address
        **key** - Server API Key
        """

        guild_config = self.config.guild(ctx.guild)
        await guild_config.host.set(address)
        await guild_config.apikey.set(key)

        await ctx.message.delete()  # Yeet the message for safety!
        await ctx.send("**Credentials have been saved!**")

    @config.group(autohelp=True, aliases=["emb"])
    @commands.admin()
    async def embed(self, ctx):
        """
        Configure persistent embed settings!

        """

    @embed.command(name="add")
    @commands.admin()
    async def embed_add(self, ctx, channel_input: discord.TextChannel):
        """Add a persistant notification
        **channel** - The channel where the notification should be posted!
        """
        guild_config = self.config.guild(ctx.guild)
        await self.embed_remove(ctx, False)

        # Placeholder message!
        embed = embed_helpers.customEmbed(title="Greener Pastures Server Status",
                                          description=f":orange_circle: Please wait while we gather server info!",
                                          timestamp=datetime.datetime.utcnow(), colour=0x7BC950
                                          ).pastures_footer().pastures_thumbnail()

        # Post the placeholder!
        message = await channel_input.send(embed=embed)

        # Set the new location!
        await guild_config.persistent_channel.set(channel_input.id)
        await guild_config.persistent_message.set(message.id)

    @embed.command(name="remove")
    @commands.admin()
    async def embed_remove(self, ctx, msg=True):
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
                except (discord.errors.NotFound, AttributeError):
                    await ctx.send("**Persistent message or channel allready deleted!**")

                await guild_config.persistent_message.set("")
            await guild_config.persistent_channel.set("")

        if msg:
            await ctx.send("**Persistent message removed!**")

    @pastures.command(name="players")
    @commands.admin_or_permissions(manage_guild=True)
    async def players(self, ctx):
        """Show a list of the currently online players"""
        guild_config = self.config.guild(ctx.guild)
        ip = await guild_config.host()
        key = await guild_config.apikey()
        embed = await embed_helpers.online_players(ip, key, "_This message will not update!_")
        await ctx.send(embed=embed)

    @config.group(name="whitelist", autohelp=True, aliases=["white"])
    @commands.admin()
    async def conf_whitelist(self, ctx):
        """Whitelist Settings"""

    @conf_whitelist.command(name="role")
    @commands.guildowner()
    async def whitelist_role(self, ctx, role: discord.Role):
        """Select which role has permission to whitelist people!"""
        guild_config = self.config.guild(ctx.guild)
        await guild_config.moderation_role.set(role.id)
        await ctx.send(f"**Only people who are mods and have the `{role.name}` role will be able to whitelist!**")

    @pastures.group(name="whitelist", autohelp=True, aliases=["white", "allow", "allowlist"])
    @commands.admin()
    async def whitelist(self, ctx):
        """Whitelist players on the server"""

    @whitelist.command(name="add")
    @commands.admin()
    async def add(self, ctx, player_name):
        """ Add a player to the whitelist

        **player_name** - The player name to be **added** to the whitelist!
        """
        guild_config = self.config.guild(ctx.guild)
        ip = await guild_config.host()
        key = await guild_config.apikey()
        role = ctx.guild.get_role(await guild_config.moderation_role())

        if role in ctx.author.roles:
            embed = await embed_helpers.whitelist_add(ip, key, player_name)
            await ctx.send(embed=embed, delete_after=10)

    @whitelist.command(name="remove")
    @commands.admin()
    async def remove(self, ctx, player_name):
        """ Remove a player from the whitelist

        **player_name** - The player name to be **removed** from the whitelist!
        """
        guild_config = self.config.guild(ctx.guild)
        ip = await guild_config.host()
        key = await guild_config.apikey()
        role = ctx.guild.get_role(await guild_config.moderation_role())

        if role in ctx.author.roles:
            embed = await embed_helpers.whitelist_remove(ip, key, player_name)
            await ctx.send(embed=embed, delete_after=10)

    @whitelist.command(name="list")
    @commands.admin()
    async def list(self, ctx):
        """ List the current whitelist
        """
        guild_config = self.config.guild(ctx.guild)
        ip = await guild_config.host()
        key = await guild_config.apikey()
        role_id = await guild_config.moderation_role()
        role = ctx.guild.get_role(role_id)

        if role in ctx.author.roles:
            embed = await embed_helpers.whitelist_list(ip, key)
            await ctx.send(embed=embed)


