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


def test_approval_accepts_original_niche_only() -> None:
    """The locked original niche should be enough to continue."""

    approved_queries = validate_approved_queries(
        niche="  Marvel  ",
        queries=(
            " Marvel ",
        ),
    )

    assert approved_queries == ("Marvel",)


def test_approval_rejects_more_than_five_queries() -> None:
    """The review must never approve more than five queries."""

    with pytest.raises(
        QueryReviewError,
        match="between 1 and 5",
    ):
        validate_approved_queries(
            niche="Marvel",
            queries=(
                "Marvel",
                "Marvel news",
                "MCU theories",
                "Marvel facts",
                "Marvel trailers",
                "Marvel interviews",
            ),
        )


def test_approval_requires_original_niche_first() -> None:
    """An alternative query cannot replace the locked niche."""

    with pytest.raises(
        QueryReviewError,
        match="first query must be the original niche",
    ):
        validate_approved_queries(
            niche="Marvel",
            queries=(
                "MCU theories",
                "Marvel",
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
