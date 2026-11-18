import pytest

from bot import is_image_request


@pytest.mark.parametrize(
    "prompt",
    [
        "1. create image where avenger and dr.doom flight",
        "Create an image of a futuristic city at night",
        "Generate a picture showing a dragon above the mountains",
        "Draw Doctor Doom flying over a ruined city",
        "I want an illustration of two heroes in the sky",
    ],
)
def test_natural_language_image_requests_are_detected(prompt):
    assert is_image_request(prompt)


@pytest.mark.parametrize(
    "prompt",
    [
        "What is the weather in Surat?",
        "Explain how a Discord bot works",
        "Calculate 12 * 8",
        "Write a short story about a flying hero",
    ],
)
def test_regular_chat_requests_are_not_routed_to_image_generation(prompt):
    assert not is_image_request(prompt)
