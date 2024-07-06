import os
from typing import Literal

import discord
from redbot.core import commands, app_commands, data_manager
from redbot.core.bot import Red
from redbot.core.config import Config
import logging
import lavalink

from ttsengine import audio_manager, file_manager, tts_api

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("red.mednis-cogs.poitranslator")


class TTSEngine(commands.Cog):
    """
    A text to speech cog that hooks into RedBots audio system.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

        self.tts_queue = []  # List of tts messages to be played.

        self.last_non_tts_track = None  # The last track that was played before TTS was started.
        self.current_track = None  # The current track that is playing.

        self.cog_path = data_manager.cog_data_path(self)  # The path to the cog data folder.
        self.audio_file_name = (data_manager.cog_data_path(self) / 'audio').as_posix()  # The path to the audio files.
        self.llplayer = None  # The lavalink player.

        # Register the lavalink event listener.
        lavalink.unregister_event_listener(self.lavalink_events)
        lavalink.register_event_listener(self.lavalink_events)

        # Cleanup any old audio files.
        file_manager.cleanup_audio(self)

        self.config = Config.get_conf(
            self,
            identifier=92651437657460736,
            force_registration=True,
        )

        # Default Guild Configuration
        default_guild = {
            "say_name": False,
            "blacklisted_users": [],
            "whitelisted_channels": [],
            "max_message_length": 400,
            "max_word_length": 15,
            "repeated_word_percentage": 80,
            "global_tts_volume": 100,

            # Text replacements
            "name_replacements": {
                "myrakine": "meerakine",
                "myra": "meera",
                "paradisespirit": "paradise spirit"
            },
            "word_replacements": {
                "afk": "A F K",
                "brb": "B R B",
                "gtg": "G T G",
                "myra": "meera",
                "myrakine": "meerakine",
                "paradisespirit": "paradise spirit",
                "poi": "poi"
            }
        }

        self.config.register_guild(**default_guild)

        # Default user configuration
        default_user = {
            "tts_enabled": False,
            "voice": "Brian"
        }
        self.config.register_user(**default_user)

        default_bot = {
            "statistics": False
        }

        self.config.register_global(**default_bot)

        # App commands
        self.blacklist_add_app = discord.app_commands.ContextMenu(
            name="Blacklist from TTS",
            callback=self.blacklist_add
        )

        self.blacklist_remove_app = discord.app_commands.ContextMenu(
            name="Remove from TTS blacklist", callback=self.blacklist_remove
        )

        # Make both commands Guild Only
        self.blacklist_add_app.guild_only = True
        self.blacklist_remove_app.guild_only = True

    def cog_load(self):
        # Load app commands when the cog is loaded
        self.bot.tree.add_command(self.blacklist_add_app)
        self.bot.tree.add_command(self.blacklist_remove_app)

    def cog_unload(self):
        # Unload app commands when unloading cog
        self.bot.tree.remove_command(self.blacklist_add_app.name, type=self.blacklist_add_app.type)
        self.bot.tree.remove_command(self.blacklist_remove_app.name, type=self.blacklist_remove_app.type)

    def __unload(self):
        lavalink.unregister_event_listener(self.lavalink_events)
        file_manager.cleanup_audio(self)

    tts_settings = app_commands.Group(name="tts_settings", description="TTS Settings", guild_only=True)

    @tts_settings.command(name="set_voice", description="Set the TTS voice for a user.")
    @app_commands.guild_only()
    async def tts_set_voice(self, interaction: discord.Interaction, user: discord.Member, voice: str):

        log.info(f"Setting TTS voice for {user} to {voice}")

        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        await self.config.user(user).voice.set(voice)
        await interaction.response.send_message(f"Set TTS voice for {user.mention} to `{voice}`.", ephemeral=True)

    @tts_settings.command(name="max_message_length", description="The maximum length of a TTS message.")
    @app_commands.guild_only()
    async def tts_max_message_length(self, interaction: discord.Interaction, length: int):
        await self.config.guild(interaction.guild).max_message_length.set(length)
        await interaction.response.send_message(f"Set the maximum message length to {length} characters.")

    @tts_settings.command(name="repeated_word_percentage",
                          description="The percentage of repeated words in a message for it to be filtered.")
    @app_commands.guild_only()
    async def tts_repeated_word_percentage(self, interaction: discord.Interaction, percentage: int):
        await self.config.guild(interaction.guild).repeated_word_percentage.set(percentage)
        await interaction.response.send_message(f"Set the repeated word percentage to {percentage}%.")

    @tts_settings.command(name="max_word_length", description="The maximum length of a word for it to be filtered.")
    @app_commands.guild_only()
    async def tts_max_word_length(self, interaction: discord.Interaction, length: int):
        await self.config.guild(interaction.guild).max_word_length.set(length)
        await interaction.response.send_message(f"Set the maximum word length to {length} characters.")

    @tts_settings.command(name="say_name", description="Whether to say the name of the user who sent the message.")
    @app_commands.guild_only()
    async def tts_say_name(self, interaction: discord.Interaction, say_name: bool):
        await self.config.guild(interaction.guild).say_name.set(say_name)
        await interaction.response.send_message(f"Set say name to {say_name}.")

    @tts_settings.command(name="add_word_substitution", description="Add a word substitution")
    @app_commands.guild_only()
    async def tts_add_name_substitution(self, interaction: discord.Interaction, source: str, substitution: str):
        words = await self.config.guild(interaction.guild).word_replacements()
        if source not in words.keys():
            words[source] = substitution
            await self.config.guild(interaction.guild).word_replacements.set(words)
            await interaction.response.send_message(f"Added word substiution `{source}`:`{substitution}` to word "
                                                    f"replacements.")
        else:
            await interaction.response.send_message(f"Substitution already exists for `{source}`")

    @tts_settings.command(name="remove_word_substitution", description="Remove a word substitution")
    @app_commands.guild_only()
    async def remove_word_substitution(self, interaction: discord.Interaction, source: str):
        words = await self.config.guild(interaction.guild).word_replacements()
        if source in words.keys():
            words.pop(source)
            await self.config.guild(interaction.guild).word_replacements.set(words)
            await interaction.response.send_message(f"Removed word substitution for word `{source}`")
        else:
            await interaction.response.send_message(f"`{source}` does not have a word substitution!")

    @tts_settings.command(name="add_name_substitution", description="Add a name substitution")
    @app_commands.guild_only()
    async def tts_add_name_substitution(self, interaction: discord.Interaction, source: str, substitution: str):
        words = await self.config.guild(interaction.guild).name_replacements()
        if source not in words.keys():
            words[source] = substitution
            await self.config.guild(interaction.guild).name_replacements.set(words)
            await interaction.response.send_message(f"Added name substitution `{source}`:`{substitution}` to name "
                                                    f"replacements.")
        else:
            await interaction.response.send_message(f"Name substitution already exists for `{source}`")

    @tts_settings.command(name="remove_name_substitution", description="Remove a name substitution")
    @app_commands.guild_only()
    async def remove_name_substitution(self, interaction: discord.Interaction, source: str):
        words = await self.config.guild(interaction.guild).name_replacements()
        if source in words.keys():
            words.pop(source)
            await self.config.guild(interaction.guild).name_replacements.set(words)
            await interaction.response.send_message(f"Removed word substitution for name `{source}`")
        else:
            await interaction.response.send_message(f"`{source}` does not have a name substitution!")

    @tts_settings.command(name="statistics", description="Enable statistic logging")
    @app_commands.guild_only()
    async def statistic_logging(self, interaction: discord.Interaction, enable: bool):
        if enable:
            await self.config.statistics.set(True)
            await interaction.response.send_message("Enabled statistics logging.")
        else:
            await self.config.statistics.set(False)
            await interaction.response.send_message("Disabled statistics logging.")

    @tts_settings.command(name="show", description="Show current settings.")
    @app_commands.guild_only()
    async def tts_show(self, interaction: discord.Interaction):
        settings = await self.config.guild(interaction.guild).all()
        settings_str = "## Current TTS Settings \n"
        for setting, value in settings.items():
            match setting:
                case "say_name":
                    settings_str += f"**Say Sender Name Before Message**: `{value}`\n"
                case "whitelisted_channels":
                    channels = ""
                    for channel in value:
                        if (channel is not None) and (interaction.guild.get_channel(channel) is not None):
                            channels += f" {interaction.guild.get_channel(channel).mention},"
                        else:
                            # Remove the channel from the list
                            channel_list = await self.config.guild(interaction.guild).whitelisted_channels()
                            channel_list.remove(channel)
                            await self.config.guild(interaction.guild).whitelisted_channels.set(channel_list)

                    settings_str += f"**Whitelisted Channels**:{channels} \n"
                case "blacklisted_users":
                    users = ""
                    for user in value:
                        users += f" {interaction.guild.get_member(user).mention},"
                    settings_str += f"**Blacklisted TTS Users**:{users} \n"
                case "max_message_length":
                    settings_str += f"**Maximum Message Length**: `{value}` characters\n"
                case "max_word_length":
                    settings_str += f"**Maximum Word Length**: `{value}` characters\n"
                case "repeated_word_percentage":
                    settings_str += f"**Maximum Repeated Words**: `{value}%`\n"
                case "global_tts_volume":
                    settings_str += f"**Global TTS Volume**: `{value}%`\n"
                case "name_replacements":
                    settings_str += "**Name Replacements** \n"
                    for text, replacement in value.items():
                        settings_str += f"- `{text}`: `{replacement}`\n"
                case "word_replacements":
                    settings_str += "**Word Replacements** \n"
                    for text, replacement in value.items():
                        settings_str += f"- `{text}`: `{replacement}`\n"
                case _:
                    settings_str += f"**{setting}**: `{value}`\n"

        await interaction.response.send_message(settings_str, allowed_mentions=discord.AllowedMentions(users=False))

    tts_blacklist = app_commands.Group(name="tts_blacklist", description="TTS Blacklist", guild_only=True)

    @tts_blacklist.command(name="add", description="Prevent a user from using the TTS")
    @app_commands.guild_only()
    async def blacklist_add_cmd(self, interaction: discord, user: discord.Member):
        await self.blacklist_add(self, interaction, user)

    async def blacklist_add(self, interaction: discord.Interaction, user: discord.Member):
        blacklist = await self.config.guild(interaction.guild).blacklisted_users()
        if user.id not in blacklist:
            blacklist.append(user.id)
            await self.config.guild(interaction.guild).blacklisted_users.set(blacklist)
            await interaction.response.send_message(f"Added user {user.mention} to blacklist!",
                                                    allowed_mentions=discord.AllowedMentions(users=False))
        else:
            await interaction.response.send_message(f"{user.mention} is already blacklisted!",
                                                    allowed_mentions=discord.AllowedMentions(users=False))

    @tts_blacklist.command(name="remove", description="Allow a  user to use TTS")
    @app_commands.guild_only()
    async def blacklist_remove_cmd(self, interaction: discord, user: discord.Member):
        await self.blacklist_remove(self, interaction, user)

    async def blacklist_remove(self, interaction: discord.Interaction, user: discord.Member):
        blacklist = await self.config.guild(interaction.guild).blacklisted_users()
        if user.id in blacklist:
            blacklist.remove(user.id)
            await self.config.guild(interaction.guild).blacklisted_users.set(blacklist)
            await interaction.response.send_message(f"Removed {user.mention} from blacklist!",
                                                    allowed_mentions=discord.AllowedMentions(users=False))
        else:
            await interaction.response.send_message(f"{user.mention} is not in the blacklist!",
                                                    allowed_mentions=discord.AllowedMentions(users=False))

    @tts_blacklist.command(name="list", description="List all blacklisted users")
    @app_commands.guild_only()
    async def blacklist_list(self, interaction: discord.Interaction):
        blacklist = await self.config.guild(interaction.guild).blacklisted_users()
        user_list = ""
        for user_id in blacklist:
            member = interaction.guild.get_member(user_id)
            user_list = user_list + member.display_name + "\n"

        if user_list == "":
            user_list = "None"

        await interaction.response.send_message(f"## TTS Blacklisted users:\n `{user_list}`")

    tts_channels = app_commands.Group(name="tts_channels", description="Whitelisted TTS channels", guild_only=True)

    @tts_channels.command(name="add_text", description="Add whitelisted channel for TTS text")
    @app_commands.guild_only()
    async def whitelist_addtext(self, interaction: discord.Interaction, channel: discord.TextChannel):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()
        whitelist.append(channel.id)
        await self.config.guild(interaction.guild).whitelisted_channels.set(whitelist)
        await interaction.response.send_message(f"Added channel {channel.mention} to TTS whitelist!")

    @tts_channels.command(name="add_vc", description="Add whitelisted voice channel for TTS text")
    @app_commands.guild_only()
    async def whitelist_addvc(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()
        whitelist.append(channel.id)
        await self.config.guild(interaction.guild).whitelisted_channels.set(whitelist)
        await interaction.response.send_message(f"Added channel {channel.mention} to TTS whitelist!")

    @tts_channels.command(name="remove_vc", description="Add whitelisted channel for TTS text")
    @app_commands.guild_only()
    async def whitelist_removevc(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()
        whitelist.remove(channel.id)
        await self.config.guild(interaction.guild).whitelisted_channels.set(whitelist)
        await interaction.response.send_message(f"Removed channel {channel.mention} from TTS whitelist!")

    @tts_channels.command(name="remove_text", description="Remove whitelisted channel for TTS text")
    @app_commands.guild_only()
    async def whitelist_removetext(self, interaction: discord.Interaction, channel: discord.TextChannel):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()
        whitelist.remove(channel.id)
        await self.config.guild(interaction.guild).whitelisted_channels.set(whitelist)
        await interaction.response.send_message(f"Removed channel {channel.mention} from TTS whitelist!")

    @tts_channels.command(name="list", description="List whitelisted channels")
    @app_commands.guild_only()
    async def whitelist_list(self, interaction: discord.Interaction):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()

        message = "Whitelisted TTS Channels: "
        for channel_id in whitelist:
            message += "\n" + interaction.guild.get_channel(channel_id).mention

        await interaction.response.send_message(message)

    @app_commands.command()
    @app_commands.guild_only()
    async def skip_tts(self, interaction: discord.Interaction):
        """
        Skip the current TTS message.
        """
        if interaction.user.voice is not None:
            blacklist = await self.config.guild(interaction.guild).blacklisted_users()
            if interaction.user.id not in blacklist:
                try:
                    await audio_manager.skip_tts(self)
                    await interaction.response.send_message("Skipped TTS message!", delete_after=5)
                except RuntimeError as err:
                    await interaction.response.send_message(err, delete_after=5)

    @app_commands.command()
    @app_commands.guild_only()
    async def tts_volume(self, interaction: discord.Interaction, volume: int):
        """
        Set the TTS volume.
        """
        if interaction.user.voice is not None:
            blacklist = await self.config.guild(interaction.guild).blacklisted_users()
            if interaction.user.id not in blacklist:
                try:
                    await self.config.guild(interaction.guild).global_tts_volume.set(volume)
                    await interaction.response.send_message(f"Set global TTS volume to `{volume}%`!")
                except RuntimeError as err:
                    await interaction.response.send_message(err)

    @app_commands.command()
    @app_commands.describe(voice="The TTS voice you wish to use.")
    @app_commands.choices(voice=[
        app_commands.Choice(name="Brian (🇬🇧)", value="Brian"),
        app_commands.Choice(name="Amy (🇬🇧)", value="Amy"),
        app_commands.Choice(name="Joey (🇺🇸)", value="Joey"),
        app_commands.Choice(name="Joanna (🇺🇸)", value="Joanna"),
        app_commands.Choice(name="Extra 🌎", value="Extra"),
        app_commands.Choice(name="Disable ❌", value="disable")
    ])
    @app_commands.describe(extra="Additional voices")
    @app_commands.choices(extra=[
        app_commands.Choice(name="Geraint (🏴󠁧󠁢󠁷󠁬󠁳󠁿)", value="Geraint"),
        app_commands.Choice(name="Salli (🇺🇸)", value="Salli"),
        app_commands.Choice(name="Matthew (🇺🇸)", value="Matthew"),
        app_commands.Choice(name="Justin (🇺🇸)", value="Justin"),
        app_commands.Choice(name="Ivy (🇺🇸)", value="Ivy"),
        app_commands.Choice(name="Auditi (🇮🇴)", value="Auditi"),
        app_commands.Choice(name="Emma (🇬🇧)", value="Emma"),
        app_commands.Choice(name="Russell (🇦🇺)", value="Russell"),
        app_commands.Choice(name="Nicole (🇦🇺)", value="Nicole"),
        app_commands.Choice(name="Hans (🇩🇪)", value="Hans"),
        app_commands.Choice(name="Ruben (🇳🇱)", value="Ruben"),
        app_commands.Choice(name="Lotte (🇳🇱)", value="Lotte"),
    ])
    @app_commands.guild_only()
    async def tts_voice(self, interaction: discord.Interaction,
                        voice: app_commands.Choice[str],
                        extra: app_commands.Choice[str] = None):
        """
        Enable TTS for the current user.
        """

        # Check if the user is blacklisted
        blacklist = await self.config.guild(interaction.guild).blacklisted_users()
        if interaction.user.id in blacklist:
            return

        # Check if User is not in a voice channel
        if interaction.user.voice is None:
            await interaction.response.send_message("You must be in a voice channel to use TTS. ❌", ephemeral=True)
            return

        if voice.value == "Extra":
            if extra is not None:
                voice = extra
            else:
                await interaction.response.send_message("You must select a voice to use TTS. ❌", ephemeral=True)
                return

        # If the user has TTS disabled
        if not await self.config.user(interaction.user).tts_enabled():
            # If the user has disabled TTS and wants to disable it
            if voice.value == "disable":
                await interaction.response.send_message("TTS Was already disabled for you! ❌", ephemeral=True)
                return
            # Enable TTS for the user and set the voice
            else:
                await self.config.user(interaction.user).voice.set(voice.value)
                await self.config.user(interaction.user).tts_enabled.set(True)

                await interaction.response.send_message(f"You have enabled TTS and sound like `{voice.value}`. \n"
                                                        f"Any messages you type in the voice channel text channels or no-mic"
                                                        f" will be read out. ✅", ephemeral=True)
                return

        # If the user has TTS enabled
        else:
            # If the user has TTS enabled and wants to disable it
            if voice.value == "disable":

                await self.config.user(interaction.user).tts_enabled.set(False)
                await interaction.response.send_message("Disabled TTS! ❌", ephemeral=True)
                return

            # if the user has TTS enabled and wants to change the voice
            else:
                await self.config.user(interaction.user).voice.set(voice.value)
                await interaction.response.send_message(f"You have changed your TTS voice to `{voice.value}`. \n"
                                                        f"Any messages you type in the voice channel text channels or no-mic"
                                                        f" will be read out. ✅", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        # If the channel is not whitelisted
        if message.channel.id not in await self.config.guild(message.guild).whitelisted_channels():
            return

        # If the message author is blacklisted
        if message.author.id in await self.config.guild(message.guild).blacklisted_users():
            return

        # If the message author has TTS enabled
        if await self.config.user(message.author).tts_enabled():
            # If the user is not in a voice channel
            if message.author.voice is None:
                await message.reply("You have left a voice channel, TTS has been disabled for you.", delete_after=10)
                await self.config.user(message.author).tts_enabled.set(False)
                return

            # Generate the TTS message and play it
            await tts_api.generate_tts(self, message)

    async def lavalink_events(self, player, event: lavalink.LavalinkEvents, extra):

        # Track end event.
        if event == lavalink.LavalinkEvents.TRACK_END:

            if self.current_track is None:
                return

            if self.current_track.track_identifier in self.tts_queue:
                # The track that just ended was a tts track.
                self.tts_queue.remove(self.current_track.track_identifier)
                await file_manager.delete_audio(self.current_track.uri)

        # Track start event.
        if event == lavalink.LavalinkEvents.TRACK_START:
            self.current_track = player.current

            if self.last_non_tts_track is not None:
                if player.current.track_identifier == self.last_non_tts_track[0].track_identifier:
                    # The track that just started was not a tts track, pause it and seek to where it was before.
                    await player.pause()
                    await player.seek(self.last_non_tts_track[1])

                    # Set the player volume to the same as we had when playing the previous track
                    await player.set_volume(self.last_non_tts_track[3])

                    # Check if the track was paused before we played TTS
                    if not self.last_non_tts_track[2]:
                        # Unpause it if needed
                        await player.pause(False)

                    # Clear the non-tts track queue
                    self.last_non_tts_track = None

        if event == lavalink.LavalinkEvents.QUEUE_END:
            # The queue has ended, cleanup the tts queue.
            self.tts_queue.clear()
            self.current_track = None

        if event == lavalink.LavalinkEvents.TRACK_STUCK:
            # The track has become stuck, if it is a tts track, remove it from the tts queue and the regular queue,
            # then delete.
            if self.current_track.track_identifier in self.tts_queue:
                if self.current_track in player.queue:
                    await player.queue.remove(self.current_track)
                await audio_manager.delete_file_and_remove(self, self.current_track)

        if event == lavalink.LavalinkEvents.TRACK_EXCEPTION:
            # The track has thrown an exception, if it is a tts track, remove it from the tts queue, and remove it
            # from the regular queue.
            if self.current_track.track_identifier in self.tts_queue:
                if self.current_track in player.queue:
                    await player.queue.remove(self.current_track)
                await audio_manager.delete_file_and_remove(self, self.current_track)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
