import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter

from timezones import time_convert, embed_helpers

log = logging.getLogger("red.mednis-cogs.timezones")

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
            "persistent_message_users": [],
            "geonames_apikey": "",
            "twelve_hour_time": False,
            "command_mention": ""
        }

        self.config.register_guild(**default_guild)

        default_user = {
            "timezone": ""
        }

        self.config.register_user(**default_user)

        # App interaction for showing time
        self.show_timezone_app = discord.app_commands.ContextMenu(
            name="Show Time", callback=self.show_user_timezone_app
        )
        self.show_timezone_app.guild_only = True

        # Start the loop to update the time list
        self.time_list_update_loop.start()

    def __unload(self):
        self.time_list_update_loop.stop()

    def cog_load(self):
        # Load app commands when the cog is loaded
        self.bot.tree.add_command(self.show_timezone_app)

    def cog_unload(self):
        # Unload app commands when unloading cog
        self.bot.tree.remove_command(self.show_timezone_app.name, type=self.show_timezone_app.type)
        self.__unload()

    @tasks.loop(seconds=30)
    async def time_list_update_loop(self):
        await self.bot.wait_until_ready()

        log.info("--- Updating time lists ---")

        async for guild in AsyncIter(self.bot.guilds):

            guild = self.bot.get_guild(guild.id)
            log.info(f"Updating time list for {guild.name}: {guild.id}")

            persistent_channel = await self.config.guild(guild).persistent_channel()
            persistent_message = await self.config.guild(guild).persistent_message()
            twelve_hour_time = await self.config.guild(guild).twelve_hour_time()
            command_mention = await self.config.guild(guild).command_mention()

            if persistent_message != "" and persistent_channel != "":
                try:
                    channel = await self.bot.fetch_channel(persistent_channel)
                    message = await channel.fetch_message(persistent_message)
                except (discord.NotFound, ValueError):
                    # The message or channel was deleted, so we reset the persistent message
                    await self.config.guild(guild).persistent_message.set("")
                    await self.config.guild(guild).persistent_channel.set("")
                    log.error("Persistent message or channel was deleted, resetting the persistent message.")
                    continue
                except (discord.HTTPException, discord.Forbidden):
                    # We can't access the channel or message, so we skip this guild
                    log.error("Could not access the persistent message or channel, skipping this guild.")
                    continue

                # Get the list of users and their timezones, sort it
                users_with_timezones = await self.config.guild(guild).persistent_message_users()
                users_with_times = await time_convert.get_times_for_all_timezones(users_with_timezones)

                # Convert the list of users and their timezones into a list of time objects
                users_with_times = await time_convert.sort_list_into_times(users_with_times)

                try:
                    await message.edit(
                        content="",
                        embed=await embed_helpers.user_time_list(users_with_times, guild, command_mention, twelve_hour_time),
                        view=embed_helpers.PersistentMessage(self.config, users_with_times, message, command_mention)
                    )
                except discord.HTTPException as e:
                    log.error(f"Error: {e}")
                    continue

    # Manage the timezone board
    async def remove_user_from_board(self, user: discord.User, guild: discord.Guild) -> None:
        users_with_timezones = await self.config.guild(guild).persistent_message_users()
        users_with_timezones = [x for x in users_with_timezones if x[0] != user.id]
        await self.config.guild(guild).persistent_message_users.set(users_with_timezones)

    async def add_user_to_board(self, user: discord.User, guild: discord.Guild, timezone: str) -> None:
        await self.remove_user_from_board(user, guild)
        users_with_timezones = await self.config.guild(guild).persistent_message_users()
        users_with_timezones.append((user.id, timezone))
        await self.config.guild(guild).persistent_message_users.set(users_with_timezones)

    # /timezone
    tz = app_commands.Group(name="timezone", description="View other people's timezones and set your own",
                            guild_only=True)

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
            await interaction.response.send_message("Both users have to set their timezones to use this command.",
                                                    ephemeral=True)

    # /timezone set
    set_group = app_commands.Group(parent=tz, name="set", description="Set your timezone")

    # /timezone set city <city>
    @set_group.command(name="city", description="Set your timezone by entering a nearby city name")
    async def city(self, interaction: discord.Interaction, city: str) -> None:
        apikey = await self.config.guild(interaction.guild).geonames_apikey()
        try:
            timezone = await time_convert.city_to_timezone(city, apikey)
            iana_name = timezone[0]

            # Save the timezone to the user's settings and add them to the board
            await self.config.user(interaction.user).timezone.set(iana_name)
            await self.add_user_to_board(interaction.user, interaction.guild, iana_name)

            await interaction.response.send_message(f"Timezone set to `{iana_name}`!", ephemeral=True)
        except ValueError as e:
            log.info(f"{interaction.user.id} - ERROR - {e}")
            await interaction.response.send_message(
                f"Could not find a timezone for `{city}`. Make sure you entered a valid city name.", ephemeral=True)

    # /timezone set iana <Location/Timezone>
    @set_group.command(name="iana", description="Set your timezone by entering an IANA timezone name")
    @app_commands.describe(iana_name="The timezone you want to set. Has to be a valid IANA timezone name. ("
                                     "Region/City, etc)")
    async def iana(self, interaction: discord.Interaction, iana_name: str) -> None:
        if await time_convert.check_timezone(iana_name):
            # Save the timezone to the user's settings and add them to the board
            await self.config.user(interaction.user).timezone.set(iana_name)
            await self.add_user_to_board(interaction.user, interaction.guild, iana_name)

            await interaction.response.send_message(f"Timezone set to `{iana_name}`!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Could not find timezone `{iana_name}`, make sure it is a valid "
                                                    f"IANA timezone name. You can see a list of IANA timezone names ["
                                                    f"here]("
                                                    f"https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).",
                                                    ephemeral=True, delete_after=60)

    # /timezone set remove
    @set_group.command(name="remove", description="Remove your timezone and hide it from others")
    async def remove(self, interaction: discord.Interaction) -> None:
        user = interaction.user
        await self.config.user(user).timezone.set("")
        await self.remove_user_from_board(user, interaction.guild)
        await interaction.response.send_message("Previous timezone removed! (You will be removed from the timezone "
                                                "board the next time it refreshes!)", ephemeral=True, delete_after=60)

    # /time
    time = app_commands.Group(name="time", description="View the current time for a user or in a timezone",
                              guild_only=True)

    # /time for <@user>
    @time.command(name="for", description="View the current time for a user")
    @app_commands.describe(user="Person for whom you want to see the current time.")
    @app_commands.rename(user="person")
    async def user(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self.show_user_timezone(interaction, user, ephemeral=False)

    async def show_user_timezone_app(self, interaction: discord.Interaction, user: discord.User) -> None:
        await self.show_user_timezone(interaction, user, ephemeral=True)

    async def show_user_timezone(self, interaction: discord.Interaction, user: discord.User, ephemeral=True) -> None:
        timezone = await self.config.user(user).timezone()

        if timezone != "":
            embed = await embed_helpers.time_for_person(user, timezone)
            await interaction.response.send_message(embed=embed,
                                                    delete_after=60,
                                                    view=embed_helpers.TimeChangeUsers(timezone, user, interaction),
                                                    ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ This user has __not__ set a timezone :(",
                                                    ephemeral=ephemeral, delete_after=15)

    # /time in <city>
    @time.command(name="in", description="View the current time in a timezone")
    @app_commands.describe(timezone="City or IANA timezone name in which you want to see the time.")
    @app_commands.rename(timezone="timezone-or-city")
    async def timezone(self, interaction: discord.Interaction, timezone: str) -> None:
        apikey = await self.config.guild(interaction.guild).geonames_apikey()

        if await time_convert.check_timezone(timezone):
            await interaction.response.send_message(
                embed=await embed_helpers.time_embed(timezone),
                delete_after=60,
                view=embed_helpers.TimeChangeLocation(timezone, timezone, interaction)
            )
        else:
            try:
                timezone_data = await time_convert.city_to_timezone(timezone, apikey)
                await interaction.response.send_message(
                    embed=await embed_helpers.time_embed(timezone_data[0], timezone_data[1]),
                    delete_after=60,
                    view=embed_helpers.TimeChangeLocation(timezone_data[0], timezone_data[1], interaction)
                )
            except ValueError as e:
                log.info(f"{interaction.user.id} - ERROR - {e} - time in {timezone}")
                await interaction.response.send_message(f"Could not find a timezone for `{timezone}`. Make sure you "
                                                        f"entered a valid timezone or city name.", ephemeral=True)

    # /time here
    @time.command(name="here", description="Show the current time in your timezone")
    async def here(self, interaction: discord.Interaction) -> None:
        timezone = await self.config.user(interaction.user).timezone()
        command_mention = await self.config.guild(interaction.guild).command_mention()
        if timezone != "":
            await interaction.response.send_message(
                embed=await embed_helpers.time_for_person(interaction.user, timezone),
                delete_after=60,
                view=embed_helpers.TimeChangeUsers(timezone, interaction.user, interaction)
            )
        else:
            await interaction.response.send_message(
                f"You have not set a timezone. Use {command_mention} to set your timezone!")

    convert_time = app_commands.Group(parent=time, name="convert", description="Convert a time from one timezone to another")

    @convert_time.command(name="from", description="A time to a different users timezone")
    @app_commands.describe(time="The time you want to convert")
    @app_commands.rename(member="member_from")
    @app_commands.describe(member="The user whose timezone you want to convert the time from")
    @app_commands.rename(member2="member_to")
    @app_commands.describe(member2="The user whose timezone you want to convert the time to")
    async def convert_time_from(self, interaction: discord.Interaction, member: discord.Member, time: str,
                                member2: discord.Member = None) -> None:

        if member2 is None:  # If the second member is not given, assume it's the user who used the command
            member2 = interaction.user

        # Get the timezones of the users
        user1_timezone = await self.config.user(member).timezone()
        user2_timezone = await self.config.user(member2).timezone()

        # Check if the users have set their timezones
        if user1_timezone == "":
            await interaction.response.send_message(f"{member.mention} has not set a timezone.", ephemeral=False)
            return
        if user2_timezone == "":
            await interaction.response.send_message(f"{member2.mention} has not set a timezone.", ephemeral=False)
            return

        # Convert the time and send the message
        try:
            time_object = await time_convert.get_time_from_fuzzy_input(time)  # Get the time object from the input

            # Convert the time to the other user's timezone
            converted_time = await time_convert.convert_time_between_zones(user1_timezone, user2_timezone, time_object)
            utc_time = await time_convert.convert_time_between_zones(user1_timezone, "UTC", time_object)

            await interaction.response.send_message(embed=await embed_helpers.time_convert_from(time, member, member2,
                                                                                                utc_time, converted_time),
                                                    ephemeral=False)
        except ValueError as e:
            await interaction.response.send_message(f"**Error Converting Time:** {e}", ephemeral=False)
            return

    @convert_time.command(name="to", description="A time to a different users timezone")
    @app_commands.describe(time="The time you want to convert")
    @app_commands.rename(member="member_to")
    @app_commands.describe(member="The user whose timezone you want to convert the time to")
    @app_commands.rename(member2="member_from")
    @app_commands.describe(member2="The user whose timezone you want to convert the time from")
    async def convert_time_to(self, interaction: discord.Interaction, member: discord.Member, time: str,
                              member2: discord.Member = None) -> None:

        if member2 is None:  # If the second member is not given, assume it's the user who used the command
            member2 = interaction.user

        # Get the timezones of the users
        user1_timezone = await self.config.user(member).timezone()
        user2_timezone = await self.config.user(member2).timezone()

        # Check if the users have set their timezones
        if user1_timezone == "":
            await interaction.response.send_message(f"{member.mention} has not set a timezone.", ephemeral=False)
            return
        if user2_timezone == "":
            await interaction.response.send_message(f"{member2.mention} has not set a timezone.", ephemeral=False)
            return

        # Convert the time and send the message
        try:
            time_object = await time_convert.get_time_from_fuzzy_input(time)  # Get the time object from the input

            # Convert the time to the other user's timezone
            converted_time = await time_convert.convert_time_between_zones(user2_timezone, user1_timezone, time_object)
            utc_time = await time_convert.convert_time_between_zones(user2_timezone, "UTC", time_object)

            await interaction.response.send_message(embed=await embed_helpers.time_convert_to(time, member, member2,
                                                                                                utc_time,
                                                                                                converted_time),
                                                    ephemeral=False)
        except ValueError as e:
            await interaction.response.send_message(f"**Error Converting Time:** {e}", ephemeral=False)
            return


    # /tz-setup
    tzsetup = app_commands.Group(name="tz-setup", description="Setup the timezone cog",
                                 guild_only=True)

    # /tz-setup channel <#channel>
    @tzsetup.command(name="channel", description="Set the channel for persistent time messages")
    @commands.has_permissions(administrator=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            message = await channel.send("Loading...")
        except discord.HTTPException:
            await interaction.response.send_message("I don't have permission to send messages in that channel.",
                                                    ephemeral=True)
            return

        await self.config.guild(interaction.guild).persistent_channel.set(channel.id)
        await self.config.guild(interaction.guild).persistent_message.set(message.id)

        await interaction.response.send_message(f"Persistent channel set to {channel.mention}!")

    # /tz-setup apikey <apikey>
    @tzsetup.command(name="apikey", description="Set the API key for geonames")
    @commands.has_permissions(administrator=True)
    async def apikey(self, interaction: discord.Interaction, apikey: str) -> None:
        await self.config.guild(interaction.guild).geonames_apikey.set(apikey)
        await interaction.response.send_message("API key set!", ephemeral=True)

    # /tz-setup commandmention <command element>
    @tzsetup.command(name="command_mention", description="Set the command mention for the cog")
    @commands.has_permissions(administrator=True)
    async def command_mention(self, interaction: discord.Interaction, command_mention: str) -> None:
        await self.config.guild(interaction.guild).command_mention.set(command_mention)
        await interaction.response.send_message(f"Command mention set to {command_mention}", ephemeral=True)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        for guild in self.bot.guilds:
            await self.config.guild(guild).persistent_message_users.set(
                [x for x in await self.config.guild(guild).persistent_message_users() if x[0] != user_id]
            )
        await self.config.user_from_id(user_id).clear()
        await super().red_delete_data_for_user(requester=requester, user_id=user_id)
