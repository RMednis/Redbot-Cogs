import io
import json
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
            },
            "word_replacements": {
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

    @tts_settings.command(name="global", description="Export the current settings to a file.")
    @app_commands.guild_only()
    async def statistic_logging(self, interaction: discord.Interaction, file:discord.Attachment = None):

        await interaction.response.defer()
        if not interaction.user.id in self.bot.owner_ids:
            await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)
            return

        if file is None:
            json_reponse = {
                "regular_voices": await self.config.regular_voices(),
                "extra_voices": await self.config.extra_voices(),
                "statistics": await self.config.statistics(),
                "local_api": await self.config.local_api(),
                "local_voices": await self.config.local_voices(),
                "local_api_url": await self.config.local_api_url(),
                "public_api_url": await self.config.public_api_url()
            }
            json_bytes = io.BytesIO(json.dumps(json_reponse, indent=4).encode('utf-8'))
            tts_file = discord.File(json_bytes, filename="tts_settings.json")

            await interaction.followup.send("Here's the current global settings.\n"
                                              "Edit this file then run the command with the file attached.\n"
                                              "You can use `{voice}` and `{text}` as placeholders in the URL's!\n",
                                              file=tts_file ,ephemeral=True)
            return

        else:
            if "application/json" in file.content_type:

                # Try and parse the JSON file
                try:
                    # Required keys for the JSON file
                    required_keys = {
                        "regular_voices": list,
                        "extra_voices": list,
                        "statistics": bool,
                        "local_api": bool,
                        "local_voices": dict,
                        "local_api_url": str,
                        "public_api_url": str
                    }

                    # Read the file
                    file_object = await file.read()
                    settings = json.loads(file_object)

                    # Check if the required keys are in the file
                    for key, expected_type in required_keys.items():
                        if key not in settings:
                            await interaction.followup.send(
                                f"Missing required key: {key}", ephemeral=True
                            )
                            return
                        if not isinstance(settings[key], expected_type):
                            await interaction.followup.send(
                                f"Invalid type for key '{key}'. Expected {expected_type.__name__}.",
                                ephemeral=True
                            )
                            return
                        if expected_type == list:
                            for item in settings[key]:
                                if not isinstance(item, dict):
                                    await interaction.followup.send(
                                        f"Invalid type for key '{key}'. Expected list of dictionaries.",
                                        ephemeral=True
                                    )
                                    return

                    await self.config.regular_voices.set(settings["regular_voices"])
                    await self.config.extra_voices.set(settings["extra_voices"])
                    await self.config.statistics.set(settings["statistics"])
                    await self.config.local_api.set(settings["local_api"])
                    await self.config.local_voices.set(settings["local_voices"])
                    await self.config.local_api_url.set(settings["local_api_url"])
                    await self.config.public_api_url.set(settings["public_api_url"])

                    await interaction.followup.send("Settings file uploaded and saved!", ephemeral=True)

                except json.JSONDecodeError:
                    await interaction.followup.send("Invalid JSON file.", ephemeral=True)
                except Exception as e:
                    await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send("Invalid file format. Please upload a JSON file.", ephemeral=True)

    @tts_settings.command(name="show", description="Show current settings.")
    @app_commands.guild_only()
    async def tts_show(self, interaction: discord.Interaction):

        # Pull all the settings from the guild
        settings = await self.config.guild(interaction.guild).all()

        # Create an embed for the settings display
        embed = discord.Embed(title="Current TTS Settings", color=discord.Color.green())

        settings_str = "## Current TTS Settings \n"

        general_settings = ""

        for setting, value in settings.items():  # Go through all the setting options

            # Match settings for a custom output
            # Otherwise, just output the setting and value

            match setting:
                case "say_name":
                    general_settings += f"Say Sender Name Before Message: `{value}`\n"

                case "max_message_length":
                    general_settings += f"Maximum Message Length: `{value}` characters\n"

                case "max_word_length":
                    general_settings += f"Maximum Word Length: `{value}` characters\n"

                case "repeated_word_percentage":
                    general_settings += f"Maximum Repeated Words: `{value}%`\n"

                case "global_tts_volume":
                    general_settings += f"Global TTS Volume: `{value}%`\n"

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

                    embed.add_field(name="Whitelisted Channels", value=channels)

                case "blacklisted_users":
                    users = ""
                    for user in value:
                        users += f" {interaction.guild.get_member(user).mention},"

                    if users == "":
                        users = "`None`"

                    embed.add_field(name="Blacklisted Users", value=users)

                case "name_replacements":
                    replacement_list = ""
                    for text, replacement in value.items():
                        replacement_list += f"- `{text}`: `{replacement}`\n"
                    embed.add_field(name="Name Replacements", value=replacement_list, inline=False)

                case "word_replacements":
                    word_replacements = ""
                    for text, replacement in value.items():
                        word_replacements += f"- `{text}`: `{replacement}`\n"

                    embed.add_field(name="Word Replacements", value=word_replacements, inline=False)

                case _:
                    general_settings += f"{setting}: `{value}`\n"

        embed.insert_field_at(index=0, name="General Settings", value=general_settings, inline=False)

        message = await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(users=False))

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
    @app_commands.guild_only()
    @app_commands.describe(voice="The TTS voice you wish to use.")
    @app_commands.describe(extra="Extra voices not available in the regular list.")
    async def tts_voice(self, interaction: discord.Interaction,
                        voice: str,
                        extra: str = None):
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

        # Sanity check the options since autocomplete is not mandatory
        for voice_option in await self.config.regular_voices():
            if voice_option["value"] == voice:
                break
            elif voice_option["value"] == "disable":
                break
            elif voice_option["value"] == "Extra":
                break
        else:
            await interaction.response.send_message("Invalid voice selected. ❌", ephemeral=True)
            return

        # Sanity check the extra voice options
        if extra is not None:
            for voice_option in await self.config.extra_voices():
                if voice_option["value"] == extra:
                    break
            else:
                await interaction.response.send_message("Invalid extra voice selected. ❌", ephemeral=True)
                return

        if voice == "Extra":
            if extra is not None:
                voice = extra
            else:
                await interaction.response.send_message("You must select a voice to use TTS. ❌", ephemeral=True)
                return

        # If the user has TTS disabled
        if not await self.config.user(interaction.user).tts_enabled():
            # If the user has disabled TTS and wants to disable it
            if voice == "disable":
                await interaction.response.send_message("TTS Was already disabled for you! ❌", ephemeral=True)
                return
            # Enable TTS for the user and set the voice
            else:
                await self.config.user(interaction.user).voice.set(voice)
                await self.config.user(interaction.user).tts_enabled.set(True)

                await interaction.response.send_message(f"You have enabled TTS and sound like `{voice}`. \n"
                                                        f"Any messages you type in the voice channel text channels or no-mic"
                                                        f" will be read out. ✅", ephemeral=True)
                return

        # If the user has TTS enabled
        else:
            # If the user has TTS enabled and wants to disable it
            if voice == "disable":

                await self.config.user(interaction.user).tts_enabled.set(False)
                await interaction.response.send_message("Disabled TTS! ❌", ephemeral=True)
                return

            # if the user has TTS enabled and wants to change the voice
            else:
                await self.config.user(interaction.user).voice.set(voice)
                await interaction.response.send_message(f"You have changed your TTS voice to `{voice}`. \n"
                                                        f"Any messages you type in the voice channel text channels or no-mic"
                                                        f" will be read out. ✅", ephemeral=True)

    @tts_voice.autocomplete("voice")
    async def tts_voice_autocomplete(self, interaction: discord.Interaction, current: str):
        voices = await self.config.regular_voices()
        return [
            discord.app_commands.Choice(name=voice["name"], value=voice["value"])
            for voice in voices
            if current.lower() in voice["name"].lower()
        ]

    @tts_voice.autocomplete("extra")
    async def tts_extra_voice_autocomplete(self, interaction: discord.Interaction, current: str):
        extra_voices = await self.config.extra_voices()
        return [
            discord.app_commands.Choice(name=voice["name"], value=voice["value"])
            for voice in extra_voices
            if current.lower() in voice["name"].lower()
        ]

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
