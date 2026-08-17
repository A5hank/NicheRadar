"""Tests for semantic query relevance assessment."""

from unittest.mock import Mock

import pytest

from nicheradar.groq_client import GroqClient
from nicheradar.query_relevance import (
    QueryRelevanceAssessment,
    QueryRelevanceError,
    assess_query_relevance,
)


def test_assessment_preserves_order_and_exposes_warnings() -> None:
    """Assessments should match their original query indexes."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "assessments": [
            {
                "index": 1,
                "is_relevant": False,
                "reason": "Minecraft is unrelated to gym content.",
            },
            {
                "index": 0,
                "is_relevant": True,
                "reason": "Home workouts are part of fitness.",
            },
        ]
    }

    review = assess_query_relevance(
        client,
        "  Gym  ",
        [
            " Home workout routines ",
            " Minecraft survival ",
        ],
    )

    assert review.niche == "Gym"
    assert review.assessments == (
        QueryRelevanceAssessment(
            query="Home workout routines",
            is_relevant=True,
            reason="Home workouts are part of fitness.",
        ),
        QueryRelevanceAssessment(
            query="Minecraft survival",
            is_relevant=False,
            reason="Minecraft is unrelated to gym content.",
        ),
    )
    assert review.warnings == (
        QueryRelevanceAssessment(
            query="Minecraft survival",
            is_relevant=False,
            reason="Minecraft is unrelated to gym content.",
        ),
    )

    client.generate_json.assert_called_once()


def test_empty_query_collection_does_not_call_groq() -> None:
    """No manually changed queries should require no LLM call."""

    client = Mock(spec=GroqClient)

    review = assess_query_relevance(
        client,
        "Gym",
        (),
    )

    assert review.niche == "Gym"
    assert review.assessments == ()
    assert review.warnings == ()

    client.generate_json.assert_not_called()


def test_assessment_rejects_non_boolean_decision() -> None:
    """Text decisions should not be accepted as booleans."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "assessments": [
            {
                "index": 0,
                "is_relevant": "no",
                "reason": "This query appears unrelated.",
            }
        ]
    }

    with pytest.raises(
        QueryRelevanceError,
        match="boolean",
    ):
        assess_query_relevance(
            client,
            "Gym",
            ["Minecraft"],
        )


def test_assessment_requires_one_result_per_query() -> None:
    """Groq must return a complete assessment collection."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "assessments": [
            {
                "index": 0,
                "is_relevant": True,
                "reason": "This query is related.",
            }
        ]
    }

    with pytest.raises(
        QueryRelevanceError,
        match="one assessment per query",
    ):
        assess_query_relevance(
            client,
            "Gym",
            [
                "Home workouts",
                "Gym motivation",
            ],
        )


def test_assessment_rejects_more_than_four_queries() -> None:
    """The locked niche leaves at most four queries to assess."""

    client = Mock(spec=GroqClient)

    with pytest.raises(
        ValueError,
        match="at most 4",
    ):
        assess_query_relevance(
            client,
            "Gym",
            [
                "Query one",
                "Query two",
                "Query three",
                "Query four",
                "Query five",
            ],
        )

    client.generate_json.assert_not_called()