"""Streamlit interface for reviewing NicheRadar search queries."""

import streamlit as st

from nicheradar.config import get_settings
from nicheradar.groq_client import GroqAPIError, GroqClient
from nicheradar.query_expansion import (
    DEFAULT_QUERY_COUNT,
    expand_niche_queries,
)
from nicheradar.query_review import (
    QueryReviewError,
    prepare_review_queries,
    validate_approved_queries,
)

st.set_page_config(
    page_title="NicheRadar",
    page_icon="📡",
    layout="wide",
)


def initialize_session_state() -> None:
    """Create the Streamlit session values used by the interface."""

    if "review_niche" not in st.session_state:
        st.session_state.review_niche = None

    if "review_queries" not in st.session_state:
        st.session_state.review_queries = None

    if "approved_queries" not in st.session_state:
        st.session_state.approved_queries = None

    if "query_generation" not in st.session_state:
        st.session_state.query_generation = 0


def generate_review_queries(
    *,
    niche: str,
    groq_api_key: str,
) -> tuple[str, list[str]]:
    """Generate and prepare editable queries for the UI."""

    with GroqClient(groq_api_key) as groq_client:
        expansion = expand_niche_queries(
            groq_client,
            niche,
            query_count=DEFAULT_QUERY_COUNT,
        )

    review_queries = prepare_review_queries(
        niche=expansion.niche,
        suggested_queries=expansion.queries,
    )

    missing_query_count = (
        DEFAULT_QUERY_COUNT - len(review_queries)
    )

    review_queries.extend(
        [""] * missing_query_count
    )

    return expansion.niche, review_queries


initialize_session_state()
settings = get_settings()

st.title("NicheRadar")

st.caption(
    "Discover high-performing YouTube Short candidates "
    "from the last seven days."
)

with st.sidebar:
    st.header("Current stage")

    st.write(
        "Generate five search queries, review them, "
        "and approve the final list."
    )

    st.info(
        "YouTube collection will be connected in the "
        "next checkpoint."
    )

niche = st.text_input(
    "What niche do you want to analyse?",
    placeholder="For example: Marvel, fitness, AI productivity",
    help=(
        "NicheRadar sends this topic to Groq to generate "
        "related YouTube search queries."
    ),
)

generate_button = st.button(
    "Generate search queries",
    type="primary",
    use_container_width=True,
)

if generate_button:
    cleaned_niche = niche.strip()

    if not cleaned_niche:
        st.error("Enter a niche before generating queries.")

    elif not settings.groq_api_key:
        st.error(
            "GROQ_API_KEY is missing. Add it to your .env file."
        )

    else:
        try:
            with st.spinner(
                "Groq is generating search queries..."
            ):
                review_niche, review_queries = (
                    generate_review_queries(
                        niche=cleaned_niche,
                        groq_api_key=settings.groq_api_key,
                    )
                )

        except (GroqAPIError, ValueError) as error:
            st.error(
                f"Query generation failed: {error}"
            )

        else:
            st.session_state.review_niche = review_niche
            st.session_state.review_queries = review_queries
            st.session_state.approved_queries = None
            st.session_state.query_generation += 1

            st.rerun()

if st.session_state.review_queries is None:
    st.info(
        "Enter a niche and generate search queries to begin."
    )
    st.stop()

st.divider()
st.subheader("Review search queries")

st.write(
    "The original niche is locked. Edit the other fields "
    "until you have exactly five unique, non-empty queries."
)

form_key = (
    f"query-review-{st.session_state.query_generation}"
)

with st.form(form_key):
    edited_queries: list[str] = []

    for index, query in enumerate(
        st.session_state.review_queries
    ):
        position = index + 1
        is_original_niche = index == 0

        label = f"Query {position}"

        if is_original_niche:
            label += " — original niche"

        edited_query = st.text_input(
            label,
            value=query,
            disabled=is_original_niche,
            key=(
                f"query-"
                f"{st.session_state.query_generation}-"
                f"{index}"
            ),
        )

        edited_queries.append(edited_query)

    approve_button = st.form_submit_button(
        "Approve five queries",
        type="primary",
        use_container_width=True,
    )

if approve_button:
    st.session_state.approved_queries = None

    try:
        approved_queries = validate_approved_queries(
            niche=st.session_state.review_niche,
            queries=edited_queries,
        )

    except QueryReviewError as error:
        st.error(f"Cannot approve queries: {error}")

    else:
        st.session_state.approved_queries = approved_queries

if st.session_state.approved_queries is not None:
    st.success("All five search queries are approved.")

    st.write("Approved queries:")

    for position, approved_query in enumerate(
        st.session_state.approved_queries,
        start=1,
    ):
        st.write(f"{position}. {approved_query}")

    st.info(
        "The next checkpoint will send these approved "
        "queries into the YouTube analysis pipeline."
    )