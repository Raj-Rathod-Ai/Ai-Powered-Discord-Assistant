"""Fail-closed Discord channel allowlist helpers."""

def allowed_channel_ids(raw_value: str) -> frozenset[int]:
    """Parse comma-separated Discord channel IDs, ignoring whitespace."""
    values = set()
    for part in (raw_value or "").split(","):
        value = part.strip()
        if not value:
            continue
        if not value.isdigit():
            raise ValueError("DISCORD_ALLOWED_CHANNEL_IDS must contain comma-separated numeric channel IDs.")
        values.add(int(value))
    return frozenset(values)


def is_allowed_channel(channel_id: int | None, allowlist: frozenset[int]) -> bool:
    """Return True only when the channel is explicitly allowlisted."""
    return channel_id is not None and channel_id in allowlist
