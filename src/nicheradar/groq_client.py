"""Minimal client for Groq's Chat Completions API."""

import json
from types import TracebackType

import httpx

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_TIMEOUT_SECONDS = 30.0


class GroqAPIError(RuntimeError):
    """Raised when Groq cannot return a usable response."""


def extract_groq_error_message(
    response: httpx.Response,
) -> str:
    """Extract a safe error message from a Groq response."""

    try:
        payload = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        error_details = payload.get("error")

        if isinstance(error_details, dict):
            message = error_details.get("message")

            if isinstance(message, str) and message:
                return message

    return f"HTTP {response.status_code}"


def is_json_schema_generation_failure(
    response: httpx.Response,
) -> bool:
    """Return whether Groq failed while enforcing JSON Schema output."""

    if response.status_code != 400:
        return False

    message = extract_groq_error_message(response).casefold()

    known_generation_failures = (
        "failed to generate json",
        "failed to validate json",
    )

    return any(failure_message in message for failure_message in known_generation_failures)


class GroqClient:
    """Small synchronous client for JSON responses from Groq."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_GROQ_MODEL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Configure the client without making an API request."""

        cleaned_api_key = api_key.strip()
        cleaned_model = model.strip()

        if not cleaned_api_key:
            raise ValueError("Groq API key must not be empty")

        if not cleaned_model:
            raise ValueError("Groq model must not be empty")

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.model = cleaned_model
        self._client = httpx.Client(
            headers={
                "Authorization": (f"Bearer {cleaned_api_key}"),
                "Content-Type": "application/json",
            },
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        """Release network resources owned by the HTTP client."""

        self._client.close()

    def __enter__(self) -> "GroqClient":
        """Return this client when entering a with block."""

        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client when leaving a with block."""

        self.close()

    def _post_chat_completion(
        self,
        request_payload: dict[str, object],
    ) -> httpx.Response:
        """Send one Groq request and convert connection failures safely."""

        try:
            return self._client.post(
                GROQ_CHAT_COMPLETIONS_URL,
                json=request_payload,
            )
        except httpx.RequestError as error:
            raise GroqAPIError("Could not connect to the Groq API.") from error

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_completion_tokens: int = 300,
        response_schema: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Ask Groq for a response containing one JSON object."""

        if max_completion_tokens < 1:
            raise ValueError("max_completion_tokens must be at least 1")

        response_format: dict[str, object] = {
            "type": "json_object",
        }

        if response_schema is not None:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "nicheradar_response",
                    "strict": True,
                    "schema": response_schema,
                },
            }

        request_payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "temperature": 0.2,
            "max_completion_tokens": max_completion_tokens,
            "response_format": response_format,
        }

        response = self._post_chat_completion(
            request_payload,
        )

        should_use_json_object_fallback = (
            response_schema is not None and is_json_schema_generation_failure(response)
        )

        if should_use_json_object_fallback:
            request_payload["response_format"] = {
                "type": "json_object",
            }

            response = self._post_chat_completion(
                request_payload,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            message = extract_groq_error_message(
                error.response,
            )

            raise GroqAPIError(f"Groq API request failed: {message}") from error

        try:
            response_payload = response.json()
        except ValueError as error:
            raise GroqAPIError("Groq returned a non-JSON API response.") from error

        if not isinstance(response_payload, dict):
            raise GroqAPIError("Groq returned an invalid response object.")

        choices = response_payload.get("choices")

        if not isinstance(choices, list) or not choices:
            raise GroqAPIError("Groq response did not contain a completion.")

        first_choice = choices[0]

        if not isinstance(first_choice, dict):
            raise GroqAPIError("Groq returned an invalid completion.")

        message = first_choice.get("message")

        if not isinstance(message, dict):
            raise GroqAPIError("Groq completion did not contain a message.")

        content = message.get("content")

        if not isinstance(content, str) or not content:
            raise GroqAPIError("Groq completion did not contain text.")

        try:
            decoded_content = json.loads(content)
        except json.JSONDecodeError as error:
            raise GroqAPIError("Groq completion was not valid JSON.") from error

        if not isinstance(decoded_content, dict):
            raise GroqAPIError("Groq completion must be a JSON object.")

        return decoded_content
