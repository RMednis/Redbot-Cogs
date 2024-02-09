from typing import Literal

import discord
from discord import app_commands
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

from timezones import time_convert, embed_helpers

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Timezones(commands.Cog):
    """
    A timezone and time conversion cog
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=92651437657460736,
            force_registration=True,
        )

        default_guild = {
            "persistent_channel": "",
            "persistent_message": "",
            "timezone_users": {},
            "geonames_apikey": ""
        }

        self.config.register_guild(**default_guild)

        default_user = {
            "timezone": ""
        }

        self.config.register_user(**default_user)

        self.show_timezone_app = discord.app_commands.ContextMenu(
            name="Show Time", callback=self.show_user_timezone
        )

        self.show_timezone_app.guild_only = True

    def cog_load(self):
        # Load app commands when the cog is loaded
        self.bot.tree.add_command(self.show_timezone_app)

    def cog_unload(self):
        # Unload app commands when unloading cog
        self.bot.tree.remove_command(self.show_timezone_app.name, type=self.show_timezone_app.type)

    # /timezone
    tz = app_commands.Group(name="timezone", description="View other people's timezones and set your own",
                            guild_only=True)

    # /timezone view
    @tz.command(name="view", description="View a user's timezone")
    async def view(self, interaction: discord.Interaction, user: discord.Member) -> None:
        timezone = await self.config.user(user).timezone()
        if timezone != "":
            await interaction.response.send_message(f"{user.mention}'s timezone is {timezone}",
                                                    allowed_mentions=discord.AllowedMentions(users=False))
        else:
            await interaction.response.send_message(f"{user.mention} has not set a timezone.",
                                                    allowed_mentions=discord.AllowedMentions(users=False))

    # /timezone difference <@user>
    @app_commands.describe(user="Person to compare your timezone with.")
    @app_commands.rename(user="person")
    @app_commands.describe(user2="Other person to compare the first persons timezone with.")
    @app_commands.rename(user2="second_person")
    @tz.command(name="difference", description="View the time difference between you and someone else")
    async def difference(self, interaction: discord.Interaction, user: discord.Member,
                         user2: discord.Member = None) -> None:
        if user2 is None:
            user2 = user
            user = interaction.user

        user1_timezone = await self.config.user(user2).timezone()
        user2_timezone = await self.config.user(user).timezone()

        if user1_timezone != "" and user2_timezone != "":
            difference = await time_convert.timezone_difference(user1_timezone, user2_timezone)
            await interaction.response.send_message(f"{user.mention} {difference} {user2.mention}",
                                                    allowed_mentions=discord.AllowedMentions(users=False))
        else:
            await interaction.response.send_message("Both users have to set their timezones to use this command.", )

    # /timezone set
    set_group = app_commands.Group(parent=tz, name="set", description="Set your timezone")

    # /timezone set city <city>
    @set_group.command(name="city", description="Set your timezone by entering a nearby city name")
    async def city(self, interaction: discord.Interaction, city: str) -> None:
        apikey = await self.config.guild(interaction.guild).geonames_apikey()
        try:
            timezone = await time_convert.city_to_timezone(city, apikey)
            iana_name = timezone[0]
            await self.config.user(interaction.user).timezone.set(iana_name)
            await interaction.response.send_message(f"Timezone set to `{iana_name}`!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(
                f"Could not find a timezone for `{city}`. Make sure you entered a valid city name.", ephemeral=True)

    # /timezone set iana <Location/Timezone>
    @set_group.command(name="iana", description="Set your timezone by entering an IANA timezone name")
    @app_commands.describe(iana_name="The timezone you want to set. Has to be a valid IANA timezone name. ("
                                     "Region/City, etc)")
    async def iana(self, interaction: discord.Interaction, iana_name: str) -> None:
        if await time_convert.check_timezone(iana_name):
            await self.config.user(interaction.user).timezone.set(iana_name)
            await interaction.response.send_message(f"Timezone set to `{iana_name}`!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Could not find timezone `{iana_name}`, make sure it is a valid "
                                                    f"IANA timezone name. You can see a list of IANA timezone names ["
                                                    f"here]("
                                                    f"https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).",
                                                    ephemeral=True)

    # /timezone set remove
    @set_group.command(name="remove", description="Remove your timezone and hide it from others")
    async def remove(self, interaction: discord.Interaction) -> None:
        user = interaction.user
        await self.config.user(user).timezone.set("")
        await interaction.response.send_message("Previous timezone removed! (You will be removed from the timezone "
                                                "board the next time it refreshes!)", ephemeral=True)

    # /time
    time = app_commands.Group(name="time", description="View the current time for a user or in a timezone",
                              guild_only=True)

    # /time for <@user>
    @time.command(name="for", description="View the current time for a user")
    @app_commands.describe(user="Person for whom you want to see the current time.")
    @app_commands.rename(user="person")
    async def user(self, interaction: discord.Interaction, user: discord.Member) -> None:
        timezone = await self.config.user(user).timezone()
        embed = await embed_helpers.time_for_person(user, timezone)

        if timezone != "":
            await interaction.response.send_message(embed=embed, delete_after=60)
        else:
            await interaction.response.send_message("This user has not set a timezone.",
                                                    ephemeral=True, delete_after=60)

    async def show_user_timezone(self, interaction: discord.Interaction, user: discord.User) -> None:
        timezone = await self.config.user(user).timezone()
        embed = await embed_helpers.time_for_person(user, timezone)

        if timezone != "":
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=60)
        else:
            await interaction.response.send_message("This user has not set a timezone.",
                                                    ephemeral=True, delete_after=60)

    # /time in <city>
    @time.command(name="in", description="View the current time in a timezone")
    @app_commands.describe(timezone="City or IANA timezone name in which you want to see the time.")
    @app_commands.rename(timezone="timezone-or-city")
    async def timezone(self, interaction: discord.Interaction, timezone: str) -> None:
        apikey = await self.config.guild(interaction.guild).geonames_apikey()

        if await time_convert.check_timezone(timezone):
            await interaction.response.send_message(
                embed=await embed_helpers.time_embed(timezone),
                delete_after=60
            )
        else:
            try:
                timezone_data = await time_convert.city_to_timezone(timezone, apikey)
                await interaction.response.send_message(
                    embed=await embed_helpers.time_embed(timezone_data[0], timezone_data[1]),
                    delete_after=60
                )
            except ValueError:
                await interaction.response.send_message(f"Could not find a timezone for `{timezone}`. Make sure you "
                                                        f"entered a valid timezone or city name.", ephemeral=True)

    # /time here
    @time.command(name="here", description="Show the current time in your timezone")
    async def here(self, interaction: discord.Interaction) -> None:
        timezone = await self.config.user(interaction.user).timezone()
        if timezone != "":
            await interaction.response.send_message(
                embed=await embed_helpers.time_for_person(interaction.user, timezone),
                delete_after=60
            )
        else:
            await interaction.response.send_message(
                "You have not set a timezone. Use `/timezone set` city or iana to set your timezone.")

    # /tz-setup
    tzsetup = app_commands.Group(name="tz-setup", description="Setup the timezone cog",
                                 guild_only=True)

    # /tz-setup channel <#channel>
    @tzsetup.command(name="channel", description="Set the channel for persistent time messages")
    @commands.has_permissions(administrator=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await self.config.guild(interaction.guild).persistent_channel.set(channel.id)
        await interaction.response.send_message(f"Persistent channel set to {channel.mention}!")

    # /tz-setup apikey <apikey>
    @tzsetup.command(name="apikey", description="Set the API key for geonames")
    @commands.has_permissions(administrator=True)
    async def apikey(self, interaction: discord.Interaction, apikey: str) -> None:
        await self.config.guild(interaction.guild).geonames_apikey.set(apikey)
        await interaction.response.send_message("API key set!", ephemeral=True)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        await super().red_delete_data_for_user(requester=requester, user_id=user_id)
