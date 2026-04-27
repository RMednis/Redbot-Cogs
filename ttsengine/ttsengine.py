import logging
from datetime import datetime, timezone
from typing import Literal

import discord
import lavalink
from discord import app_commands

from redbot.core import commands, data_manager
from redbot.core.bot import Red
from redbot.core.config import Config

from ttsengine.core import audio_manager, file_manager, tts_generator

# Import command classes
from ttsengine.commands.blacklist import BlacklistCommands
from ttsengine.commands.settings import SettingsCommands
from ttsengine.commands.tts import TTSCommands

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("red.mednis-cogs.poitranslator.main")

cooldown = 10 * 60 # 10 minute cooldown between message to show alerts again


def is_within_time(last_message_time: str, time=5 * 60) -> bool:
    """
    Check if the users last message was within a specified time.
    """

    # If the last message time is not set, return False
    if last_message_time == "":
        return False

    last_message_time = datetime.fromisoformat(last_message_time)

    # Check if the last TTS message was within a specified time.
    if (datetime.now(timezone.utc) - last_message_time).total_seconds() < time:
        return True

    return False


async def manage_guild_check(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.manage_guild


class TTSEngine(TTSCommands, BlacklistCommands, SettingsCommands, commands.Cog):
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
            },
            "word_replacements": {
            },

            # Command prefixes
            "command_prefixes": []
        }

        self.config.register_guild(**default_guild)

        # Default user configuration
        default_user = {
            "last_tts_message_time": "",
            "tts_enabled": False,
            "warning_summon": False,
            "warning_notts": False,
            "voice": "Brian"
        }
        self.config.register_user(**default_user)

        default_bot = {
            "regular_voices": [
                {"name": "Brian (🇬🇧)", "value": "Brian"},
                {"name": "Amy (🇬🇧)", "value": "Amy"},
                {"name": "Joey (🇺🇸)", "value": "Joey"},
                {"name": "Joanna (🇺🇸)", "value": "Joanna"},
                {"name": "Extra 🌎", "value": "Extra"},
                {"name": "Disable ❌", "value": "disable"}
            ],
            "extra_voices": [
                {"name": "Geraint (🏴)", "value": "Geraint"},
                {"name": "Salli (🇺🇸)", "value": "Salli"},
                {"name": "Matthew (🇺🇸)", "value": "Matthew"},
                {"name": "Justin (🇺🇸)", "value": "Justin"},
                {"name": "Ivy (🇺🇸)", "value": "Ivy"},
                {"name": "Auditi (🇮🇴)", "value": "Auditi"},
                {"name": "Emma (🇬🇧)", "value": "Emma"},
                {"name": "Russell (🇦🇺)", "value": "Russell"},
                {"name": "Nicole (🇦🇺)", "value": "Nicole"},
                {"name": "Hans (🇩🇪)", "value": "Hans"},
                {"name": "Ruben (🇳🇱)", "value": "Ruben"},
                {"name": "Lotte (🇳🇱)", "value": "Lotte"},
            ],
            "statistics": False,
            "local_api": False,
            "local_voices": {},
            "local_api_url": "",
            "public_api_url": "https://api.streamelements.com/kappa/v2/speech?voice={voice}&text={text}"
        }

        self.config.register_global(**default_bot)

        # App commands
        self.blacklist_add_app = discord.app_commands.ContextMenu(
            name="Blacklist from TTS",
            callback=self.blacklist_add
        )

        self.blacklist_add_app.add_check(manage_guild_check)

        self.blacklist_remove_app = discord.app_commands.ContextMenu(
            name="Remove from TTS blacklist", callback=self.blacklist_remove
        )

        self.blacklist_remove_app.add_check(manage_guild_check)

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
        lavalink.unregister_event_listener(self.lavalink_events)
        file_manager.cleanup_audio(self)

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

        # Store the previous tts mesasge time
        last_message_time = await self.config.user(message.author).last_tts_message_time()

        # Update the last TTS message time
        await self.config.user(message.author).last_tts_message_time.set(datetime.now(timezone.utc).isoformat())

        # If the message author has TTS enabled
        if await self.config.user(message.author).tts_enabled():
            # If the user is not in a voice channel
            if message.author.voice is None:

                # Check if the user has been warned about not being in a voice channel
                if not await self.config.user(message.author).warning_notts() or not is_within_time(last_message_time):

                    # Warn the user that they are not in a voice channel
                    await message.reply("❌ You are not in a VC, your messages will not be read out until you join."
                                        , delete_after = 10)
                    await self.config.user(message.author).warning_notts.set(True)

                return

            voice_clients = discord.utils.get(self.bot.voice_clients, guild=message.guild)

            # If the bot is not connected to a voice channel or in the same voice channel as the user
            if voice_clients is None or voice_clients.channel == message.author.voice.channel:

                # Reset the warning flags
                await self.config.user(message.author).warning_summon.set(False)
                await self.config.user(message.author).warning_notts.set(False)

                # Generate the TTS message and play it
                await tts_generator.generate_tts(self, message)

            # If the bot is connected to a different voice channel
            elif voice_clients.channel != message.author.voice.channel:

                if not await self.config.user(message.author).warning_summon() or not is_within_time(last_message_time):

                    # If the user has not been warned about the bot being in a different voice channel
                    await message.reply(f"❌ **I'm already in {voice_clients.channel.mention}.** \n"
                                        f"Please use the `/summon` command to bring me here.\n"
                                        f"_Also, make sure the people in the other channel are okay with it :D_",
                                        delete_after = 30)
                    await self.config.user(message.author).warning_summon.set(True)
                    return

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
                if player.current.track_identifier == self.last_non_tts_track.track.track_identifier:
                    # The track that just started was not a tts track, pause it and seek to where it was before.
                    await player.pause()
                    await player.seek(self.last_non_tts_track.position)

                    # Set the player volume to the same as we had when playing the previous track
                    await player.set_volume(self.last_non_tts_track.volume)

                    # Check if the track was paused before we played TTS
                    if not self.last_non_tts_track.was_paused:
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
