import datetime
import io
import json
import logging
from json import JSONDecodeError

from discord import PartialEmoji
from discord.ext import tasks
from typing import Literal

import discord
from redbot.core import commands, app_commands

from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter


from pastures_integration import embed_helpers, config_helper

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
            "servers" : [],
            "whitelisting_role": "",
            "whitelisting_channel": "",
            "logging_channel": ""
        }

        self.config.register_guild(**default_guild_config)
        self.update_loop.start()

        log.info("Pastures Integration Loaded!")

    def __unload(self):
        # Stop the loop after unload!
        self.update_loop.stop()

    def cog_unload(self):
        self.__unload()

    @tasks.loop(minutes=1)
    async def update_loop(self):
        """ Main persistent notification update loop! """

        await self.bot.wait_until_ready()

        async for guild in AsyncIter(self.bot.guilds):
            guild = self.bot.get_guild(guild.id)
            guild_config = self.config.guild_from_id(guild.id)

            servers = await guild_config.servers()
            changed = False

            for server_config in servers:
                # Get the server information for RCON
                ip = server_config["ip"]
                key = server_config["key"]

                # Get the embed information
                embed = await embed_helpers.online_player_status(server_config, ip, key,
                                                                 "_This message updates every minute!  ⌚_")

                # Get the stored channel and message id
                channel_id = server_config["config"]["embed"]["channel_id"]
                message_id = server_config["config"]["embed"]["message_id"]

                try:
                    channel = guild.get_channel(channel_id)
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)

                except (discord.errors.NotFound, AttributeError):
                    log.warning("Message and/or channel has been deleted. Clearing stored id's!")

                    server_config["config"]["embed"]["channel_id"] = 0
                    server_config["config"]["embed"]["message_id"] = 0
                    changed = True

                except discord.HTTPException as HttpErr:
                    log.error("Error editing message: ", HttpErr)

            if changed:
                log.info("Saving changes to server config!")
                await guild_config.servers.set(servers)

    servers = app_commands.Group(name="server",description="Server management commands",
                                         guild_only=True)


    async def server_autocomplete(self, interaction: discord.Interaction, current: str):
        servers = await self.config.guild(interaction.guild).servers()
        return [
            discord.app_commands.Choice(name=server["name"], value=server["name"])
            for server in servers
            if current.lower() in server["name"].lower()
        ]
    @app_commands.guild_only()
    @app_commands.describe(server="The name of the server you want to add.",
                           ip="The IP of the server you want to add.",
                           key="The RCON key for the server you want to add.",
                           config="A JSON file with the server configuration.")
    @servers.command(name="add", description="Add a server to the bot!")
    async def server_add(self, interaction: discord.Interaction, server: str, ip: str, key: str, config: discord.Attachment = None):
        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        if config is not None:
            if "application/json" in config.content_type:
                try:
                    # Save the config to the server object
                    file_object = await config.read()
                    settings = json.loads(file_object)

                    # Parse the config file
                    config_helper.ServerConfig.from_json(settings)

                    # Save the config to the server object
                    json_string = {
                        "name": server,
                        "ip": ip,
                        "key": key,
                        "config": settings
                    }

                except config_helper.ConfigError as err:
                    await interaction.response.send_message(f"Error parsing config file: {err}")
                    return

            else:
                await interaction.response.send_message("The attached file is not a `.json` file!")
                return

        else:
            json_string ={
                "name": server,
                "ip": ip,
                "key": key,
                "config": config_helper.ServerConfig.default_config().to_dict()
            }

        if servers is None:
            servers = [json_string]
            await guild_config.servers.set(servers)
            await interaction.response.send_message(f"Server {server} added!")

        else :
            for s in servers:
                if s["name"] == server:
                    await interaction.response.send_message(f"Server {server} already exists!")
                    return

            servers.append(json_string)
            await guild_config.servers.set(servers)
            await interaction.response.send_message(f"Server {server} added!")
    @app_commands.guild_only()
    @servers.command(name="list", description="List all servers added to the bot!")
    async def server_list(self, interaction: discord.Interaction):
        """ List all servers added to the bot!
        """
        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        log.info(f"Servers: {servers}")

        if len(servers) == 0:
            await interaction.response.send_message("No servers added!")
            return

        server_list = ""
        for s in servers:
            server_list += f"`{s['name']}` - `{s['ip']}` \n"

        await interaction.response.send_message(f"## Servers: \n {server_list}")

    @app_commands.guild_only()
    @app_commands.autocomplete(server_name=server_autocomplete)
    @app_commands.describe(server_name="The name of the server you want to edit.",
                           ip="The changed IP (Optional)",
                           key="The changed RCON key (Optional)",
                           config="The changed server configuration (Optional)")
    @servers.command(name="edit", description="Edit a saved servers configuration!")
    async def server_edit(self, interaction: discord.Interaction, server_name: str, ip: str = None, key: str = None, config: discord.Attachment = None):
        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        for s in servers:
            if s["name"] == server_name:
                if ip is not None:
                    s["ip"] = ip
                if key is not None:
                    s["key"] = key
                if config is not None:
                    try:
                        # Save the config to the server object
                        file_object = await config.read()
                        settings = json.loads(file_object)

                        # Parse the config file
                        config_helper.ServerConfig.from_json(settings)

                        # Save the config to the server object
                        s["config"] = settings

                    except config_helper.ConfigError as err:
                        await interaction.response.send_message(f"Error parsing config file: {err}")
                        return

            else:
                await interaction.response.send_message(f"Server `{server_name}` not found!")
                return

        await guild_config.servers.set(servers)
        await interaction.response.send_message("Server edited!")

    @app_commands.guild_only()
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.describe(server="The server you want to show the configuration for.")
    @servers.command(name="show", description="Show a servers configuration!")
    async def server_show(self, interaction: discord.Interaction, server: str = None):

        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        if server is None:
            file = io.BytesIO(config_helper.ServerConfig.default_config().to_json().encode('UTF-8'))
            await interaction.response.send_message("This is the default server configuration!\n"
                                                    "Edit this file and re-upload it to add a new server!",
                                                    file=discord.File(file, filename="server_default.json"))
            return

        else:
            for s in servers:
                if s["name"] == server:
                    # Convert the config to a file-like object
                    json_payload = io.BytesIO(json.dumps(s["config"], indent=4).encode('UTF-8'))
                    # File name is the server name, but lowercased and with spaces replaced with underscores
                    filename = f"{server.lower().replace(' ','_')}_config.json"

                    await interaction.response.send_message(f"Server configuration for `{server}` attached!\n"
                                                            f"**Edit this file and re-upload it to edit the server!**",
                                                            file=discord.File(json_payload, filename=filename))
                    return

            await interaction.response.send_message(f"Server `{server}` not found!")

    @app_commands.guild_only()
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.describe(server="The server you want to set the one click whitelisting emote for",
                           emote="The emote you want to use for one-click reaction whitelisting")
    @servers.command(name="set_emote", description="Set the emote for one-click whitelisting!")
    async def server_set_emote(self, interaction: discord.Interaction, server: str, emote: str):
        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        if PartialEmoji.from_str(emote) is None:
            await interaction.response.send_message("Invalid emote!")
            return

        for s in servers:
            if s["name"] == server:
                s["config"]["one_click_emoji"] = emote

        await guild_config.servers.set(servers)
        await interaction.response.send_message(f"Emote for {server} set to {emote}")

    @app_commands.guild_only()
    @app_commands.describe(role="The role a user needs to have to use one-click whitelisting")
    @servers.command(name="set_role", description="Set the role for one-click whitelisting!")
    async def server_set_role(self, interaction: discord.Interaction, role: discord.Role = None):
        guild_config = self.config.guild(interaction.guild)

        if role is None:
            role_id =  await guild_config.whitelisting_role()
            if role_id is None:
                await interaction.response.send_message("No role set for one-click whitelisting!")
                return
            else:
                role = interaction.guild.get_role(role_id)
                await interaction.response.send_message(f"Role for one-click whitelisting is set to: {role.mention}!",
                                                        allowed_mentions=discord.AllowedMentions.none())
                return
        await guild_config.whitelisting_role.set(role.id)
        await interaction.response.send_message(f"One click whitelisting is available to everyone "
                                                f"with the {role.mention} role!",
                                                allowed_mentions=discord.AllowedMentions.none())

    @app_commands.guild_only()
    @app_commands.describe(channel="The channel to listen in for one-click whitelisting events")
    @servers.command(name="set_channel", description="Set the channel for one-click whitelisting!")
    async def server_set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        guild_config = self.config.guild(interaction.guild)

        if channel is None:
            channel_id = guild_config.whitelisting_channel()
            if channel_id is None:
                await interaction.response.send_message("No channel set for one-click whitelisting!")
                return
            else:
                channel = interaction.guild.get_channel(channel_id)
                await interaction.response.send_message(f"Channel for one-click whitelisting is set to: {channel.mention}!",
                                                        allowed_mentions=discord.AllowedMentions.none())
                return

        await guild_config.whitelisting_channel.set(channel.id)
        await interaction.response.send_message(f"One click whitelisting is available in {channel.mention}!",
                                                allowed_mentions=discord.AllowedMentions.none())

    @app_commands.guild_only()
    @app_commands.describe(channel="The channel to send one click whitelisting events to")
    @servers.command(name="set_logging", description="Set the channel for logging!")
    async def server_set_logging(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        guild_config = self.config.guild(interaction.guild)

        if channel is None:
            channel_id = guild_config.logging_channel()
            if channel_id is None:
                await interaction.response.send_message("No logging channel set!")
                return
            else:
                channel = interaction.guild.get_channel(channel_id)
                await interaction.response.send_message(f"Logging channel is set to: {channel.mention}!",
                                                        allowed_mentions=discord.AllowedMentions.none())
                return

        await guild_config.logging_channel.set(channel.id)
        await interaction.response.send_message(f"Logging is set to {channel.mention}!",
                                                allowed_mentions=discord.AllowedMentions.none())

    @app_commands.guild_only()
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.describe(server="The server you want to set the embed for",
                           channel="The channel to send the embed to")
    @servers.command(name="embed", description="Set the embed for a server!")
    async def server_embed(self, interaction: discord.Interaction, server: str, channel: discord.TextChannel):
        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        for s in servers:
            if s["name"] == server:
                ip = s["ip"]
                key = s["key"]

                embed = await embed_helpers.online_player_status(s, ip, key, "_Please wait..._")

                try:
                    message = await channel.send(embed=embed)
                    s["config"]["embed"]["channel_id"] = channel.id
                    s["config"]["embed"]["message_id"] = message.id
                    await guild_config.servers.set(servers)

                    await interaction.response.send_message(f"Embed sent in {channel.mention}!\n"
                                                            f"It should update every minute!")

                except discord.HTTPException as HttpErr:
                    log.error("Error sending message: ", HttpErr)
                    await interaction.response.send_message(f"Error sending message in {channel.mention}!")
                    return


    @app_commands.guild_only()
    @app_commands.describe(server="The server to remove")
    @app_commands.autocomplete(server=server_autocomplete)
    @servers.command(name="remove", description="Remove a server from the bot!")
    async def server_remove(self, interaction: discord.Interaction, server: str):
        """ Remove a server from the bot!

        **server** - The server name
        """
        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        for s in servers:
            if s["name"] == server:
                servers.remove(s)

        await guild_config.servers.set(servers)

        await interaction.response.send_message("Server removed!")

    @app_commands.guild_only()
    @app_commands.autocomplete(server_name=server_autocomplete)
    @app_commands.describe(server_name="The name of the server you want to ping")
    @app_commands.command(name="ping", description="Ping the server and check for command execution times!")
    async def ping(self, interaction: discord.Interaction, server_name: str):
        """Ping the server and check for command execution times!"""

        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        for s in servers:
            if s["name"] == server_name:
                ip = s["ip"]
                key = s["key"]

                # Defer the response - The ping can take a while!
                await interaction.response.defer()

                ping_embed = await embed_helpers.ping_embed(server_name, ip, key)

                # We got the response, send it!
                await interaction.followup.send(embed=ping_embed)

                return

        await interaction.response.send_message(f"Server `{server_name}` not found!")

    @app_commands.guild_only()
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.describe(server="The server you want to show the player count for.")
    @app_commands.command(name="players", description="Show a list of the currently online players")
    async def players(self, interaction: discord.Interaction, server: str):
        """Show a list of the currently online players"""
        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        for s in servers:
            if s["name"] == server:
                embed = await embed_helpers.online_player_status(s, s["ip"], s["key"],
                                                                 "_This message will not update._")
                await interaction.response.send_message(embed=embed)
                return

        await interaction.response.send_message(f"Server `{server}` not found!")


    whitelist = app_commands.Group(name="whitelist",
                                         description="Add or remove players from the server whitelists",
                                         guild_only=True)

    @app_commands.guild_only()
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.describe(server="The server to add the player to",
                            player="The name of the player you wish to add to the whitelist")
    @whitelist.command(name="add", description="Add a player to the whitelist")
    async def whitelist_add(self, interaction: discord.Interaction, server: str, player: str):

        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        for s in servers:
            if s["name"] == server:
                ip = s["ip"]
                key = s["key"]
                embed = await embed_helpers.whitelist_add(ip, key, player, server)
                await interaction.response.send_message(embed=embed)
                return
        else:
            await interaction.response.send_message(f"Server `{server}` not found!")

    @app_commands.guild_only()
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.describe(server="The server to remove the player from",
                            player="The name of the player you wish to remove from the whitelist")
    @whitelist.command(name="remove", description="Remove a player from the whitelist")
    async def whitelist_remove(self, interaction: discord.Interaction, server: str, player: str):

        guild_config = self.config.guild(interaction.guild)
        servers = await guild_config.servers()

        for s in servers:
            if s["name"] == server:
                ip = s["ip"]
                key = s["key"]

                embed = await embed_helpers.whitelist_remove(ip, key, player, server)
                await interaction.response.send_message(embed=embed)
                return

        else:
            await interaction.response.send_message(f"Server `{server}` not found!")

    @app_commands.guild_only()
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.describe(server="The server to list the whitelist for")
    @whitelist.command(name="list", description="List the current whitelist")
    async def whitelist_list(self, interaction: discord.Interaction, server: str):
        guild_config = self.config.guild(interaction.guild)

        servers = await guild_config.servers()

        for s in servers:
            if s["name"] == server:
                ip = s["ip"]
                key = s["key"]
                color = s["config"]["embed"]["color"]
                embed = await embed_helpers.whitelist_list(server, ip, key, color)
                await interaction.response.send_message(embed=embed)
                return

        else:
            await interaction.response.send_message(f"Server `{server}` not found!")


    # Single click whitelistling reaction listener

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        guild_config = self.config.guild(guild)

        # Initial sanity checks

        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id != await guild_config.whitelisting_channel():
            return

        if await guild_config.whitelisting_role() is None:
            return

        role = guild.get_role(await guild_config.whitelisting_role())
        if role not in guild.get_member(payload.user_id).roles:
            return

        servers = await guild_config.servers()

        # Check if the reaction is a whitelisting reaction for one of the servers
        for s in servers:
            if s["config"]["one_click_whitelist"]:
                # The server has one-click whitelisting enabled
                if str(payload.emoji) == s["config"]["one_click_emoji"]:
                    # Emoji matches the one-click emoji, lets do this!
                    ip = s["ip"]
                    key = s["key"]

                    channel = guild.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)

                    player = message.content.split(" ")[0]

                    try:
                        log_channel = guild.get_channel(await guild_config.logging_channel())
                        embed = await embed_helpers.whitelist_add(ip, key, player, s["name"], guild.get_member(payload.user_id))
                        await log_channel.send(embed=embed)
                    except discord.HTTPException as HttpErr:
                        log.error("Error sending message: ", HttpErr)