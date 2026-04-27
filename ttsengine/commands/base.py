from redbot.core.config import Config
from redbot.core.bot import Red
from typing import NamedTuple

class TTSBase:
    # This class is mainly here to make the analysis from the IDE happy
    # while also avoid circular imports.

    bot: Red

    config: Config


class NonTTSTrack(NamedTuple):
    # This sorts track information for non-tts tracks
    track: object
    position: int
    was_paused: bool
    volume: int