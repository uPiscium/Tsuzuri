"""Async Ollama chat client."""

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

JsonObject = Mapping[str, Any]


class OllamaClient:
    """Small async client for Ollama's /api/chat endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_sec: float,
        temperature: float,
        num_ctx: int,
        retry_count: int,
        client: httpx.AsyncClient | None = None,
        retry_delay_sec: float = 1.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = httpx.Timeout(timeout_sec)
        self._temperature = temperature
        self._num_ctx = num_ctx
        self._retry_count = retry_count
        self._client = client
        self._retry_delay_sec = retry_delay_sec

    async def chat(self, prompt: str) -> str:
        """Send one user prompt and return the assistant message content."""
        if self._client is not None:
            return await self._chat_with_retry(self._client, prompt)
        async with httpx.AsyncClient(
            base_url=self._base_url, timeout=self._timeout
        ) as client:
            return await self._chat_with_retry(client, prompt)

    async def _chat_with_retry(self, client: httpx.AsyncClient, prompt: str) -> str:
        attempts = self._retry_count + 1
        for attempt in range(attempts):
            try:
                response = await client.post(
                    "/api/chat",
                    json={
                        "model": self._model,
                        "stream": False,
                        "messages": [{"role": "user", "content": prompt}],
                        "options": {
                            "temperature": self._temperature,
                            "num_ctx": self._num_ctx,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, Mapping):
                    raise ValueError("Ollama response must be a JSON object")
                return _message_content(data)
            except (httpx.HTTPError, ValueError):
                if attempt == attempts - 1:
                    raise
                await asyncio.sleep(self._retry_delay_sec)
        raise RuntimeError("Ollama retry loop exited unexpectedly")


def _message_content(data: JsonObject) -> str:
    message = data.get("message")
    if not isinstance(message, Mapping):
        raise ValueError("Ollama response missing message object")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("Ollama response missing message content")
    return content
