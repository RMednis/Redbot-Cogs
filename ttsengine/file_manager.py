import os
import uuid
import logging
import aiohttp

log = logging.getLogger("red.mednis-cogs.poitranslator.file_manager")
async def download_audio(self, voice: str, text: str):
    """
    Downloads audio from the tts api.
    """
    url = f"https://api.streamelements.com/kappa/v2/speech?voice={voice}&text={text}"

    file_path = f"{self.audio_file_name}{uuid.uuid4()}.mp3"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            with open(file_path, "wb") as file:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    file.write(chunk)

    return file_path


def cleanup_audio(self):
    """
    Removes all .mp3 files from the audio folder.
    """

    log.info("Cleaning up audio files.")

    for file in os.listdir(self.cog_path):
        if file.endswith(".mp3"):
            os.remove(self.cog_path / file)


async def delete_audio(file_path: str):
    """
    Deletes the audio file.
    """
    os.remove(file_path)
