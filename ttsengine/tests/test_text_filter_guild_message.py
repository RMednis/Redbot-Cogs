import pytest
from unittest.mock import MagicMock
from ttsengine.core.text_filter import filter_message, filter_and_format_message
from ttsengine.core.settings import TTSGuildSettings

# Dirty mock of a discord message, only the properties we need for the tests
def make_message(content: str, nick=None, name="TestUser") -> MagicMock:
    message = MagicMock()
    message.content = content
    message.author.nick = nick
    message.author.name = name
    message.message_snapshots = []
    message.attachments = []
    message.stickers = []
    return message

# Helper function to create TTSGuildSettings with defaults and overrides
def make_settings(**overrides) -> TTSGuildSettings:
    defaults = dict(
        say_name=True,
        max_message_length=400,
        max_word_length=15,
        repeated_word_percentage=80,
        global_tts_volume=100,
        name_replacements={},
        word_replacements={},
        command_prefixes=[]
    )
    return TTSGuildSettings(**{**defaults, **overrides})

def make_attachment(content_type: str) -> MagicMock:
    attachment = MagicMock()
    attachment.content_type = content_type
    return attachment

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

@pytest.mark.asyncio
async def test_says_name():
    message = make_message(content="hello", name="testuser")
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "testuser says hello"

@pytest.mark.asyncio
async def test_does_not_say_name():
    message = make_message(content="hello", name="testuser")
    result = await filter_and_format_message(message, make_settings(say_name=False))
    assert result.text == "hello"

@pytest.mark.asyncio
async def test_uses_nick():
    message = make_message(content="hello", nick="NotMednis", name="Mednis")
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "notmednis says hello"

@pytest.mark.asyncio
async def test_name_replacement():
    message = make_message(content="hello", name="testuser")
    result = await filter_and_format_message(message, make_settings(say_name=True, name_replacements={"testuser": "Mednis"}))
    assert result.text == "Mednis says hello"

@pytest.mark.asyncio
async def test_word_replacement():
    message = make_message(content="hello world", name="testuser")
    result = await filter_and_format_message(message, make_settings(word_replacements={"world": "universe"}))
    assert result.text == "testuser says hello universe"

@pytest.mark.asyncio
async def test_filter_command_prefix():
    message = make_message(content="!play something", name="testuser")
    result = await filter_and_format_message(message, make_settings(command_prefixes=["!"]))
    assert result is None

@pytest.mark.asyncio
async def test_attachment_no_text():
    message = make_message(content="")
    message.attachments = [make_attachment("image/png")]
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "testuser sends image"

@pytest.mark.asyncio
async def test_attachment_unknown_type():
    message = make_message(content="")
    message.attachments = [make_attachment("")]
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "testuser sends media"

@pytest.mark.asyncio
async def test_attachment_with_text():
    message = make_message(content="check this out")
    message.attachments = [make_attachment("image/png")]
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "testuser says check this out with attached image"

@pytest.mark.asyncio
async def test_link():
    message = make_message(content="check this out https://example.com")
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "testuser says check this out Link"

@pytest.mark.asyncio
async def test_link_alone():
    message = make_message(content="https://example.com")
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "testuser sends link"

@pytest.mark.asyncio
async def test_forwarded_message_with_name():
    message = make_message(content="")
    message.message_snapshots = [MagicMock()]
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "testuser forwarded a message"

@pytest.mark.asyncio
async def test_forwarded_message_without_name():
    message = make_message(content="")
    message.message_snapshots = [MagicMock()]
    result = await filter_and_format_message(message, make_settings(say_name=False))
    assert result is None

@pytest.mark.asyncio
async def test_sticker():
    message = make_message(content="")
    sticker = MagicMock()
    sticker.name = "sheepspin"
    message.stickers = [sticker]
    result = await filter_and_format_message(message, make_settings(say_name=True))
    assert result.text == "testuser sends sheepspin sticker"