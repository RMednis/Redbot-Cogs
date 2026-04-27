import json
import io

import discord
import logging

from redbot.core import app_commands

from ttsengine.commands.base import TTSBase
import ttsengine.core.text_filter
from ttsengine.core import text_filter
from ttsengine.core.settings import TTSGuildSettings

log = logging.getLogger("red.mednis-cogs.poitranslator.settings_commands")

class SettingsCommands(TTSBase):
    tts_settings = app_commands.Group(name="tts_settings", description="TTS Settings", guild_only=True)

    @tts_settings.command(name="set_voice", description="Set the TTS voice for a user.")
    @app_commands.guild_only()
    async def tts_set_voice(self, interaction: discord.Interaction, user: discord.Member, voice: str):

        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        log.info(f"Setting TTS voice for {user} to {voice}")
        await self.config.user(user).voice.set(voice)
        await interaction.response.send_message(f"Set TTS voice for {user.mention} to `{voice}`.", ephemeral=True)

    @tts_settings.command(name="max_message_length", description="The maximum length of a TTS message.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tts_max_message_length(self, interaction: discord.Interaction, length: int):
        await self.config.guild(interaction.guild).max_message_length.set(length)
        await interaction.response.send_message(f"Set the maximum message length to {length} characters.")

    @tts_settings.command(name="repeated_word_percentage",
                          description="The percentage of repeated words in a message for it to be filtered.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tts_repeated_word_percentage(self, interaction: discord.Interaction, percentage: int):
        await self.config.guild(interaction.guild).repeated_word_percentage.set(percentage)
        await interaction.response.send_message(f"Set the repeated word percentage to {percentage}%.")

    @tts_settings.command(name="max_word_length", description="The maximum length of a word for it to be filtered.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tts_max_word_length(self, interaction: discord.Interaction, length: int):
        await self.config.guild(interaction.guild).max_word_length.set(length)
        await interaction.response.send_message(f"Set the maximum word length to {length} characters.")

    @tts_settings.command(name="say_name", description="Whether to say the name of the user who sent the message.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tts_say_name(self, interaction: discord.Interaction, say_name: bool):
        await self.config.guild(interaction.guild).say_name.set(say_name)
        await interaction.response.send_message(f"Set say name to {say_name}.")

    @tts_settings.command(name="add_word_substitution", description="Add a word substitution")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tts_add_word_substitution(self, interaction: discord.Interaction, source: str, substitution: str):
        words = await self.config.guild(interaction.guild).word_replacements()
        if source not in words.keys():
            words[source] = substitution
            await self.config.guild(interaction.guild).word_replacements.set(words)
            await interaction.response.send_message(f"Added word substitution `{source}`:`{substitution}` to word "
                                                    f"replacements.")
        else:
            await interaction.response.send_message(f"Substitution already exists for `{source}`")

    @tts_settings.command(name="remove_word_substitution", description="Remove a word substitution")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
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
    @app_commands.checks.has_permissions(manage_guild=True)
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
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_name_substitution(self, interaction: discord.Interaction, source: str):
        words = await self.config.guild(interaction.guild).name_replacements()
        if source in words.keys():
            words.pop(source)
            await self.config.guild(interaction.guild).name_replacements.set(words)
            await interaction.response.send_message(f"Removed name substitution for name `{source}`")
        else:
            await interaction.response.send_message(f"`{source}` does not have a name substitution!")

    @tts_settings.command(name="global", description="Export the current settings to a file.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def statistic_logging(self, interaction: discord.Interaction, file: discord.Attachment = None):

        await interaction.response.defer()
        if not interaction.user.id in self.bot.owner_ids:
            await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)
            return

        if file is None:
            json_response = {
                "regular_voices": await self.config.regular_voices(),
                "extra_voices": await self.config.extra_voices(),
                "statistics": await self.config.statistics(),
                "local_api": await self.config.local_api(),
                "local_voices": await self.config.local_voices(),
                "local_api_url": await self.config.local_api_url(),
                "public_api_url": await self.config.public_api_url()
            }
            json_bytes = io.BytesIO(json.dumps(json_response, indent=4).encode('utf-8'))
            tts_file = discord.File(json_bytes, filename="tts_settings.json")

            await interaction.followup.send("Here's the current global settings.\n"
                                            "Edit this file then run the command with the file attached.\n"
                                            "You can use `{voice}` and `{text}` as placeholders in the URL's!\n",
                                            file=tts_file, ephemeral=True)
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

    @tts_settings.command(name="debug_message", description="Debug a message to see how it would be processed by the TTS engine.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def debug_message(self, interaction: discord.Interaction, message: str,
                            voice_channel: discord.VoiceChannel = None,
                            text_channel: discord.TextChannel = None):

        if text_channel is not None:
            channel = text_channel
        elif voice_channel is not None:
            channel = voice_channel
        else:
            channel = interaction.channel

        try:
            message = await channel.fetch_message(int(message))
        except (discord.NotFound, ValueError):
            await interaction.response.send_message("Invalid message ID or message not found.", ephemeral=True)
            return

        await self._debug_tts_message(interaction, message)

    async def _debug_tts_message(self, interaction: discord.Interaction, message: discord.Message):
        tts_guild_settings = await TTSGuildSettings.from_config(self.config, message.guild)
        processed = await text_filter.filter_and_format_message(message, tts_guild_settings)

        if processed is None:
            result = "None (Message was filtered out and would not be sent to TTS)"
        else:
            result = processed.text

        await interaction.response.send_message(
            f"**Input Message:** ```{message.content}```\n"
            f"**Sent to TTS:** ```{result}```",
            ephemeral=True
        )

    @tts_settings.command(name="show", description="Show current settings.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
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
                    stale_ids = []
                    for channel in value:
                        resolved = interaction.guild.get_channel(channel)
                        if resolved:
                            channels += f" {resolved.mention},"
                        else:
                            stale_ids.append(channel)
                    if stale_ids:
                        cleaned = [cid for cid in value if cid not in stale_ids]
                        await self.config.guild(interaction.guild).whitelisted_channels.set(cleaned)
                    embed.add_field(name="Whitelisted Channels", value=channels or "`None`")

                case "blacklisted_users":
                    users = ""
                    stale_ids = []
                    for user in value:
                        member = interaction.guild.get_member(user)
                        if member:
                            users += f" {member.mention},"
                        else:
                            stale_ids.append(user)
                    if stale_ids:
                        cleaned = [uid for uid in value if uid not in stale_ids]
                        await self.config.guild(interaction.guild).blacklisted_users.set(cleaned)
                    embed.add_field(name="Blacklisted Users", value=users or "`None`")

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

                case "command_prefixes":
                    prefix_list = ""
                    for prefix in value:
                        prefix_list += f"{prefix}, "

                    if prefix_list == "":
                        prefix_list = "`None`"

                    general_settings += f"Ignored Command Prefixes: `{prefix_list}`\n"

                case _:
                    general_settings += f"{setting}: `{value}`\n"

        embed.insert_field_at(index=0, name="General Settings", value=general_settings, inline=False)

        message = await interaction.response.send_message(embed=embed,
                                                          allowed_mentions=discord.AllowedMentions(users=False))

    @tts_settings.command(name="add_command_prefix", description="Add a command prefix")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_command_prefix(self, interaction: discord.Interaction, prefix: str):
        prefixes = await self.config.guild(interaction.guild).command_prefixes()
        if prefix not in prefixes:
            prefixes.append(prefix)
            await self.config.guild(interaction.guild).command_prefixes.set(prefixes)
            await interaction.response.send_message(f"Added command prefix `{prefix}`")
        else:
            await interaction.response.send_message(f"Command prefix `{prefix}` already exists!")

    @tts_settings.command(name="remove_command_prefix", description="Remove a command prefix")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_command_prefix(self, interaction: discord.Interaction, prefix: str):
        prefixes = await self.config.guild(interaction.guild).command_prefixes()
        if prefix in prefixes:
            prefixes.remove(prefix)
            await self.config.guild(interaction.guild).command_prefixes.set(prefixes)
            await interaction.response.send_message(f"Removed command prefix `{prefix}`")
        else:
            await interaction.response.send_message(f"Command prefix `{prefix}` does not exist!")

    tts_channels = app_commands.Group(name="tts_channels", description="Whitelisted TTS channels", guild_only=True)

    @tts_channels.command(name="add_text", description="Add whitelisted channel for TTS text")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_addtext(self, interaction: discord.Interaction, channel: discord.TextChannel):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()

        if channel.id in whitelist:
            await interaction.response.send_message(f"{channel.mention} is already whitelisted!")
            return

        whitelist.append(channel.id)

        await self.config.guild(interaction.guild).whitelisted_channels.set(whitelist)
        await interaction.response.send_message(f"Added channel {channel.mention} to TTS whitelist!")

    @tts_channels.command(name="add_vc", description="Add whitelisted voice channel for TTS text")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_addvc(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()

        if channel.id in whitelist:
            await interaction.response.send_message(f"{channel.mention} is already whitelisted!")
            return

        whitelist.append(channel.id)
        await self.config.guild(interaction.guild).whitelisted_channels.set(whitelist)
        await interaction.response.send_message(f"Added channel {channel.mention} to TTS whitelist!")

    @tts_channels.command(name="remove_vc", description="Remove whitelisted voice channel for TTS text")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_removevc(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()

        if channel.id not in whitelist:
            await interaction.response.send_message(f"{channel.mention} is not in the whitelist!")
            return

        whitelist.remove(channel.id)
        await self.config.guild(interaction.guild).whitelisted_channels.set(whitelist)
        await interaction.response.send_message(f"Removed channel {channel.mention} from TTS whitelist!")

    @tts_channels.command(name="remove_text", description="Remove whitelisted channel for TTS text")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_removetext(self, interaction: discord.Interaction, channel: discord.TextChannel):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()

        if channel.id not in whitelist:
            await interaction.response.send_message(f"{channel.mention} is not in the whitelist!")
            return

        whitelist.remove(channel.id)
        await self.config.guild(interaction.guild).whitelisted_channels.set(whitelist)
        await interaction.response.send_message(f"Removed channel {channel.mention} from TTS whitelist!")

    @tts_channels.command(name="list", description="List whitelisted channels")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_list(self, interaction: discord.Interaction):
        whitelist = await self.config.guild(interaction.guild).whitelisted_channels()

        message = "Whitelisted TTS Channels:"
        stale_ids = []

        for channel_id in whitelist:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                message += f"\n{channel.mention}"
            else:
                stale_ids.append(channel_id)

        if stale_ids:
            cleaned = [cid for cid in whitelist if cid not in stale_ids]
            await self.config.guild(interaction.guild).whitelisted_channels.set(cleaned)

        await interaction.response.send_message(message)