import pytest
from unittest.mock import MagicMock
from ttsengine.core.text_filter import filter_message
from ttsengine.core.settings import TTSGuildSettings


def make_settings(**overrides) -> TTSGuildSettings:
    defaults = dict(
        say_name=True,
        max_message_length=400,
        max_word_length=15,
        repeated_word_percentage=80,
        global_tts_volume=100,
        name_replacements={},
        word_replacements={},
        command_prefixes=[],
    )
    return TTSGuildSettings(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_filter_message_basic():
    result = await filter_message("hello world", settings=make_settings(), guild=MagicMock())
    assert result == "hello world"


@pytest.mark.asyncio
async def test_filter_message_too_long():
    result = await filter_message(
        "word " * 100,
        settings=make_settings(max_message_length=20),
        guild=MagicMock(),
    )
    assert len(result) <= 20


@pytest.mark.asyncio
async def test_filter_message_command_prefix():
    result = await filter_message(
        "!play something",
        settings=make_settings(command_prefixes=["!"]),
        guild=MagicMock(),
    )
    assert result == ""


@pytest.mark.asyncio
async def test_filter_message_repeated_words():
    result = await filter_message(
        "spam spam spam spam spam",
        settings=make_settings(repeated_word_percentage=50),
        guild=MagicMock(),
    )
    assert result == ""


@pytest.mark.asyncio
async def test_filter_message_long_word():
    result = await filter_message(
        "thisisaverylongword",
        settings=make_settings(max_word_length=10),
        guild=MagicMock(),
    )
    assert result == ""
