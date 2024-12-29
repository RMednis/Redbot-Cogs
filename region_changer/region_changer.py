from typing import Literal

import discord
from discord import app_commands
from discord.app_commands import Choice
import logging
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

logger = logging.getLogger("red.mednis.cogs.region_changer")

class RegionChanger(commands.Cog):
    """
    Allows changing the voice channel region without needing specific permissions
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=92651437657460736,
            force_registration=True,
        )

        default_guild = {
            "channel_whitelist": [],
            "enabled": False
        }

        self.config.register_guild(**default_guild)


    region_settings = app_commands.Group(name="region_settings",
                                        description="Configure the roles and channels that can change the region of a voice channel",
                                        guild_only=True)

    @app_commands.guild_only()
    @region_settings.command(name="enable", description="Enable the region changer")
    async def enable(self, interaction: discord.Interaction):

        if await self.config.guild(interaction.guild).enabled():
            await self.config.guild(interaction.guild).enabled.set(False)
            return await interaction.response.send_message("Region changer disabled")
        else:
            await self.config.guild(interaction.guild).enabled.set(True)
            await interaction.response.send_message("Region changer enabled")

    @app_commands.guild_only()
    @region_settings.command(name="add_channel", description="Add a channel to the whitelist")
    async def add_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        async with self.config.guild(interaction.guild).channel_whitelist() as channels:
            channels.append(channel.id)
            await self.config.guild(interaction.guild).channel_whitelist.set(channels)
        await interaction.response.send_message(f"Channel {channel.mention} added to the whitelist")

    @app_commands.guild_only()
    @region_settings.command(name="remove_channel", description="Remove a channel from the whitelist")
    async def remove_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        async with self.config.guild(interaction.guild).channel_whitelist() as channels:
            channels.remove(channel.id)
            await self.config.guild(interaction.guild).channel_whitelist.set(channels)
        await interaction.response.send_message(f"Channel {channel.mention} removed from the whitelist")

    @app_commands.guild_only()
    @region_settings.command(name="clean", description="Remove non-existent channels from the whitelist")
    async def clean(self, interaction: discord.Interaction):
        guild = interaction.guild

        logger.info(f"Cleaning whitelist for {guild.name}")

        async with self.config.guild(guild).channel_whitelist() as channels:
            channels_new = [channel for channel in channels if guild.get_channel(channel)]
            channel_diff = len(channels) - len(channels_new)
            await self.config.guild(guild).channel_whitelist.set(channels_new)

        await interaction.response.send_message(f"Cleaned the channel whitelist. \n"
                                                f"Removed {channel_diff} channels")

    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    @app_commands.describe(region="The region to change the voice channel to")
    @app_commands.choices(region=[
        Choice(name="Brazil", value="brazil"),
        Choice(name="Hong Kong", value="hongkong"),
        Choice(name="India", value="india"),
        Choice(name="Japan", value="japan"),
        Choice(name="Rotterdam", value="rotterdam"),
        Choice(name="Russia", value="russia"),
        Choice(name="Singapore", value="singapore"),
        Choice(name="South Korea", value="south-korea"),
        Choice(name="South Africa", value="southafrica"),
        Choice(name="Sydney", value="sydney"),
        Choice(name="US Central", value="us-central"),
        Choice(name="US East", value="us-east"),
        Choice(name="US South", value="us-south"),
        Choice(name="US West", value="us-west")
    ])
    @app_commands.command(name="region", description="Change the region of the voice channel")
    async def region(self,interaction: discord.Interaction, region: str):
        if not isinstance(interaction.channel, discord.VoiceChannel):
            return await interaction.response.send_message("This command can only be used in a voice channel",
                                                           ephemeral=True)

        if not await self.config.guild(interaction.guild).enabled():
            return await interaction.response.send_message("Region changer is not enabled", ephemeral=True)

        if interaction.channel.id not in await self.config.guild(interaction.guild).channel_whitelist():
            return await interaction.response.send_message("This channel is not whitelisted", ephemeral=True)

        old_region = interaction.channel.rtc_region
        await interaction.channel.edit(rtc_region=region)
        await interaction.response.send_message(f"Region of {interaction.channel.mention} changed from `{old_region}` to `{region}`")


    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
