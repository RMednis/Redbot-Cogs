import ttsengine.core.text_filter

## Repeated Word Filter Tests

def test_repeated_word_filter_no_repeats():
    text = "This is a test sentence."
    assert ttsengine.core.text_filter.repeated_word_filter(text) == 0.00

def test_repeated_word_filter_with_repeats():
    text = "spam spam spam spam"
    assert ttsengine.core.text_filter.repeated_word_filter(text) == 75

def test_repeated_word_filter_mixed():
    text = "This is a test sentence. This test is only a test."
    assert round(ttsengine.core.text_filter.repeated_word_filter(text)) == 45

## Long Word Filter Tests

def test_long_word_filter_no_long_words():
    text = "This is a test sentence."
    assert ttsengine.core.text_filter.long_word_filter(text, 10) == False

def test_long_word_filter_with_long_words():
    text = "This is a test sentence with a supercalifragilisticexpialidocious word."
    assert ttsengine.core.text_filter.long_word_filter(text, 10) == True

def test_long_word_filter_one_over():
    text = "This is a test sentence with a supercalifragilisticexpialidocious word."
    assert ttsengine.core.text_filter.long_word_filter(text, 33) == True

def test_long_word_filter_one_under():
    text = "This is a test sentence with a supercalifragilisticexpialidocious word."
    assert ttsengine.core.text_filter.long_word_filter(text, 34) == False

# Emoji Text-ifier Tests

def test_emoji_textifier_no_emojis():
    text = "This is a test sentence."
    assert ttsengine.core.text_filter.emoji_textifier(text) == text

def test_emoji_static():
    assert ttsengine.core.text_filter.emoji_textifier("<:apple:123456789>") == "apple"

def test_emoji_animated():
    assert ttsengine.core.text_filter.emoji_textifier("<a:apple:123456789>") == "apple"

def test_emoji_mixed():
    text = "I love <:apples:123456789> and <:grapes:987654321>!"
    assert ttsengine.core.text_filter.emoji_textifier(text) == "I love apples and grapes!"

# Filter Spoiler Tests

def test_filter_spoiler_no_spoiler():
    text = "This is a test sentence."
    assert ttsengine.core.text_filter.filter_spoilers(text) == text

def test_filter_spoiler_with_spoiler():
    text = "This is a ||apple|| sentence."
    assert ttsengine.core.text_filter.filter_spoilers(text) == "This is a spoiler sentence."

def test_filter_spoiler_multiple_spoilers():
    text = "This is a ||apple|| sentence with multiple ||apples||."
    assert ttsengine.core.text_filter.filter_spoilers(text) == "This is a spoiler sentence with multiple spoiler."

# Test Character Filter

def test_character_filter_no_filter():
    text = "This is a test sentence."
    assert ttsengine.core.text_filter.remove_characters(text) == text

def test_character_filter_with_filter():
    text = "This is a test/sentence with some special_characters!"
    assert ttsengine.core.text_filter.remove_characters(text) == "This is a test sentence with some special characters!"

# Repeated Character Filter Tests

def test_repeated_character_filter_no_repeats():
    text = "This is a test sentence. So cool!"
    assert ttsengine.core.text_filter.repeated_letter_fix(text) == text

def test_repeated_character_filter_with_repeats():
    text = "Spaaaace is soooo cooool!!!"
    assert ttsengine.core.text_filter.repeated_letter_fix(text) == "Spaace is soo cool!!!"

# Fixup Text Tests

def test_fixup_text_no_changes():
    text = "This is a test sentence."
    assert ttsengine.core.text_filter.fixup_text(text, {"lol": "laugh"}) == text

def test_fixup_text_with_changes():
    text = "This is a test sentence lol"
    assert ttsengine.core.text_filter.fixup_text(text, {"lol": "laugh"}) == "This is a test sentence laugh"

def test_fixup_text_case_insensitive():
    text = "This is a test sentence LOL"
    assert ttsengine.core.text_filter.fixup_text(text, {"lol": "laugh"}) == "This is a test sentence laugh"

def test_fixup_text_multiple_words():
    text = "I can't believe it lol."
    assert (ttsengine.core.text_filter.fixup_text(text, {"lol": "laugh out loud"})
            == "I can't believe it laugh out loud.")

def test_fixup_text_partial_word():
    text = "This is a test sentence lollipop."
    assert ttsengine.core.text_filter.fixup_text(text, {"lol": "laugh"}) == text

def test_fixup_text_with_suffix():
    text = "I can't believe it lols."
    assert ttsengine.core.text_filter.fixup_text(text, {"lol": "laugh"}) == "I can't believe it laughs."

# Test Name Filter
def test_name_filter_no_filter():
    text = "mednis"
    assert ttsengine.core.text_filter.fixup_name(text, {"bert":"Bart"}) == "mednis"

def test_name_filter_capitalized():
    text = "Mednis"
    assert ttsengine.core.text_filter.fixup_name(text, {"bert":"Bart"}) == "mednis"

def test_name_filter_with_filter():
    text = "Mednis"
    assert ttsengine.core.text_filter.fixup_name(text, {"mednis":"NotMednis"}) == "NotMednis"

def test_name_filter_with_filter_capitalized():
    text = "Mednis"
    assert ttsengine.core.text_filter.fixup_name(text, {"Mednis":"NotMednis"}) == "NotMednis"

def test_name_filter_partial_match():
    text = "MednisBot"
    assert ttsengine.core.text_filter.fixup_name(text, {"Mednis":"NotMednis"}) == "NotMednisbot"

def test_name_filter_multiple_matches():
    text = "Mednis is great. But I am Mednis!"
    assert ttsengine.core.text_filter.fixup_name(text, {"Mednis":"NotMednis"}) == "NotMednis is great. but i am NotMednis!"