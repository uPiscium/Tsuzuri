import asyncio

import httpx

from tsuzuri.llm.ollama_client import OllamaClient


def test_ollama_client_posts_chat_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": "result"}},
            request=request,
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://ollama.example"
        ) as http_client:
            client = OllamaClient(
                base_url="https://ollama.example",
                model="gemma",
                timeout_sec=10,
                temperature=0.2,
                num_ctx=8192,
                retry_count=0,
                client=http_client,
            )

            assert await client.chat("Summarize") == "result"

        request = requests[0]
        assert request.method == "POST"
        assert str(request.url) == "https://ollama.example/api/chat"
        assert b'"stream":false' in request.content
        assert b'"model":"gemma"' in request.content

    asyncio.run(run())
