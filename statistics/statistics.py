import logging
from datetime import datetime
from typing import Literal

import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from statistics import database
from _collections import defaultdict

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]
log = logging.getLogger("red.mednis-cogs.statistics")


class Statistics(commands.Cog):
    message_stats_cache = defaultdict(lambda: defaultdict(int))
    channel_name_cache = defaultdict(lambda: defaultdict(str))

    """
    A cog for pulling server and bot statistics into influx.
    """

    def __init__(self, bot: Red) -> None:

        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=92651437657460736,
            force_registration=True,
        )

        default_bot = {
            "address": None,
            "bucket": None,
            "token": None,
            "org": None,
            "log_vc_stats": False,
            "log_message_stats": False,
            "log_bot_stats": True,
            "log_external_stats": True
        }

        self.log_vc_stats = None
        self.log_message_stats = None
        self.log_bot_stats = None
        self.log_external_stats = None

        self.config.register_global(**default_bot)

    def cog_load(self) -> None:
        log.info("Statistics cog loaded")

        # Load the config values locally
        self.bot.loop.create_task(self.load_config())

        # Start the statistics gathering loop
        self.statistics_gather_loop.start()

    def cog_unload(self) -> None:
        self.statistics_gather_loop.cancel()

    async def load_config(self):
        # Load the config values into memory
        # This is done on cog load and when the config is updated

        self.log_vc_stats = await self.config.log_vc_stats()
        self.log_message_stats = await self.config.log_message_stats()
        self.log_bot_stats = await self.config.log_bot_stats()
        self.log_external_stats = await self.config.log_external_stats()

    async def temp_disable_logging(self):
        # Disable the statistics gathering loop
        # Used when the database is not set or the database connection fails
        # This will prevent the bot from spamming the logs with errors

        self.statistics_gather_loop.cancel()
        self.log_vc_stats = False
        self.log_message_stats = False
        self.log_bot_stats = False
        self.log_external_stats = False


    @tasks.loop(seconds=30, reconnect=True)
    async def statistics_gather_loop(self):
        # Gather statistics
        await self.update_bot_stats()
        await self.update_all_vc_stats()
        await self.update_all_message_stats()

        pass

    @statistics_gather_loop.before_loop
    async def before_statistics_gather_loop(self):
        log.info("Waiting for bot to be ready...")

        if await self.config.address() is None:
            log.error("❌ No statistics database address set. "
                      "Please set one using the set_statistics_db command then restart.")
            await self.temp_disable_logging()
            return

        try:
            await database.activate_client(await self.config.address(), await self.config.bucket(),
                                           await self.config.token(), await self.config.org())
        except Exception as e:
            log.error(f"❌ Failed to connect to statistics database: {e}"
                      " Statistics will not be gathered.")
            await self.temp_disable_logging()
            return

        await self.bot.wait_until_ready()

        log.info("Bot ready, testing database connection...")

        try:
            await database.client.ping()
            log.info("✅ Database up, Statistics will be gathered.")
        except Exception as e:
            log.error(f"❌ Failed to connect to statistics database: {e}"
                      " Statistics will not be gathered.")
            await self.temp_disable_logging()

    @commands.Cog.listener()
    async def on_statistics_event(self, measurement: str, event: dict, data: dict) -> None:
        if self.log_external_stats is True:
            await database.write_data_point(measurement, event, data)

    """
    Shard/Connection statistics
    """

    async def update_bot_stats(self):

        if self.bot.uptime is not None:
            uptime = (datetime.utcnow() - self.bot.uptime).total_seconds()
        else:
            uptime = 0

        data = {
            "latency": self.bot.latency,
            "guild_count": len(self.bot.guilds),
            "user_count": len(self.bot.users),
            "uptime": uptime,
        }

        await database.write_data_point("bot_stats", {"bot_id": self.bot.user.id}, data)

    """
    Voice channel statistics
    """

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:

        # Bail if we are not logging vc stats
        if self.log_vc_stats is False:
            return

        guild_id = member.guild.id

        # Update the statistics for the channel the member left
        if before.channel is not None:
            channel_id = before.channel.id

            # We cant use the before.channel.members list as the member is already gone
            channel = member.guild.get_channel(channel_id)

            await database.write_vc_stats(guild_id, channel_id, channel.name, len(channel.members),
                                          [member for member in channel.members])

        # Update the statistics for the channel the member joined
        if after.channel is not None:
            channel_id = after.channel.id
            await database.write_vc_stats(guild_id, channel_id, after.channel.name, len(after.channel.members),
                                          [member for member in after.channel.members])

    async def update_all_vc_stats(self):
        # Bail if we are not logging vc stats
        if self.log_vc_stats is False:
            return

        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                await database.write_vc_stats(guild.id, channel.id, channel.name, len(channel.members),
                                              [member for member in channel.members])

    """
    Message statistics
    """

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Bail if we are not logging message stats
        if self.log_message_stats is False:
            return

        # Bail if the message is from a bot
        if message.author.bot:
            return

        # Bail if the message is from a DM
        if message.guild is None:
            return

        guild_id = message.guild.id
        channel_id = message.channel.id

        # Cache the channel name if we don't have it
        self.channel_name_cache[guild_id][channel_id] = message.channel.name

        # Add the message to the cache
        self.message_stats_cache[guild_id][channel_id] += 1

    async def update_all_message_stats(self):
        # Bail if we are not logging message stats
        if self.log_message_stats is False:
            return

        await database.write_message_stats(self.message_stats_cache, self.channel_name_cache)
        self.message_stats_cache.clear()

    """
    Configuration commands
    """

    @commands.command("set_statistics_db")
    @commands.dm_only()
    @commands.is_owner()
    async def statistics_set(self, ctx: commands.Context, address: str, bucket: str, org: str, token: str):
        """
        Set the api credentials for the statistics database

        *address*: The address of the database
        *bucket*: The bucket to store the data in
        *org*: The influxdb organization
        *token*: The key for the database
        """

        if ctx.author.id not in self.bot.owner_ids:  # Double check just in case xD
            return await ctx.send("You must be the bot owner to use this command")

        await self.config.address.set(address)
        await self.config.bucket.set(bucket)
        await self.config.org.set(org)
        await self.config.token.set(token)

        await ctx.send("Statistics database credentials set... Testing connection...")

        try:
            await database.activate_client(address, bucket, token, org)
            await ctx.send(":white_check_mark: Connection successful.")
        except Exception as e:
            await ctx.send(f"Failed to connect to the database: {e}\n"
                           f"Make sure the credentials are correct and the database is up.\n"
                           f"_Also make sure the address is in the format: http(s)://<ip>:<port>_")
            return

    @commands.command("set_logging_level")
    @commands.dm_only()
    @commands.is_owner()
    async def set_logging_level(self, ctx: commands.Context, log_vc_stats: bool, log_message_stats: bool,
                                log_bot_stats: bool, log_external_stats: bool):
        """
        Set the logging level for the statistics cog

        **log_vc_stats**: Log voice channel statistics `(True/False)`
        **log_message_stats**: Log message statistics `(True/False)`
        **log_bot_stats**: Log bot statistics `(True/False)`
        **log_external_stats**: Log external statistics `(True/False)`

        """

        # Update the config values
        await self.config.log_vc_stats.set(log_vc_stats)
        await self.config.log_message_stats.set(log_message_stats)
        await self.config.log_bot_stats.set(log_bot_stats)
        await self.config.log_external_stats.set(log_external_stats)

        # Update the in memory values
        await self.load_config()

        # Send a confirmation message
        await ctx.send(f"Statistics logging set to: \n"
                       f"- VC Statistics: {log_vc_stats}\n- Message Statistics: {log_message_stats},\n"
                       f"- Bot Statistics: {log_bot_stats},\n- External Statistics: {log_external_stats}")

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
