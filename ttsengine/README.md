# TTS Engine
A better way of using Text to Speech from discord for our no-mic friends.
Uses Stream elements API to be able to generate TTS using the voices of Brian, Amy, and many others instead of the awful
Microsoft system localised voices. 

This lets different users have different voices and languages, as well as letting you adjust the volume of people using 
TTS separately from the general discord volume in system settings.

> [!IMPORTANT]  
> This cog only uses slash commands!

## Requirements
Red 3.5+ is required for this cog to work.

# Commands

### User Settings
These are the user facing settings for the TTS cog.

- `/tts-voice` - Set what voice you want to use for TTS.
- `/tts-skip` - Skip the current TTS message.

### Admin Settings
These are the admin facing settings for the TTS cog.

- `/tts-volume` - Set the volume of TTS for the server.
- `/tts-settings` - General settings for the TTS cog.
    - `add_name_substitution <name> <substitution>` - Add a name substitution for TTS. (Used for swapping out usernames with different phonetic pronunciations)
    - `remove_name_substitution <name>` - Remove a name substitution for TTS.
    - `add_word_substitution <word> <substitution>` - Add a word substitution for TTS. (Used for swapping out words with different phonetic pronunciations)
    - `remove_word_substitution <word>` - Remove a word substitution for TTS.
    - `max_word_length <length>` - Set the maximum word length for TTS. Words longer then this will mean that the message will not be read out.
    - `max_message_length <length>` - Set the maximum message length for TTS. Messages longer then this will mean that the message will not be read out.
    - `repeated_word_percentage <percentage>` - Set the percentage of repeated words in a message for TTS. Messages with more then this percentage of repeated words will not be read out.
    - `show` - Show the current settings for the TTS cog.
- `/tts_channels` - Set the channels that TTS will read out messages from.
  - `add_vc <channel>` - Add a voice channel to the TTS list.
  - `remove_vc <channel>` - Remove a voice channel from the TTS list.
  - `add_text <channel>` - Add a text channel to the TTS list.
  - `remove_text <channel>` - Remove a text channel from the TTS list.
- `/tts_blacklist` - Set the blacklist for TTS.
  - `add <user>` - Add a person to the TTS blacklist.
  - `remove <userl>` - Remove a person from the TTS blacklist.
  - `list` - Show the current TTS blacklist.

You can also add or remove people from the TTS blacklist by right clicking on their name and selecting the option from the `Apps` context menu.
Make sure you have enabled all the slash commands by using `[p]slash enablecog ttsengine` (Some commands use spaces and can only be enabled that way.)