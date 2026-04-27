from unittest.mock import MagicMock
from ttsengine.core.text_filter import mention_filter

# User mention tests

def test_mention_user_without_nick():
    guild = MagicMock()
    member = MagicMock()
    member.nick = None
    member.display_name = "Mednis"
    guild.get_member.return_value = member
    assert mention_filter("<@123456789>", guild) == "to Mednis"

def test_mention_user_with_nick():
    guild = MagicMock()
    member = MagicMock()
    member.nick = "NotMednis"
    member.display_name = "Mednis"
    guild.get_member.return_value = member
    assert mention_filter("<@123456789>", guild) == "to NotMednis"

def test_mention_user_id():
  guild = MagicMock()
  member = MagicMock()
  member.nick = None
  member.display_name = "Mednis"
  guild.get_member.return_value = member

  mention_filter("<@123456789>", guild)
  guild.get_member.assert_called_once_with(123456789)

def test_mention_user_unknown():
  guild = MagicMock()
  guild.get_member.return_value = None

  assert mention_filter("<@123456789>", guild) == "<@123456789>"

# Role mention tests

def test_mention_role_output():
    guild = MagicMock()
    role = MagicMock()
    role.name = "Admins"
    guild.get_role.return_value = role

    assert mention_filter("<@&123456789>", guild) == "at Admins"

def test_mention_role_id():
  guild = MagicMock()
  role = MagicMock()
  role.name = "Admins"
  guild.get_role.return_value = role

  mention_filter("Hi <@&123456789>!", guild)
  guild.get_role.assert_called_once_with(123456789)

def test_mention_role_unknown():
  guild = MagicMock()
  guild.get_role.return_value = None

  assert mention_filter("<@&123456789>", guild) == "<@&123456789>"

# Channel mention tests

def test_mention_channel_output():
  guild = MagicMock()
  channel = MagicMock()
  channel.name = "general"
  guild.get_channel.return_value = channel

  assert mention_filter("<#123456789>", guild) == "in general"

def test_mention_channel_id():
    guild = MagicMock()
    channel = MagicMock()
    channel.name = "general"
    guild.get_channel.return_value = channel

    mention_filter("It's in <#123456789>!", guild)
    guild.get_channel.assert_called_once_with(123456789)


def test_mention_channel_unknown():
    guild = MagicMock()
    guild.get_channel.return_value = None

    assert mention_filter("<#123456789>", guild) == "<#123456789>"


def test_mention_multiple():
  guild = MagicMock()
  member = MagicMock()
  member.nick = None
  member.display_name = "Mednis"
  channel = MagicMock()
  channel.name = "general"
  guild.get_member.return_value = member
  guild.get_channel.return_value = channel

  assert mention_filter("<@123456789> <#987654321>", guild) == "to Mednis in general"