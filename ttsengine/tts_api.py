import logging
from collections import Counter
import random

import discord
import re

from ttsengine import audio_manager, file_manager

log = logging.getLogger("red.mednis-cogs.poitranslator.text_filter")

patterns_to_replace = {
    "afk": "A F K",
    "brb": "B R B",
    "gtg": "G T G",
    "myra": "mira",
    "¯\\_(ツ)_/¯": "shrug",
    "myrakine": "meerakine",
    "paradisespirit": "paradise spirit",
    "poi": "poi"
}

compiled_patterns = {re.compile(r'\b' + re.escape(pattern) + r'\b(?!\w)', flags=re.IGNORECASE): replacement
                     for pattern, replacement in patterns_to_replace.items()}

async def generate_tts(self, message: discord.Message):
    text = await filter_message(self, message)
    track_name = "TTS"

    track_volume = await self.config.guild(message.guild).global_tts_volume()

    if await self.config.guild(message.guild).say_name():

        if message.author.nick:
            # Take the server nickname as preferable
            # Fix pronunciation of certain names
            name = await fixup_name(message.author.nick)

            # Set the track name to the nickname
            track_name = f"TTS from {message.author.nick}"
        else:
            # Fix pronunciation of certain names
            name = await fixup_name(message.author.display_name)

            # Set the track name to the display name
            track_name = f"TTS from {message.author.display_name}"

        if text == "":
            # Message doesn't contain text or it got clobbered
            if not message.attachments:
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

                # 1 in 10000 chance to say "sends zelda" instead of "sands link"
                num = random.randint(1, 10000)

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
    file_path = await file_manager.download_audio(self, voice, text)

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


async def repeated_word_filter(text: str):
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


async def long_word_filter(text: str, length):
    words = text.split()

    for word in words:
        if len(word) > length:
            return True

    return False


async def mention_filter(text: str, guild: discord.Guild):
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


async def emoji_textifier(text: str):
    emote_pattern = r'<a?:(\w+):\d+>'
    text = re.sub(emote_pattern, lambda match: match.group(1), text)

    return text


async def filter_spoilers(text: str):
    spoiler_pattern = r'\|\|(.*?)\|\|'
    text = re.sub(spoiler_pattern, "spoiler", text)

    return text


async def link_filter(text: str):
    # Regular expression pattern to match URLs
    url_pattern = re.compile(r"https?://(?:[a-zA-Z0-9$-_@.&+]|[!*\\(),]|(?:%[0-9a-fA-F]{2}))+")

    # Remove URLs from the text
    text_without_links = re.sub(url_pattern, 'Link', text)

    return text_without_links


async def remove_characters(text: str):
    # Slash command pauses the tts for a bit
    text = text.replace("/", " ")

    # Underscores are used to imply italics, we should ignore them
    text = text.replace("_", " ")

    return text


async def fixup_text(text: str):
    # Replace certain message patterns with more readable ones
    for regex_pattern, replacement in compiled_patterns.items():
        text = regex_pattern.sub(replacement, text)

    return text


async def fixup_name(text: str):
    # Fix pronunciation of certain names
    patterns_to_replace = {
        "myrakine": "meerakine",
        "myra": "mira",
        "paradisespirit": "paradise spirit"
    }

    # Replace the patterns
    for pattern, replacement in patterns_to_replace.items():

        text = text.lower().replace(pattern, replacement)

    return text


async def filter_message(self, text: discord.Message):
    # Config settings
    max_message_length = await self.config.guild(text.guild).max_message_length()
    max_word_length = await self.config.guild(text.guild).max_word_length()
    repeated_word_percentage = await self.config.guild(text.guild).repeated_word_percentage()

    filtered = text.content
    # log.info(f"Filtering message: {text}")
    # Remove random spaces
    filtered = filtered.strip()

    # Clear message if it contains a command
    if filtered.startswith("."):
        return ""

    if len(filtered) == 0:
        return ""

    # Clear message if it contains too many repeated words
    # log.info(f"Repeated word percentage: {await repeated_word_filter(self, filtered)}")
    if await repeated_word_filter(filtered) > repeated_word_percentage:
        return ""

    # Replace certain message patterns with more readable ones
    filtered = await fixup_text(filtered)

    # Replace mentions with the user's name
    filtered = await mention_filter(filtered, text.guild)

    # Replace emotes with their text meanings
    filtered = await emoji_textifier(filtered)

    # Remove links
    filtered = await link_filter(filtered)

    # Remove characters that cause issues
    filtered = await remove_characters(filtered)

    # Remove spoilers
    filtered = await filter_spoilers(filtered)

    # Clear message if it is contains too long of a word
    if await long_word_filter(filtered, max_word_length):
        return ""

    # Limit the message length
    filtered = filtered[:max_message_length]

    return filtered
