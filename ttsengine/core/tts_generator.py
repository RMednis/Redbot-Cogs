import logging
import time

import discord

from ttsengine.core import audio_manager, file_manager, text_filter
from ttsengine.core.base import TTSBase
from ttsengine.core.settings import TTSGuildSettings

log = logging.getLogger("red.mednis-cogs.poitranslator.tts_generator")


async def generate_tts(self: TTSBase, message: discord.Message):

    tts_guild_settings = await TTSGuildSettings.from_config(self.config, message.guild)

    ttsmessage = await text_filter.filter_and_format_message(message, tts_guild_settings)

    if ttsmessage is None:
        log.info(f"Message from user {message.author.id} was filtered and will not be converted to TTS.")
        return

    voice = await self.config.user(message.author).voice()

    try:
        if await self.config.statistics():

            # Start timing the API request
            start = time.perf_counter()

            # Do the API request
            file_path = await file_manager.download_audio(self, voice, ttsmessage.text)

            # Calculate the API latency
            api_latency = time.perf_counter() - start
            # Send the API statistics
            await send_api_statistics(self, message, ttsmessage.text, api_latency, voice)

            if api_latency > 2:
                log.warning(f"API request took {api_latency} seconds for user {message.author.id}.\
                 That is over 2 seconds, dropping the message.")
                return

        else:
            file_path = await file_manager.download_audio(self, voice, ttsmessage.text)
    except RuntimeError:
        # We had an error downloading the audio, lets reset the used voice to the default
        log.error(f"API request failed for user {message.author.id} with voice {voice}, resetting to default voice.")
        await self.config.user(message.author).voice.set("Brian")
        try:
            file_path = await file_manager.download_audio(self, "Brian", ttsmessage.text)
        except RuntimeError:
            log.error("!! Failed to download audio file after resetting voice to default, is the TTS API down? !!")
            return

    try:
        await audio_manager.play_audio(self, message.author.voice.channel, file_path,
                                       tts_guild_settings.global_tts_volume, ttsmessage.track_name)
    except RuntimeError:
        # Attempt to reset the lavalink connection
        await audio_manager.reconnect_ll(self, message.author.voice.channel)
        log.info("Reconnecting lavalink to a VC")

        try:
            await audio_manager.play_audio(self, message.author.voice.channel, file_path,
                                           tts_guild_settings.global_tts_volume, ttsmessage.track_name)
        except RuntimeError as err:
            log.error("Failed to (re)connect LavaLink to a VC")
            log.error(err)


async def send_api_statistics(self: TTSBase, message, text, api_latency, voice) -> None:
    statistics_event_tags = {
        "guild_id": message.guild.id,
        "user_id": message.author.id,
        "voice": voice
    }
    statistics_event_data = {
        "length": len(text),
        "latency": api_latency,
    }

    self.bot.dispatch("statistics_event", "tts_request", statistics_event_tags, statistics_event_data)
