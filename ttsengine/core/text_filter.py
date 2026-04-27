import re

import discord


def repeated_word_filter(text: str) -> float:
    # Strip punctuation and normalize case
    words = re.sub(r"[^\w\s]", "", text.lower()).split()

    if not words:
        return 0.0

    total_words = len(words)
    total_unique_words = len(set(words))
    repeating_words = total_words - total_unique_words

    return (repeating_words / total_words) * 100


def long_word_filter(text: str, length):
    words = text.split()

    for word in words:
        if len(word) > length:
            return True

    return False


def mention_filter(text: str, guild: discord.Guild):
    mentions = re.findall(r"<(@!?\d+|@&\d+|#\d+)>", text)
    for mention in mentions:
        full_mention = f"<{mention}>"
        id_part = int(re.findall(r"\d+", mention)[0])

        if mention.startswith("@&"):
            role = guild.get_role(id_part)
            if role:
                text = text.replace(full_mention, f"at {role.name}")
        elif mention.startswith("#"):
            channel = guild.get_channel(id_part)
            if channel:
                text = text.replace(full_mention, f"in {channel.name}")
        else:
            user = guild.get_member(id_part)
            if user:
                name = user.nick or user.display_name
                text = text.replace(full_mention, f"to {name}")

    return text


def emoji_textifier(text: str):
    emote_pattern = r'<a?:(\w+):\d+>'
    text = re.sub(emote_pattern, lambda match: match.group(1), text)

    return text


def filter_spoilers(text: str):
    spoiler_pattern = r'\|\|(.*?)\|\|'
    text = re.sub(spoiler_pattern, "spoiler", text, flags=re.DOTALL)

    return text


def link_filter(text: str):
    # Regular expression pattern to match URLs
    url_pattern = re.compile(r"https?://\S+")

    # Remove URLs from the text
    text_without_links = re.sub(url_pattern, 'Link', text)

    return text_without_links


def remove_characters(text: str):
    # Slash command pauses the tts for a bit
    text = text.replace("/", " ")

    # Underscores are used to imply italics, we should ignore them
    text = text.replace("_", " ")

    return text


def fixup_text(text: str, replacements: dict) -> str:
    # Replace certain message patterns with more readable ones
    for pattern, replacement in replacements.items():
        # Regular expression to match the pattern with optional 's or s at the end
        regex_pattern = r'\b' + re.escape(pattern) + r"(?:'s|s)?\b"

        # Function to perform the replacement while keeping the 's or s suffix
        def replace_with_suffix(match):
            suffix = match.group(0)[len(pattern):]  # Extract the suffix ('s or s)
            return replacement + suffix

        text = re.sub(regex_pattern, replace_with_suffix, text, flags=re.IGNORECASE)

    return text


def fixup_name(text: str, name_replacements: dict) -> str:
    # Fix pronunciation of certain names
    # Replace the patterns
    for pattern, replacement in name_replacements.items():
        text = text.lower().replace(pattern, replacement)

    return text

def repeated_letter_fix(string):
    # This regex matches any letter that repeats 4 or more times consecutively.
    return re.sub(r"([a-zA-Z])\1{3,}", lambda m: ' '.join(m.group()) + ' ', string)

# Ignore commands that start with the command prefix
def command_ignore_filter(text: str, command_prefixes: list):
    for prefix in command_prefixes:
        if text.startswith(prefix):
            command_word = text.split(" ")[0]
            command = command_word[len(prefix):]
            if command.isalpha():
                return ""
    return text

async def filter_message(text: str, *, max_message_length: int, max_word_length: int,
                            repeated_word_percentage: float, word_replacements: dict,
                            command_prefixes: list, guild: discord.Guild) -> str:

    # Remove random spaces
    filtered = text.strip()

    # Ignore commands
    filtered = command_ignore_filter(filtered, command_prefixes)

    if len(filtered) == 0:
        return ""

    # Clear message if it contains too many repeated words
    # log.info(f"Repeated word percentage: {await repeated_word_filter(self, filtered)}")
    if repeated_word_filter(filtered) > repeated_word_percentage:
        return ""

    # Replace certain message patterns with more readable ones
    filtered = fixup_text(filtered, word_replacements)

    # Replace mentions with the user's name
    filtered = mention_filter(filtered, guild)

    # Replace emotes with their text meanings
    filtered = emoji_textifier(filtered)

    # Remove links
    filtered = link_filter(filtered)

    # Remove characters that cause issues
    filtered = remove_characters(filtered)

    # Remove spoilers
    filtered = filter_spoilers(filtered)

    # Clear message if it contains too long of a word
    if long_word_filter(filtered, max_word_length):
        return ""

    # Replace multiplied letters with their individual pronunciations
    filtered = repeated_letter_fix(filtered)

    # Limit the message length
    if len(filtered) > max_message_length:
        truncated = filtered[:max_message_length]
        last_space = truncated.rfind(" ")
        filtered = truncated[:last_space] if last_space > 0 else truncated


    return filtered