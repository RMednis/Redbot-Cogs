import logging
from collections import Counter

import discord
import re

from ttsengine import audio_manager, file_manager

log = logging.getLogger("red.mednis-cogs.poitranslator.text_filter")

async def generate_tts(self, message: discord.Message):
    text = await filter_message(self, message)

    if text == "":
        return

    else:
        if await self.config.guild(message.guild).say_name():
            if message.author.nick != "":
                name = message.author.nick
            else:
                name = message.author.display_name

            text = f"{name} says {text}"

    voice = await self.config.user(message.author).voice()
    file_path = await file_manager.download_audio(self, voice, text)
    await audio_manager.play_audio(self, message.author.voice.channel, file_path)



async def repeated_word_filter(self, text: str):
    # Tokenize the text into words
    words = text.split()

    # Count the occurrences of each word
    word_counts = Counter(words)

    # Calculate the percentage of repeating words
    total_unique_words = len(word_counts)
    total_words = len(words)
    repeating_words = total_words - total_unique_words
    repeating_word_percentage = (repeating_words / total_words) * 100

    return repeating_word_percentage

async def long_word_filter(self, text: str, length):
    words = text.split()

    for word in words:
        if len(word) > length:
            return True

    return False
async def mention_filter(self, text: str, guild: discord.Guild):
    mentions = re.findall(r"<@!?\d+>", text)
    for mention in mentions:
        # Extract the user ID from the mention
        user_id = int(re.findall(r"\d+", mention)[0])

        # Retrieve the user object using the user ID
        user = guild.get_member(user_id)

        # Replace the mention with the user's regular name
        if user:
            if user.nick:
                name = user.nick
            else:
                name = user.display_name

            text = text.replace(mention, f"to {name}")

    return text

async def link_filter(self, text: str):
    # Regular expression pattern to match URLs
    url_pattern = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    # Remove URLs from the text
    text_without_links = re.sub(url_pattern, 'Link', text)

    return text_without_links


async def filter_message(self, text: discord.Message):

    # Config settings
    max_message_length = await self.config.guild(text.guild).max_message_length()
    max_word_length = await self.config.guild(text.guild).max_word_length()
    repeated_word_percentage = await self.config.guild(text.guild).repeated_word_percentage()



    filtered = text.content
    log.info(f"Filtering message: {text}")
    # Remove random spaces
    filtered = filtered.strip()

    # Clear message if it contains a command
    if filtered.startswith("."):
        return ""

    if len(filtered) == 0:
        return ""

    # Clear mesaage if it contains too many repeated words
    log.info(f"Repeated word percentage: {await repeated_word_filter(self, filtered)}")
    if await repeated_word_filter(self, filtered) > repeated_word_percentage:
        return ""

    # Replace mentions with the user's name
    filtered = await mention_filter(self, filtered, text.guild)

    # Remove links
    filtered = await link_filter(self, filtered)

    # Clear message if it is contains too long of a word
    if await long_word_filter(self, filtered, max_word_length):
        return ""

    # Limit the message length
    filtered = filtered[:max_message_length]

    return filtered
