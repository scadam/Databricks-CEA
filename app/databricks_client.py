from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable, List, Mapping

from openai import OpenAI

logger = logging.getLogger(__name__)


class DatabricksClientError(RuntimeError):
    """Raised when the Databricks endpoint returns an error."""


def _coalesce_content(content: Any) -> str:
    """Normalize Databricks/OpenAI message content into plain text."""

    def _chunk_to_text(chunk: Any) -> str:
        if chunk is None:
            return ""
        if isinstance(chunk, str):
            return chunk
        if isinstance(chunk, dict):
            text = chunk.get("text")
            if isinstance(text, str):
                return text
            if isinstance(text, list):
                return "".join(str(part) for part in text)
            content_value = chunk.get("content")
            if isinstance(content_value, str):
                return content_value
            return str(chunk)
        attr_text = getattr(chunk, "text", None)
        if isinstance(attr_text, str):
            return attr_text
        if isinstance(attr_text, list):
            return "".join(str(part) for part in attr_text)
        return str(chunk)

    if isinstance(content, list):
        return "".join(_chunk_to_text(chunk) for chunk in content)

    return _chunk_to_text(content)


class DatabricksClient:
    """Thin async wrapper around the Databricks-serving-compatible OpenAI client."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int,
        temperature: float,
        request_timeout: float = 30.0,
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = request_timeout

    async def generate_reply(self, *, messages: Iterable[Mapping[str, str]]) -> str:
        """Send a chat.completions request and return the concatenated reply text."""

        payload: List[Mapping[str, str]] = list(messages)
        if not payload:
            raise DatabricksClientError("At least one message is required for generation.")

        logger.debug("Dispatching Databricks request with %d messages", len(payload))

        def _invoke() -> str:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=payload,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            if not response.choices:
                raise DatabricksClientError("Databricks response did not include choices.")
            return "".join(
                _coalesce_content(getattr(choice.message, "content", None))
                for choice in response.choices
            ).strip()

        try:
            content = await asyncio.wait_for(asyncio.to_thread(_invoke), timeout=self._timeout)
        except asyncio.TimeoutError as exc:
            logger.error("Databricks request timed out: %s", exc)
            raise DatabricksClientError("Databricks request timed out") from exc
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Databricks request failed")
            raise DatabricksClientError("Databricks request failed") from exc

        if not content:
            content = "I could not generate a response just now. Please try again."
        return content
