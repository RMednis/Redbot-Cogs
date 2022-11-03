import datetime
import io
import json
import logging
from json import JSONDecodeError

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

            # Embed customization
            "embed_colour": 0x7BC950,
            "embed_image": "https://file.mednis.network/static_assets/main-logo-mini.png",
            "embed_title": "Greener Pastures Server Status",
            "embed_strings": ["building", "exploring", "vibing", "committing arson", "bartering", "singing to ABBA",
                              "online"],

            # One Click Whitelisting
            "reaction_channel": "",
            "reaction_emote": "",
            "reaction_embed_id": "",

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

            image = await guild_config.embed_image()
            color = await guild_config.embed_colour()
            text = await guild_config.embed_title()
            words = await guild_config.embed_strings()

            if (channel_id != "") and (message_id != ""):

                if (ip != "") and (key != ""):

                    embed = await embed_helpers.online_players(ip, key, "_This message updates every minute! :watch:_",
                                                               color, image, text, words)

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
    @commands.guild_only()
    @commands.mod_or_permissions(manage_guild=True)
    async def pastures(self, ctx):
        """Discord integration for greener pastures

        Automagic whitelisting, currently online player notifications, and more! (tm)

        **Version:** `1.3.0`
        _Made with <3 by Mednis!_
        """

    @pastures.group(autohelp=True, aliases=["cfg"])
    @commands.admin_or_permissions(manage_guild=True)
    async def config(self, ctx):
        """
        Configure pastures integration settings!

        """

    @config.command(name="creds")
    @commands.admin()
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

    @config.command(name="clear")
    @commands.admin()
    async def clear(self, ctx):
        """Clears stored credentials
        """
        guild_config = self.config.guild(ctx.guild)
        await guild_config.host.set("")
        await guild_config.apikey.set("")

        await ctx.message.delete()  # Yeet the message for safety!
        await ctx.send("**Credentials cleared**")

    @config.group(autohelp=True, aliases=["emb"])
    @commands.admin_or_permissions(manage_guild=True)
    async def embed(self, ctx):
        """
        Configure persistent embed settings!

        """

    @embed.command(name="add")
    @commands.admin_or_permissions(manage_guild=True)
    async def embed_add(self, ctx, channel_input: discord.TextChannel):
        """Add a persistant notification
        **channel** - The channel where the notification should be posted!
        """
        guild_config = self.config.guild(ctx.guild)
        await self.embed_remove(ctx, False)

        image = await guild_config.embed_image()
        color = await guild_config.embed_color()

        # Placeholder message!
        embed = embed_helpers.customEmbed(title="Greener Pastures Server Status",
                                          description=f":orange_circle: Please wait while we gather server info!",
                                          timestamp=datetime.datetime.utcnow(), colour=color,
                                          ).pastures_footer().pastures_thumbnail(image=image)

        # Post the placeholder!
        message = await channel_input.send(embed=embed)

        # Set the new location!
        await guild_config.persistent_channel.set(channel_input.id)
        await guild_config.persistent_message.set(message.id)

    @embed.command(name="remove")
    @commands.admin_or_permissions(manage_guild=True)
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
                    await ctx.send("**Persistent message or channel already deleted!**")

                await guild_config.persistent_message.set("")
            await guild_config.persistent_channel.set("")

        if msg:
            await ctx.send("**Persistent message removed!**")

    @embed.command(name="colour")
    @commands.admin_or_permissions(manage_guild=True)
    async def emded_color(self, ctx, colour=""):
        """ Set/Show the embed color!
        """
        guild_config = self.config.guild(ctx.guild)

        if colour == "":
            colour = await guild_config.embed_colour()
            await ctx.send(f"Current embed colour: `{colour}`")
        else:
            try:
                color = colour.lstrip('#')
                await guild_config.embed_colour.set(int(color, 16))
                await ctx.send(f"Embed colour set to: `{colour}`")

            except ValueError:
                await ctx.send(f"Entered value is not a valid HEX colour code!")

    @embed.command(name="image")
    @commands.admin_or_permissions(manage_guild=True)
    async def embed_image(self, ctx, url=""):
        """ Set the thumbnail image for the embed!
        """
        guild_config = self.config.guild(ctx.guild)

        if url == "none":
            url = await guild_config.embed_image()
            await ctx.send(f"Current embed image url: `{url}`")
        else:
            await guild_config.embed_image.set(url)
            await ctx.send(f"Current image set to `{url}`")

    @embed.command(name="title")
    @commands.admin_or_permissions(manage_guild=True)
    async def embed_title(self, ctx, *, title=""):
        """ Set the title for the embed!
        """
        guild_config = self.config.guild(ctx.guild)

        if title == "":
            title = await guild_config.embed_title()
            await ctx.send(f"Current embed title: `{title}`")
        else:
            await guild_config.embed_title.set(title)
            await ctx.send(f"Embed title set to `{title}`")

    @embed.command(name="message")
    @commands.admin_or_permissions(manage_guild=True)
    async def embed_message(self, ctx):
        """ Set the embed player text messages!
        """
        guild_config = self.config.guild(ctx.guild)

        if not ctx.message.attachments:
            messages = await guild_config.embed_strings()

            json_data = {"messages": messages}
            json_test = json.dumps(json_data, indent=4)

            log.info(json_test)
            json_file = io.BytesIO(json_test.encode())

            file = discord.File(fp=json_file, filename="embed_messages.json")

            await ctx.send(file=file, content=f"Current embed player online messages attached to this file! \n"
                           f"*Edit them, then re-run this command with the edited file attached! :D*")
        else:
            log.info(ctx.message.attachments[0].content_type)
            if "application/json" in ctx.message.attachments[0].content_type:
                try:
                    file_object = await ctx.message.attachments[0].read()
                    json_string = json.loads(file_object)

                    await guild_config.embed_strings.set(json_string["messages"])
                    await ctx.send("Embed messages saved! :D")
                except JSONDecodeError:
                    await ctx.send("Error reading file, make sure it's a valid `.json` file with a `messages` array!!")

            else:
                await ctx.send("The attached file is not a `.json` file!")

    @pastures.command(name="ping")
    @commands.admin_or_permissions(manage_guild=True)
    async def ping(self, ctx):
        """Ping the server and check for command execution times!"""

        guild_config = self.config.guild(ctx.guild)
        ip = await guild_config.host()
        key = await guild_config.apikey()

        # Placeholder
        tmp_embed = embed_helpers.customEmbed(title="Server Ping Status",
                                              description="Please wait while I gather all the necessary data!",
                                              timestamp=datetime.datetime.utcnow(), colour=0x202020).pastures_footer()
        message = await ctx.send(embed=tmp_embed)

        # Response
        ping_embed = await embed_helpers.ping_embed(ip, key)
        await message.edit(embed=ping_embed)

    @pastures.command(name="players")
    @commands.admin_or_permissions(manage_guild=True)
    async def players(self, ctx):
        """Show a list of the currently online players"""
        guild_config = self.config.guild(ctx.guild)
        ip = await guild_config.host()
        key = await guild_config.apikey()

        image = await guild_config.embed_image()
        color = await guild_config.embed_colour()
        text = await guild_config.embed_title()
        words = await guild_config.embed_strings()

        # We just use the regular online player embed :)
        embed = await embed_helpers.online_players(ip, key, "_This message will not update!_", color, image, text,
                                                   words)

        await ctx.send(embed=embed)

    @config.group(name="whitelist", autohelp=True, aliases=["white", "allow", "allowlist"])
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

    @conf_whitelist.command(name="log")
    @commands.guildowner()
    async def whitelist_log(self, ctx, channel: discord.TextChannel):
        """Select which channel whitelist changes will be logged to!"""
        guild_config = self.config.guild(ctx.guild)
        await guild_config.logging_channel.set(channel.id)
        await ctx.send(f"**Whitelist changes will be logged to `{channel}`**")

    @pastures.group(name="whitelist", autohelp=True, aliases=["white", "allow", "allowlist"])
    @commands.mod_or_permissions(manage_guild=True)
    async def whitelist(self, ctx):
        """Whitelist players on the server"""

    @whitelist.command(name="add")
    @commands.mod_or_permissions(manage_guild=True)
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
    @commands.mod_or_permissions(manage_guild=True)
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
    @commands.mod_or_permissions(manage_guild=True)
    async def list(self, ctx):
        """ List the current whitelist
        """
        guild_config = self.config.guild(ctx.guild)
        ip = await guild_config.host()
        key = await guild_config.apikey()
        color = await guild_config.embed_colour()
        role_id = await guild_config.moderation_role()
        role = ctx.guild.get_role(role_id)

        if role in ctx.author.roles:
            embed = await embed_helpers.whitelist_list(ip, key, color)
            await ctx.send(embed=embed)
