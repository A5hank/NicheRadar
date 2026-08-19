"""Tests for AI-assisted niche query expansion."""

from unittest.mock import Mock

import pytest

from nicheradar.groq_client import GroqClient
from nicheradar.query_expansion import (
    QueryExpansionError,
    expand_niche_queries,
)


def test_expansion_keeps_original_and_removes_duplicates() -> None:
    """Expansion should produce clean unique queries."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {
        "queries": [
            " Marvel ",
            " MCU theories ",
            "Marvel news",
            "mcu theories",
            "",
            123,
        ]
    }

    expansion = expand_niche_queries(
        client,
        "  Marvel  ",
        query_count=5,
    )

    assert expansion.niche == "Marvel"
    assert expansion.queries == (
        "Marvel",
        "MCU theories",
        "Marvel news",
    )
    client.generate_json.assert_called_once()


def test_one_query_does_not_call_groq() -> None:
    """The original niche alone should not require an LLM."""

    client = Mock(spec=GroqClient)

    expansion = expand_niche_queries(
        client,
        "Marvel",
        query_count=1,
    )

    assert expansion.queries == ("Marvel",)
    client.generate_json.assert_not_called()


def test_expansion_accepts_ten_total_queries() -> None:
    """Expansion should support one niche and nine alternatives."""

    client = Mock(spec=GroqClient)

    alternative_queries = [f"Marvel angle {index}" for index in range(1, 10)]

    client.generate_json.return_value = {
        "queries": alternative_queries,
    }

    expansion = expand_niche_queries(
        client,
        "Marvel",
        query_count=10,
    )

    assert expansion.queries == (
        "Marvel",
        *alternative_queries,
    )

    request_arguments = client.generate_json.call_args.kwargs

    assert request_arguments["max_completion_tokens"] == 450

    response_schema = request_arguments["response_schema"]

    query_schema = response_schema["properties"]["queries"]

    assert query_schema["minItems"] == 9
    assert query_schema["maxItems"] == 9


def test_expansion_rejects_more_than_ten_queries() -> None:
    """Expansion should reject an eleventh query."""

    client = Mock(spec=GroqClient)

    with pytest.raises(
        ValueError,
        match="between 1 and 10",
    ):
        expand_niche_queries(
            client,
            "Marvel",
            query_count=11,
        )

    client.generate_json.assert_not_called()


def test_expansion_rejects_missing_query_list() -> None:
    """Malformed Groq output should be rejected clearly."""

    client = Mock(spec=GroqClient)
    client.generate_json.return_value = {"unexpected": []}

    with pytest.raises(
        QueryExpansionError,
        match="queries list",
    ):
        expand_niche_queries(
            client,
            "Marvel",
        )
