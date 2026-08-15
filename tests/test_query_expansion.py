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
