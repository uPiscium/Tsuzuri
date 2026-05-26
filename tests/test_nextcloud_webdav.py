import asyncio

import httpx

from tsuzuri.storage.nextcloud_webdav import WebdavUploader


def test_webdav_upload_skips_when_config_is_missing() -> None:
    async def run() -> None:
        uploader = WebdavUploader(
            webdav_url="https://nextcloud.example/remote.php/dav/files/user/research",
            username="user",
            password=None,
            timeout_sec=10,
        )

        result = await uploader.upload_bytes(
            content=b"report", remote_path="runs/run-1/report.md"
        )

        assert result.uploaded is False
        assert result.skipped is True
        assert result.warning == "WebDAV upload skipped; missing password"

    asyncio.run(run())


def test_webdav_upload_puts_bytes_with_auth_and_content_type() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, request=request)

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            uploader = WebdavUploader(
                webdav_url="https://nextcloud.example/remote.php/dav/files/user/research/",
                username="user",
                password="pass",
                timeout_sec=10,
                client=client,
            )

            result = await uploader.upload_bytes(
                content=b"report",
                remote_path="/runs/run-1/report.md",
                content_type="text/markdown",
            )

        assert result.uploaded is True
        assert result.skipped is False
        assert result.remote_url == (
            "https://nextcloud.example/remote.php/dav/files/user/research/runs/run-1/report.md"
        )
        assert requests[0].method == "PUT"
        assert requests[0].url == result.remote_url
        assert requests[0].headers["Content-Type"] == "text/markdown"
        assert requests[0].headers["Authorization"].startswith("Basic ")
        assert requests[0].content == b"report"

    asyncio.run(run())


def test_webdav_upload_warns_and_continues_on_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            uploader = WebdavUploader(
                webdav_url="https://nextcloud.example/webdav",
                username="user",
                password="pass",
                timeout_sec=10,
                client=client,
            )

            result = await uploader.upload_bytes(
                content=b"report", remote_path="report.md"
            )

        assert result.uploaded is False
        assert result.skipped is False
        assert result.remote_url == "https://nextcloud.example/webdav/report.md"
        assert result.warning is not None
        assert result.warning.startswith("WebDAV upload failed:")

    asyncio.run(run())
