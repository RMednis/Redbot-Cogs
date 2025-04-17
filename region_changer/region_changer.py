from http.client import HTTPException
from typing import Literal

import discord
from discord import app_commands
from discord.app_commands import Choice, Command
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

        default_bot = {
            "regions": {}
        }

        default_guild = {
            "channel_whitelist": [],
            "enabled": False
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_bot)


    region_settings = app_commands.Group(name="region_settings",
                                        description="Configure the roles and channels that can change the region of a voice channel",
                                        guild_only=True)

    region_names = {
        "brazil": "Brazil",
        "hongkong": "Hong Kong",
        "india": "India",
        "japan": "Japan",
        "rotterdam": "Rotterdam",
        "russia": "Russia",
        "singapore": "Singapore",
        "south-korea": "South Korea",
        "southafrica": "South Africa",
        "sydney": "Sydney",
        "us-central": "US Central",
        "us-east": "US East",
        "us-south": "US South",
        "us-west": "US West"
    }

    async def update_region_list(self, error: discord.HTTPException) -> None:
        """
        Update the region list if the error is a 400 error
        """
        if error.status == 400:
            if "In rtc_region: Value must be one of" in error.text:
                # Get the list of available regions
                text = error.text.split("In rtc_region: Value must be one of (")[1].split(",")
                regions = []
                for part in text:
                    part = part.strip()
                    part = part.replace("'", "")
                    part = part.replace('(', "")
                    part = part.replace(')', "")
                    part = part.replace('.', "")
                    regions.append(part)

                logger.info(f"Updated region list: {regions}")

                # Make the list into a nicely formated array of choices
                choices = {}
                for region in regions:
                    # If the region is not in the region_names dict, add it as is
                    if region not in self.region_names:
                        choices[region] = region

                    # Otherwise, add it with the name from the region_names dict
                    else:
                        choices[region] = self.region_names[region]

                # Update the config
                await self.config.regions.set(choices)

    async def region_autocomplete(self, interaction: discord.Interaction, current: str):
        # Get config
        regions = await self.config.regions()
        # If the config is empty, return the default region names
        if not regions:
            regions = self.region_names

        return [Choice(name=regions[region], value=region) for region in regions.keys() if current.lower() in region.lower()]

    async def force_region_update(self, interaction: discord.Interaction) -> str:
        if (interaction.channel.id not in await self.config.guild(interaction.guild).channel_whitelist() or not
                isinstance(interaction.channel, discord.VoiceChannel)):
            return "The channel you are in has is not on the whitelist/a voice channel. Did not perform region refresh."

        else:
            try:
                await interaction.channel.edit(rtc_region="aaaa") # Invalid region to force a refresh
                raise Exception("Region refresh failed, somehow the API did not return a 400 error.")

            except discord.Forbidden:
                return "I don't have permission to change the region of this channel."

            except discord.HTTPException as e:
                await self.update_region_list(e)
                return "Region list updated."

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
        if not isinstance(channel, discord.VoiceChannel):
            return await interaction.response.send_message("The channel must be a voice channel", ephemeral=True)

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

        region_messages = await self.force_region_update(interaction)

        await interaction.response.send_message(f"Cleaned the channel whitelist. \n"
                                                f"Removed {channel_diff} channels \n"
                                                f"{region_messages}")

    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    @app_commands.rename(region_name="set")
    @app_commands.describe(region_name="The region to change the voice channel to")
    @app_commands.autocomplete(region_name=region_autocomplete)

    @app_commands.command(name="region", description="Change the region of the voice channel")
    async def region(self,interaction: discord.Interaction, region_name: str = None):
        if not isinstance(interaction.channel, discord.VoiceChannel):
            return await interaction.response.send_message("This command can only be used in a voice channel",
                                                           ephemeral=True)

        if not await self.config.guild(interaction.guild).enabled():
            return await interaction.response.send_message("Region changer is not enabled", ephemeral=True)

        if interaction.channel.id not in await self.config.guild(interaction.guild).channel_whitelist():
            return await interaction.response.send_message("This channel is not whitelisted", ephemeral=True)

        old_region = interaction.channel.rtc_region

        if region_name is None or region_name == "":
            return await interaction.response.send_message(f"The current region for {interaction.channel.mention} is `{old_region}`",
                                                           ephemeral=True)
        # Check if the region is valid
        if region_name not in await self.config.regions():

            if await self.config.regions() == {}:
                await self.force_region_update(interaction)

            return await interaction.response.send_message(f"Invalid region `{region_name}`. \n"
                                                           f"Available regions: `{', '.join(await self.config.regions())}`",
                                                           ephemeral=True)

        if region_name == old_region:
            return await interaction.response.send_message(f"The region is already set to `{region_name}`", ephemeral=True)

        try:
            await interaction.channel.edit(rtc_region=region_name)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to change the region of this channel")
            return
        except discord.HTTPException as e:
            await interaction.response.send_message("**Failed to change the region.** \n"
                                                    "This may be temporary or the list of available regions has changed on discord's side.",
                                                    ephemeral=True)
            await self.update_region_list(e)
            return

        await interaction.response.send_message(f"Region of {interaction.channel.mention} changed from `{old_region}` to `{region_name}`")


    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
