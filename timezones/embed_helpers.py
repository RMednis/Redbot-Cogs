import datetime
import logging

import discord
from redbot.core.bot import Red

from timezones import time_convert

version = "1.0.0"
log = logging.getLogger("red.mednis-cogs.timezones")


async def button_changer(self, button: discord.ui.Button):
    # Color the button based on the time display mode
    if self.AmPm:
        button.style = discord.ButtonStyle.primary
        button.label = "24 Hour"
    else:
        button.style = discord.ButtonStyle.secondary
        button.label = "12 Hour"


class TimeChangeUsers(discord.ui.View):
    def __init__(self, timezone: str, member: discord.Member, interaction: discord.Interaction):
        self.timezone = timezone
        self.member = member
        self.AmPm = False
        self.interaction = interaction
        super().__init__(timeout=60)

    @discord.ui.button(label="12 Hour")
    async def time_display_switch(self, interaction, button):
        await interaction.response.defer()  # Tell Discord we are handling the interaction

        self.AmPm = not self.AmPm  # Switch the time display mode

        await button_changer(self, button)

        response = await self.interaction.original_response()  # Get the original response

        # Update the original response with the new time display mode
        await response.edit(
            embed=await time_for_person(self.member, self.timezone, self.AmPm), view=self
        )


class TimeChangeLocation(discord.ui.View):
    def __init__(self, timezone: str, location: str, interaction: discord.Interaction):
        self.timezone = timezone
        self.location = location
        self.AmPm = False
        self.interaction = interaction

        super().__init__(timeout=60)

    @discord.ui.button(label="12 Hour")
    async def time_display_switch(self, interaction, button):
        await interaction.response.defer()  # Tell Discord we are handling the interaction

        self.AmPm = not self.AmPm  # Switch the time display mode

        await button_changer(self, button)

        response = await self.interaction.original_response()  # Get the original response

        # Update the original response with the new time display mode
        await response.edit(
            embed=await time_embed(self.timezone, self.location, self.AmPm), view=self
        )


class PersistentMessage(discord.ui.View):
    def __init__(self, config, users: list, message: discord.Message, command_mention: str):
        self.users = users
        self.AmPm = False
        self.message = message
        self.last_interaction_time = None
        self.config = config
        self.command_mention = command_mention
        super().__init__(timeout=None)

    @discord.ui.button(label="12 Hour")
    async def time_display_switch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.last_interaction_time is not None:
            if (datetime.datetime.now() - self.last_interaction_time).seconds < 10:
                await interaction.response.send_message("⚠️ Please wait a few seconds before changing the time display "
                                                        "mode!",
                                                        ephemeral=True, delete_after=15)
                return

        await interaction.response.defer()  # Tell Discord we are handling the interaction
        self.last_interaction_time = datetime.datetime.now()  # Update the last interaction time

        self.AmPm = not self.AmPm  # Switch the time display mode

        await button_changer(self, button)

        # Update the original response with the new time display mode
        await self.message.edit(
            embed=await user_time_list(self.users, self.message.guild, self.command_mention, self.AmPm), view=self
        )

    @discord.ui.button(label="Add/Remove", style=discord.ButtonStyle.danger)
    async def add_remove_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        users = await self.config.guild(interaction.guild).persistent_message_users()

        found = any(userid == interaction.user.id for userid, _ in users)

        if found:
            users_with_timezones = [x for x in users if x[0] != interaction.user.id]
            await self.config.guild(interaction.guild).persistent_message_users.set(users_with_timezones)
            await interaction.response.send_message("❌ **You have been removed from the time display board.**\n"
                                                    "You will have to wait for it to refresh before "
                                                    "seeing the changes!",
                                                    ephemeral=True, delete_after=15)
        else:
            timezone = await self.config.user(interaction.user).timezone()

            if timezone == "":
                await interaction.response.send_modal(TimezoneModal(self.config))
                return

            users.append((interaction.user.id, timezone))
            await self.config.guild(interaction.guild).persistent_message_users.set(users)

            await interaction.response.send_message("✅ **You have been added to the time display board.** \n"
                                                    "You will have to wait for it to refresh before "
                                                    "seeing the changes!",
                                                    ephemeral=True, delete_after=15)


