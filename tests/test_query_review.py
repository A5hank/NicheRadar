"""Tests for search-query review and approval."""

import pytest

from nicheradar.query_review import (
    QueryReviewError,
    add_query,
    prepare_review_queries,
    remove_query,
    review_queries_interactively,
    validate_approved_queries,
)


def test_prepare_queries_keeps_original_first() -> None:
    """Suggestions should be cleaned and deduplicated."""

    queries = prepare_review_queries(
        niche="  Marvel  ",
        suggested_queries=(
            "Marvel",
            " MCU theories ",
            "Marvel news",
            "mcu theories",
            "",
        ),
    )

    assert queries == [
        "Marvel",
        "MCU theories",
        "Marvel news",
    ]


def test_original_niche_cannot_be_removed() -> None:
    """Position one must remain locked."""

    queries = [
        "Marvel",
        "Marvel news",
    ]

    with pytest.raises(
        QueryReviewError,
        match="cannot be removed",
    ):
        remove_query(
            queries,
            position=1,
        )


def test_duplicate_query_cannot_be_added() -> None:
    """Query comparisons should ignore capitalization."""

    queries = [
        "Marvel",
        "Marvel news",
    ]

    with pytest.raises(
        QueryReviewError,
        match="already exists",
    ):
        add_query(
            queries,
            "MARVEL NEWS",
        )


def test_approval_requires_exactly_five_queries() -> None:
    """Four approved queries should be rejected."""

    with pytest.raises(
        QueryReviewError,
        match="exactly 5",
    ):
        validate_approved_queries(
            niche="Marvel",
            queries=(
                "Marvel",
                "Marvel news",
                "MCU theories",
                "Marvel facts",
            ),
        )


def test_interactive_review_can_remove_and_add() -> None:
    """A user should be able to correct Groq suggestions."""

    commands = iter(
        [
            "remove 3",
            "add Marvel trailers",
            "confirm",
        ]
    )
    output_messages: list[str] = []

    approved_queries = review_queries_interactively(
        niche="Marvel",
        suggested_queries=(
            "Marvel",
            "Marvel news",
            "MCU theories",
            "Marvel facts",
            "Upcoming Marvel movies",
        ),
        input_function=lambda _prompt: next(commands),
        output_function=output_messages.append,
    )

    assert approved_queries == (
        "Marvel",
        "Marvel news",
        "Marvel facts",
        "Upcoming Marvel movies",
        "Marvel trailers",
    )
    assert any("Queries approved" in message for message in output_messages)
