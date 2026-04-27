import discord
import logging

from redbot.core import app_commands
from ttsengine.core import audio_manager

from ttsengine.core.base import TTSBase

log = logging.getLogger("red.mednis-cogs.poitranslator.tts_commands")

class TTSCommands(TTSBase):
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
    @app_commands.describe(volume="The global volume you wish to set (0-150).")
    async def tts_volume(self, interaction: discord.Interaction, volume: app_commands.Range[int, 0, 150]):
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
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def summon(self, interaction: discord.Interaction):
        """
        Summon the bot to your voice channel.
        """
        if interaction.user.voice is None:
            await interaction.response.send_message("❌ You must be in a voice channel to summon the bot.",
                                                    ephemeral=True)
            return

        # Check if the user is blacklisted
        blacklist = await self.config.guild(interaction.guild).blacklisted_users()
        if interaction.user.id in blacklist:
            return

        # Try to connect to the user's voice channel
        try:
            await audio_manager.connect_ll(self, interaction.user.voice.channel)
            await interaction.response.send_message(f" Connected to {interaction.user.voice.channel.mention}!",
                                                    ephemeral=True)
            await self.config.user(interaction.user).warning_summon.set(False)
        except RuntimeError as err:
            await interaction.response.send_message("❌ Failed to connect to your voice channel.", ephemeral=True)

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
            await interaction.response.send_message("❌ You must be in a voice channel to use TTS.", ephemeral=True)
            return

        # Sanity check the options since autocomplete is not mandatory
        for voice_option in await self.config.regular_voices():
            if voice_option["value"] == voice:
                break
        else:
            await interaction.response.send_message("❌ Invalid voice selected.", ephemeral=True)
            return

        # Sanity check the extra voice options
        if extra is not None:
            for voice_option in await self.config.extra_voices():
                if voice_option["value"] == extra:
                    break
            else:
                await interaction.response.send_message("❌ Invalid extra voice selected.", ephemeral=True)
                return

        if voice == "Extra":
            if extra is not None:
                voice = extra
            else:
                await interaction.response.send_message("❌ You must select a voice to use TTS.", ephemeral=True)
                return

        # If the user has TTS disabled
        if not await self.config.user(interaction.user).tts_enabled():
            # If the user has disabled TTS and wants to disable it
            if voice == "disable":
                await interaction.response.send_message("❌ TTS Was already disabled for you!", ephemeral=True)
                return
            # Enable TTS for the user and set the voice
            else:
                await self.config.user(interaction.user).voice.set(voice)
                await self.config.user(interaction.user).tts_enabled.set(True)

                await interaction.response.send_message(f"✅ You have enabled TTS and sound like `{voice}`. \n"
                                                        f"Any messages you type in the voice channel text channels or no-mic"
                                                        f" will be read out.", ephemeral=True)
                return

        # If the user has TTS enabled
        else:
            # If the user has TTS enabled and wants to disable it
            if voice == "disable":

                await self.config.user(interaction.user).tts_enabled.set(False)
                await interaction.response.send_message("❌ Disabled TTS!", ephemeral=True)
                return

            # if the user has TTS enabled and wants to change the voice
            else:
                await self.config.user(interaction.user).voice.set(voice)
                await interaction.response.send_message(f"✅ You have changed your TTS voice to `{voice}`. \n"
                                                        f"Any messages you type in the voice channel text channels or no-mic"
                                                        f" will be read out.", ephemeral=True)

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