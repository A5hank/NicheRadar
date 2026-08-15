"""Validation and interactive review of search queries."""

from collections.abc import Callable, Sequence

from nicheradar.query_expansion import normalize_query

REQUIRED_QUERY_COUNT = 5


class QueryReviewError(ValueError):
    """Raised when a query-review operation is invalid."""


def prepare_review_queries(
    *,
    niche: str,
    suggested_queries: Sequence[str],
) -> list[str]:
    """Create a clean editable query list."""

    cleaned_niche = normalize_query(niche)

    if not cleaned_niche:
        raise QueryReviewError("niche must not be empty")

    prepared_queries = [cleaned_niche]
    seen_queries = {cleaned_niche.casefold()}

    for suggested_query in suggested_queries:
        if not isinstance(suggested_query, str):
            continue

        cleaned_query = normalize_query(suggested_query)

        if not cleaned_query:
            continue

        comparison_key = cleaned_query.casefold()

        if comparison_key in seen_queries:
            continue

        prepared_queries.append(cleaned_query)
        seen_queries.add(comparison_key)

        if len(prepared_queries) == (REQUIRED_QUERY_COUNT):
            break

    return prepared_queries


def _query_position_to_index(
    position: int,
    query_count: int,
) -> int:
    """Convert a user-facing position into a list index."""

    if not 1 <= position <= query_count:
        raise QueryReviewError(f"position must be between 1 and {query_count}")

    return position - 1


def _validate_new_query(
    *,
    query: str,
    existing_queries: Sequence[str],
    ignored_index: int | None = None,
) -> str:
    """Clean a query and ensure it is not duplicated."""

    cleaned_query = normalize_query(query)

    if not cleaned_query:
        raise QueryReviewError("query must not be empty")

    comparison_key = cleaned_query.casefold()

    for index, existing_query in enumerate(existing_queries):
        if index == ignored_index:
            continue

        if existing_query.casefold() == comparison_key:
            raise QueryReviewError(f'query "{cleaned_query}" already exists')

    return cleaned_query


def add_query(
    queries: list[str],
    query: str,
) -> None:
    """Add one unique query when fewer than five exist."""

    if len(queries) >= REQUIRED_QUERY_COUNT:
        raise QueryReviewError("five queries already exist; remove or replace one first")

    cleaned_query = _validate_new_query(
        query=query,
        existing_queries=queries,
    )

    queries.append(cleaned_query)


def remove_query(
    queries: list[str],
    *,
    position: int,
) -> None:
    """Remove a query other than the original niche."""

    index = _query_position_to_index(
        position,
        len(queries),
    )

    if index == 0:
        raise QueryReviewError("the original niche cannot be removed")

    queries.pop(index)


def replace_query(
    queries: list[str],
    *,
    position: int,
    replacement: str,
) -> None:
    """Replace a query other than the original niche."""

    index = _query_position_to_index(
        position,
        len(queries),
    )

    if index == 0:
        raise QueryReviewError("the original niche cannot be replaced")

    cleaned_replacement = _validate_new_query(
        query=replacement,
        existing_queries=queries,
        ignored_index=index,
    )

    queries[index] = cleaned_replacement


def validate_approved_queries(
    *,
    niche: str,
    queries: Sequence[str],
) -> tuple[str, ...]:
    """Validate and freeze the five approved queries."""

    cleaned_niche = normalize_query(niche)

    if len(queries) != REQUIRED_QUERY_COUNT:
        raise QueryReviewError(f"exactly {REQUIRED_QUERY_COUNT} queries are required")

    cleaned_queries: list[str] = []

    for query in queries:
        if not isinstance(query, str):
            raise QueryReviewError("every query must be a string")

        cleaned_query = normalize_query(query)

        if not cleaned_query:
            raise QueryReviewError("queries must not be empty")

        cleaned_queries.append(cleaned_query)

    if cleaned_queries[0].casefold() != cleaned_niche.casefold():
        raise QueryReviewError("the first query must be the original niche")

    comparison_keys = {query.casefold() for query in cleaned_queries}

    if len(comparison_keys) != REQUIRED_QUERY_COUNT:
        raise QueryReviewError("all five queries must be unique")

    return tuple(cleaned_queries)


def format_review_queries(
    queries: Sequence[str],
) -> str:
    """Build the numbered query-review display."""

    lines = [
        "",
        "Proposed search queries:",
        "",
    ]

    for position, query in enumerate(
        queries,
        start=1,
    ):
        locked_label = " [original - locked]" if position == 1 else ""

        lines.append(f"{position}. {query}{locked_label}")

    lines.extend(
        [
            "",
            (f"{len(queries)}/{REQUIRED_QUERY_COUNT} queries selected"),
            "",
            "Commands:",
            "  add <query>",
            "  remove <number>",
            "  replace <number> <query>",
            "  confirm",
        ]
    )

    return "\n".join(lines)


def review_queries_interactively(
    *,
    niche: str,
    suggested_queries: Sequence[str],
    input_function: Callable[[str], str] = input,
    output_function: Callable[[str], None] = print,
) -> tuple[str, ...]:
    """Let a terminal user edit and approve five queries."""

    queries = prepare_review_queries(
        niche=niche,
        suggested_queries=suggested_queries,
    )

    while True:
        output_function(format_review_queries(queries))

        command = input_function("\nquery-review> ").strip()

        if not command:
            output_function("Enter a review command.")
            continue

        action, _separator, argument = command.partition(" ")
        action = action.casefold()
        argument = argument.strip()

        try:
            if action == "add":
                add_query(
                    queries,
                    argument,
                )
                continue

            if action == "remove":
                position = int(argument)

                remove_query(
                    queries,
                    position=position,
                )
                continue

            if action == "replace":
                position_text, separator, replacement = argument.partition(" ")

                if not separator:
                    raise QueryReviewError("use: replace <number> <query>")

                position = int(position_text)

                replace_query(
                    queries,
                    position=position,
                    replacement=replacement,
                )
                continue

            if action == "confirm":
                approved_queries = validate_approved_queries(
                    niche=niche,
                    queries=queries,
                )

                output_function("Queries approved. Starting YouTube collection.")

                return approved_queries

            raise QueryReviewError("unknown command; use add, remove, replace, or confirm")
        except ValueError as error:
            output_function(f"Error: {error}")
