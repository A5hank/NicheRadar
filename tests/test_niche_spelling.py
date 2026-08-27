"""Tests for conservative niche spelling suggestions."""

from unittest.mock import Mock

import pytest

from nicheradar.groq_client import GroqClient
from nicheradar.niche_spelling import (
    NicheSpellingError,
    check_niche_spelling,
)


@pytest.mark.parametrize(
    ("niche", "suggestion"),
    [
        ("  meincraft  ", "Minecraft"),
        ("chadgpt", "ChatGPT"),
        ("twitch clups", "Twitch clips"),
    ],
)
def test_high_confidence_typo_returns_a_suggestion(
    niche: str,
    suggestion: str,
) -> None:
    """An obvious misspelling can be offered, but is not silently changed."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "is_high_confidence_typo": True,
        "suggestion": suggestion,
    }

    spelling_check = check_niche_spelling(
        client,
        niche,
    )

    assert spelling_check.niche == niche.strip()
    assert spelling_check.suggestion == suggestion

    request_arguments = client.generate_json.call_args.kwargs

    assert request_arguments["max_completion_tokens"] == 120
    assert request_arguments["model"] == "groq/compound-mini"
    assert request_arguments["enable_web_search"] is True
    assert "response_schema" not in request_arguments


def test_correct_niche_returns_no_suggestion() -> None:
    """A correctly spelled niche should proceed without an interruption."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "is_high_confidence_typo": False,
        "suggestion": "",
    }

    spelling_check = check_niche_spelling(
        client,
        "Minecraft",
    )

    assert spelling_check.niche == "Minecraft"
    assert spelling_check.suggestion is None


def test_uncommon_niche_stays_unchanged_when_not_high_confidence() -> None:
    """A plausible uncommon niche must not be corrected on a weak signal."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "is_high_confidence_typo": False,
        "suggestion": "Aether Flux",
    }

    spelling_check = check_niche_spelling(
        client,
        "AetherFlux",
    )

    assert spelling_check.niche == "AetherFlux"
    assert spelling_check.suggestion is None


def test_case_only_suggestion_is_suppressed() -> None:
    """Capitalization alone is not a spelling suggestion worth interrupting for."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "is_high_confidence_typo": True,
        "suggestion": "Minecraft",
    }

    spelling_check = check_niche_spelling(
        client,
        "minecraft",
    )

    assert spelling_check.suggestion is None


@pytest.mark.parametrize(
    ("niche", "suggestion"),
    [
        ("Figma", "Sigma"),
        ("Minecraft", "Minecraftland"),
        ("AetherFlux", "AetherFlix"),
    ],
)
def test_unsafe_high_confidence_suggestions_are_suppressed(
    niche: str,
    suggestion: str,
) -> None:
    """A model cannot turn a plausible name or related term into a correction."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "is_high_confidence_typo": True,
        "suggestion": suggestion,
    }

    spelling_check = check_niche_spelling(
        client,
        niche,
    )

    assert spelling_check.suggestion is None


def test_malformed_high_confidence_output_is_rejected() -> None:
    """The API layer can fail open when Groq's structured output is unusable."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "is_high_confidence_typo": True,
        "suggestion": "",
    }

    with pytest.raises(
        NicheSpellingError,
        match="must not be empty",
    ):
        check_niche_spelling(
            client,
            "meincraft",
        )