class TimezoneModal(discord.ui.Modal, title='Set a timezone'):

    def __init__(self, config):
        self.config = config
        super().__init__()

    location = discord.ui.TextInput(
        label='Enter a nearby city/town/general area:',
        placeholder='London, New York, etc.',
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        apikey = await self.config.guild(interaction.guild).geonames_apikey()

        try:
            timezone = await time_convert.city_to_timezone(self.location.value, apikey)
            iana_name = timezone[0]

            # Save the timezone to the user's settings
            await self.config.user(interaction.user).timezone.set(iana_name)

            # Save the timezone to the guild's settings
            users = await self.config.guild(interaction.guild).persistent_message_users()
            users.append((interaction.user.id, iana_name))
            await self.config.guild(interaction.guild).persistent_message_users.set(users)

            await interaction.response.send_message(f"Timezone set to `{iana_name}`!",
                                                    embed=await time_for_person(interaction.user, iana_name),
                                                    view=TimeChangeUsers(iana_name, interaction.user, interaction),
                                                    delete_after=60, ephemeral=True
                                                    )
        except ValueError as e:
            log.info(f"{interaction.user.id} - ERROR - {e}")
            await interaction.response.send_message(
                f"Could not find a timezone for `{self.location}`. Make sure you entered a valid city name.",
                ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong... Try again later!', ephemeral=True)

        # Make sure we know what the error actually is
        log.error(f'Error in timezone modal:{error}')


class TimeEmbed(discord.Embed):
    def version_footer(self):
        return self.set_footer(text=f"Medsbot Timezones v{version}")


def greeting_calculator(hour: int) -> str:
    if 5 <= hour < 12:
        return "🌇  Good morning!"
    elif 12 <= hour < 18:
        return "☀️  Good afternoon!"
    elif 18 <= hour < 22:
        return "🌆  Good evening!"
    else:
        return "🌛  Good night!"


def emoji_calculator(hour: int) -> str:
    if 5 <= hour < 12:
        return "🌇"
    elif 12 <= hour < 18:
        return "☀️"
    elif 18 <= hour < 22:
        return "🌆"
    else:
        return "🌛"


def color_calculator(hour: int) -> int:
    if 5 <= hour < 8:
        return 0x8D5273
    elif 8 <= hour < 12:
        return 0xC3727C
    elif 12 <= hour < 18:
        return 0xE8817F
    elif 18 <= hour < 24:
        return 0x5A336E
    else:
        return 0x311f62


async def utc_time(timezone) -> str:
    utc_offset = await time_convert.timezone_to_utc(timezone)
    dst = await time_convert.dst_status(timezone)
    return f"(UTC{utc_offset}{dst})"


async def time_embed(timezone: str, location="", ampm=False) -> TimeEmbed:
    time = await time_convert.get_time_object(timezone)
    utc_offset = await utc_time(timezone)

    # Support to display time in 12-hour format
    if ampm:
        time_str = time.strftime('%A - %I:%M %p')
    else:
        time_str = time.strftime('%A - %H:%M')

    if location == "":
        description = (f"The current time in `{timezone} {utc_offset}` is:\n"
                       f"# {time_str}\n"
                       )
    else:
        description = (f"In **{location}** \n"
                       f"`{timezone} {utc_offset}`\n"
                       f"The current time is:\n"
                       f"# {time_str}\n"
                       )

    embed = (TimeEmbed(
        title=greeting_calculator(time.hour),
        description=description,
        colour=color_calculator(time.hour))
             .version_footer())
    return embed


async def time_for_person(person: discord.Member, timezone: str, ampm=False) -> TimeEmbed:
    time = await time_convert.get_time_object(timezone)

    if ampm:
        time_str = time.strftime('%A - %I:%M %p')
    else:
        time_str = time.strftime('%A - %H:%M')

    description = (f"The current time for {person.mention} `{await utc_time(timezone)}` is:\n"
                   f"# {time_str}\n"
                   )

    embed = (TimeEmbed(
        title=greeting_calculator(time.hour),
        description=description,
        colour=color_calculator(time.hour))
             .version_footer())
    return embed


async def user_time_list(users_times: list, guild: discord.Guild, command_mention: str, ampm=False) -> TimeEmbed:
    description = "These are the current times for the users in this server:\n"
    previous_day = None
    for timezone in users_times:
        time = timezone["time"]
        utc_offset = await time_convert.utc_time(time)

        if previous_day != time.strftime('%A'):
            emoji = emoji_calculator(time.hour)
            description += f"### {emoji} **{time.strftime('%A')}** {time.strftime(', %d %B')}\n"
            previous_day = time.strftime('%A')

        if ampm:
            time_str = time.strftime('%I:%M %p')
        else:
            time_str = time.strftime('%H:%M')

        users = ""
        for userid in timezone["users"]:
            user = guild.get_member(userid)
            if users != "":
                users += f", {user.mention}"
            else:
                users += f"{user.mention}"

        description += f"- `{time_str}` `(UTC{utc_offset})`: {users}\n"

    description += (f"\n You can use {command_mention} to set it based on location, or lookup your timezone name " \
                    f"[here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) and use the `iana` option!" \
                    f"\nGeolocation is only used to figure out your timezone and uses GeoNames for the information." \
                    f"\n\n_You can toggle 12/24 hour time and whether or not you should be shown in this" \
                    f" list with the buttons below._")

    embed = (TimeEmbed(
        title="🕒 Server Times",
        description=description,
        colour=color_calculator(datetime.datetime.now().hour))
             .version_footer())

    return embed
