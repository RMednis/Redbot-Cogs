from redbot.core.config import Config
from redbot.core.bot import Red
from typing import NamedTuple
import lavalink
from pathlib import Path

class NonTTSTrack(NamedTuple):
    # This sorts track information for non-tts tracks
    track: lavalink.Track
    position: int
    was_paused: bool
    volume: int

class TTSBase:
    # This class is mainly here to make the analysis from the IDE happy
    # while also avoid circular imports.

    bot: Red
    config: Config
    llplayer: lavalink.Player | None
    tts_queue: list[str]
    last_non_tts_track: NonTTSTrack | None
    audio_file_name: str
    cog_path: Path