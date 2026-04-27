import pytest
from unittest.mock import MagicMock
from ttsengine.core.text_filter import filter_message


@pytest.mark.asyncio
async def test_filter_message_basic():
    guild = MagicMock()
    result = await filter_message(
        "hello world",
        max_message_length=400,
        max_word_length=15,
        repeated_word_percentage=80,
        word_replacements={},
        command_prefixes=[],
        guild=guild
    )
    assert result == "hello world"

@pytest.mark.asyncio
async def test_filter_message_too_long():
  guild = MagicMock()
  result = await filter_message(
      "word " * 100,
      max_message_length=20,
      max_word_length=15,
      repeated_word_percentage=80,
      word_replacements={},
      command_prefixes=[],
      guild=guild
  )
  assert len(result) <= 20

  @pytest.mark.asyncio
  async def test_filter_message_command_prefix():
      guild = MagicMock()
      result = await filter_message(
          "!play something",
          max_message_length=400,
          max_word_length=15,
          repeated_word_percentage=80,
          word_replacements={},
          command_prefixes=["!"],
          guild=guild
      )
      assert result == ""

@pytest.mark.asyncio
async def test_filter_message_repeated_words():
  guild = MagicMock()
  result = await filter_message(
      "spam spam spam spam spam",
      max_message_length=400,
      max_word_length=15,
      repeated_word_percentage=50,
      word_replacements={},
      command_prefixes=[],
      guild=guild
  )
  assert result == ""

@pytest.mark.asyncio
async def test_filter_message_long_word():
  guild = MagicMock()
  result = await filter_message(
      "thisisaverylongword",
      max_message_length=400,
      max_word_length=10,
      repeated_word_percentage=80,
      word_replacements={},
      command_prefixes=[],
      guild=guild
  )
  assert result == ""
