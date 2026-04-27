from dataclasses import dataclass

@dataclass
class TTSGuildSettings:
    say_name: bool
    max_message_length: int
    max_word_length: int
    repeated_word_percentage: float
    global_tts_volume: int
    name_replacements: dict
    word_replacements: dict
    command_prefixes: list

    @classmethod
    async def from_config(cls, config, guild):
        return cls(
            say_name=await config.guild(guild).say_name(),
            max_message_length=await config.guild(guild).max_message_length(),
            max_word_length=await config.guild(guild).max_word_length(),
            repeated_word_percentage=await config.guild(guild).repeated_word_percentage(),
            global_tts_volume=await config.guild(guild).global_tts_volume(),
            name_replacements=await config.guild(guild).name_replacements(),
            word_replacements=await config.guild(guild).word_replacements(),
            command_prefixes=await config.guild(guild).command_prefixes(),
        )


@dataclass
class TTSMessage:
    text: str
    track_name: str