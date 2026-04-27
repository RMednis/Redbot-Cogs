import logging
import random
import time

import discord

from ttsengine.core import audio_manager, file_manager, text_filter

log = logging.getLogger("red.mednis-cogs.poitranslator.text_filter")


async def generate_tts(self, message: discord.Message):
    text = await text_filter.filter_message(
      message.content,
      max_message_length=await self.config.guild(message.guild).max_message_length(),
      max_word_length=await self.config.guild(message.guild).max_word_length(),
      repeated_word_percentage=await self.config.guild(message.guild).repeated_word_percentage(),
      word_replacements=await self.config.guild(message.guild).word_replacements(),
      command_prefixes=await self.config.guild(message.guild).command_prefixes(),
      guild=message.guild
    )

    track_name = "TTS"

    track_volume = await self.config.guild(message.guild).global_tts_volume()
    name_replacements = await self.config.guild(message.guild).name_replacements()

    if await self.config.guild(message.guild).say_name():

        if message.author.nick:
            # Take the server nickname as preferable
            # Fix pronunciation of certain names
            name = text_filter.fixup_name(message.author.nick, name_replacements)

            # Set the track name to the nickname
            track_name = f"TTS from {message.author.nick}"
        else:
            # Fix pronunciation of certain names
            name = text_filter.fixup_name(message.author.display_name, name_replacements)

            # Set the track name to the display name
            track_name = f"TTS from {message.author.display_name}"

        if text == "" or text is None:
            # Message doesn't contain text or it got clobbered
            if not message.attachments:
                # Message is empty...
                return
            else:
                media_type = message.attachments[0].content_type.split("/", 1)[0]

                if media_type:
                    text = f"{name} sends {media_type}"
                else:
                    text = f"{name} sends media"
        else:
            if text == "Link":
                # Clobbered to Link

                # 1 in 1000 chance to say "sends zelda" instead of "sands link"
                random.seed(message.content)
                num = random.randint(1, 1000)

                if num == 1:
                    text = f"{name} sends zelda"
                else:
                    text = f"{name} sends link"

            else:
                # Regular message
                text = f"{name} says {text}"

            if message.attachments:
                log.info(message.attachments[0].content_type)
                media_type = message.attachments[0].content_type.split("/", 1)[0]
                if media_type:
                    text = text + f" with attached {media_type}"
                else:
                    text = text + " with attached media"

    voice = await self.config.user(message.author).voice()

    if not text:
        return

    try:
        if await self.config.statistics():
            # Start timing the API request
            start = time.perf_counter()

            # Do the API request
            file_path = await file_manager.download_audio(self, voice, text)

            # Calculate the API latency
            api_latency = time.perf_counter() - start
            # Send the API statistics
            await send_api_statistics(self, message, text, api_latency, voice)

            if api_latency > 2:
                log.warning(f"API request took {api_latency} seconds for user {message.author.id}.\
                 That is over 2 seconds, dropping the message.")
                return

        else:
            file_path = await file_manager.download_audio(self, voice, text)
    except RuntimeError:
        # We had an error downloading the audio, lets reset the used voice to the default
        log.error(f"API request failed for user {message.author.id} with voice {voice}, resetting to default voice.")
        await self.config.user(message.author).voice.set("Brian")
        try:
            file_path = await file_manager.download_audio(self, "Brian", text)
        except RuntimeError:
            log.error("!! Failed to download audio file after resetting voice to default, is the TTS API down? !!")
            return

    try:
        await audio_manager.play_audio(self, message.author.voice.channel, file_path, track_volume, track_name)
    except RuntimeError:
        # Attempt to reset the lavalink connection
        await audio_manager.reconnect_ll(self, message.author.voice.channel)
        log.info("Reconnecting lavalink to a VC")

        try:
            await audio_manager.play_audio(self, message.author.voice.channel, file_path, track_volume, track_name)
        except RuntimeError as err:
            log.error("Failed to (re)connect LavaLink to a VC")
            log.error(err)


async def send_api_statistics(self, message, text, api_latency, voice) -> None:
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
