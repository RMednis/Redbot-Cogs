import os
import urllib
import uuid
import logging
import aiohttp

log = logging.getLogger("red.mednis-cogs.poitranslator.file_manager")


async def download_audio(self, voice: str, text: str):
    """
    Downloads audio from the tts api.
    """

    # Encode the text to be URL safe
    text = urllib.parse.quote_plus(text)
    voice = urllib.parse.quote_plus(voice)

    if await self.config.local_api():
        # Depending on the voice, we can use a local voice API instead of the cloud API
        local_voices = await self.config.local_voices()

        if voice.lower() in local_voices:
            voice = local_voices[voice.lower()]
            voice = urllib.parse.quote_plus(voice)

            url = await self.config.local_api_url()
            url= url.format(voice=voice, text=text)

            file_path = f"{self.audio_file_name}{uuid.uuid4()}.wav"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:

                    # Check if the request returns an audio file
                    if response.headers.get("content-type") != "audio/wav":
                        log.error(f"Was expecting a wav file, got ({response.headers.get('content-type')})")
                        log.error(f"Response: {await response.json()}")

                    # Save the audio file
                    with open(file_path, 'wb') as file:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            file.write(chunk)

                    await send_voice_statistics(self, text, voice, "local", response.status)
            return file_path

    # Use the cloud API
    url = await self.config.public_api_url()
    url = url.format(voice=voice, text=text)

    file_path = f"{self.audio_file_name}{uuid.uuid4()}.mp3"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:

            # Check if the request returns an audio file
            if response.headers.get("content-type") != "audio/mp3":
                log.error("Failed to download audio file.")

                raise RuntimeError("Failed to download audio file.")

            # Save the audio file
            with open(file_path, "wb") as file:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    file.write(chunk)
            await send_voice_statistics(self, text, voice, "public", response.status)
    return file_path


def cleanup_audio(self):
    """
    Removes all .mp3 files from the audio folder.
    """

    log.info("Cleaning up audio files.")

    for file in os.listdir(self.cog_path):
        if file.endswith(".mp3"):
            os.remove(self.cog_path / file)
        if file.endswith(".wav"):
            os.remove(self.cog_path / file)


async def delete_audio(file_path: str):
    """
    Deletes the audio file.
    """
    os.remove(file_path)

async def send_voice_statistics(self, text, voice, server, code) -> None:
    statistics_event_data = {
        "voice": voice,
        "length": len(text),
        "message": text,
        "server": server,
        "code": code
    }

    self.bot.dispatch("statistics_event", "tts_backend", {}, statistics_event_data)