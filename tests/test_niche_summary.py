"""Tests for deterministic niche-summary facts and guarded AI prose."""

import json
from dataclasses import replace
from unittest.mock import Mock

import pytest

from nicheradar.groq_client import GroqClient
from nicheradar.niche_summary import (
    AI_SUMMARY_SYSTEM_PROMPT,
    SUMMARY_RESPONSE_SCHEMA,
    AnalysisSummaryFacts,
    NewCreatorSignalLabel,
    NicheSummaryError,
    determine_new_creator_signal,
    generate_niche_summary,
    validate_summary_observations,
)


def build_facts(
    **changes: int | float,
) -> AnalysisSummaryFacts:
    """Create an adequate, favourable baseline for focused rule tests."""

    baseline = AnalysisSummaryFacts(
        query_count=5,
        videos_considered=100,
        videos_returned=50,
        videos_with_subscriber_data=40,
        breakout_count=4,
        breakout_channel_count=3,
        exceptional_count=1,
        unique_channel_count=28,
        virality_score=80,
        confidence_score=88,
        median_views_per_day=42_000.0,
    )

    return replace(
        baseline,
        **changes,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence_score": 39},
        {"query_count": 1},
        {
            "videos_considered": 29,
            "videos_returned": 29,
            "videos_with_subscriber_data": 25,
        },
        {
            "videos_returned": 9,
            "videos_with_subscriber_data": 8,
            "breakout_count": 1,
            "breakout_channel_count": 1,
            "exceptional_count": 0,
            "unique_channel_count": 9,
        },
        {"videos_with_subscriber_data": 19},
    ],
)
def test_insufficient_evidence_takes_precedence(
    changes: dict[str, int | float],
) -> None:
    """Any agreed evidence floor should suppress a creator verdict."""

    signal = determine_new_creator_signal(build_facts(**changes))

    assert signal.label is NewCreatorSignalLabel.INSUFFICIENT_EVIDENCE


def test_favourable_signal_requires_every_approved_threshold() -> None:
    """A favourable result needs broad, reliable breakout evidence."""

    signal = determine_new_creator_signal(build_facts())

    assert signal.label is NewCreatorSignalLabel.FAVOURABLE
    assert "multiple creators" in signal.rationale


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence_score": 69},
        {"virality_score": 79},
        {"breakout_count": 2, "breakout_channel_count": 2},
        {"breakout_count": 3, "breakout_channel_count": 1},
        {"unique_channel_count": 19},
        {"videos_with_subscriber_data": 29},
    ],
)
def test_missing_a_favourable_threshold_becomes_mixed(
    changes: dict[str, int | float],
) -> None:
    """One insufficient positive signal cannot make the verdict favourable."""

    signal = determine_new_creator_signal(build_facts(**changes))

    assert signal.label is NewCreatorSignalLabel.MIXED


def test_limited_signal_requires_adequate_but_weak_current_evidence() -> None:
    """Low activity and both low highlight rates should be called limited."""

    signal = determine_new_creator_signal(
        build_facts(
            breakout_count=1,
            breakout_channel_count=1,
            exceptional_count=1,
            virality_score=49,
        )
    )

    assert signal.label is NewCreatorSignalLabel.LIMITED


def test_virality_score_of_fifty_is_mixed_not_limited() -> None:
    """The middle score band must not be labelled limited."""

    signal = determine_new_creator_signal(
        build_facts(
            breakout_count=1,
            breakout_channel_count=1,
            exceptional_count=1,
            virality_score=50,
        )
    )

    assert signal.label is NewCreatorSignalLabel.MIXED


def test_exceptional_activity_without_breakouts_is_mixed_not_favourable() -> None:
    """Large-channel exceptional results alone do not prove creator accessibility."""

    signal = determine_new_creator_signal(
        build_facts(
            breakout_count=1,
            breakout_channel_count=1,
            exceptional_count=4,
        )
    )

    assert signal.label is NewCreatorSignalLabel.MIXED


def test_summary_facts_reject_impossible_counts() -> None:
    """Invalid browser-provided facts must not reach the model."""

    with pytest.raises(
        ValueError,
        match="breakout_channel_count cannot exceed breakout_count",
    ):
        build_facts(
            breakout_count=2,
            breakout_channel_count=3,
        )


def test_generate_niche_summary_uses_only_validated_statistics() -> None:
    """Groq should receive facts and return exactly three guarded observations."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "observations": [
            "Virality and current view velocity show active recent momentum.",
            "The sample and subscriber coverage support the confidence score.",
            "Breakout results are spread across multiple channels.",
        ]
    }

    observations = generate_niche_summary(
        client,
        niche="  Minecraft  ",
        facts=build_facts(),
    )

    assert observations == (
        "Virality and current view velocity show active recent momentum.",
        "The sample and subscriber coverage support the confidence score.",
        "Breakout results are spread across multiple channels.",
    )

    request_arguments = client.generate_json.call_args.kwargs

    assert request_arguments["system_prompt"] == AI_SUMMARY_SYSTEM_PROMPT
    assert request_arguments["response_schema"] == SUMMARY_RESPONSE_SCHEMA
    assert request_arguments["max_completion_tokens"] == 600
    assert request_arguments["reasoning_effort"] == "low"

    prompt_payload = json.loads(request_arguments["user_prompt"])
    assert prompt_payload["niche"] == "Minecraft"
    assert set(prompt_payload) == {"niche", "analysis_facts"}
    assert "titles" not in prompt_payload["analysis_facts"]


@pytest.mark.parametrize(
    "observations",
    [
        [],
        ["one", "two"],
        ["same", "same", "third"],
        ["Guaranteed success.", "A second fact.", "A third fact."],
    ],
)
def test_summary_observation_validation_rejects_unsafe_output(
    observations: list[str],
) -> None:
    """Malformed, duplicate, and promissory model prose stays hidden."""

    with pytest.raises(NicheSummaryError):
        validate_summary_observations(observations)
