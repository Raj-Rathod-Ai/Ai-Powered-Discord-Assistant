import pytest
from channel_policy import allowed_channel_ids, is_allowed_channel


def test_parse_single_channel():
    assert allowed_channel_ids("1572151691539648564") == frozenset({1572151691539648564})


def test_parse_multiple_channels_and_whitespace():
    assert allowed_channel_ids(" 12, 34 ,,56 ") == frozenset({12, 34, 56})


def test_empty_allowlist_fails_closed():
    allowlist = allowed_channel_ids("")
    assert not is_allowed_channel(123, allowlist)
    assert not is_allowed_channel(None, allowlist)


def test_reject_non_numeric_channel_id():
    with pytest.raises(ValueError):
        allowed_channel_ids("123,not-a-channel")


def test_only_configured_channel_is_allowed():
    allowlist = allowed_channel_ids("1572151691539648564")
    assert is_allowed_channel(1572151691539648564, allowlist)
    assert not is_allowed_channel(1572151691539648565, allowlist)
