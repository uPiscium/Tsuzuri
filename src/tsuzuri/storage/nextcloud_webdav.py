"""Nextcloud WebDAV upload support."""

from pathlib import PurePosixPath
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ConfigDict


class WebdavUploadResult(BaseModel):
    """Non-throwing result for optional WebDAV uploads."""

    model_config = ConfigDict(frozen=True)

    uploaded: bool
    skipped: bool
    remote_url: str | None = None
    warning: str | None = None


class WebdavUploader:
    """Upload artifacts through WebDAV without failing the pipeline on errors."""

    def __init__(
        self,
        *,
        webdav_url: str | None,
        username: str | None,
        password: str | None,
        timeout_sec: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._webdav_url = webdav_url.rstrip("/") if webdav_url else None
        self._username = username
        self._password = password
        self._timeout = httpx.Timeout(timeout_sec)
        self._client = client

    async def upload_bytes(
        self, *, content: bytes, remote_path: str, content_type: str | None = None
    ) -> WebdavUploadResult:
        """Upload bytes to WebDAV, returning warnings instead of raising."""
        warning = self._missing_config_warning()
        if warning is not None:
            return WebdavUploadResult(uploaded=False, skipped=True, warning=warning)

        assert self._webdav_url is not None
        remote_url = _join_webdav_url(self._webdav_url, remote_path)
        headers = {"Content-Type": content_type} if content_type is not None else None

        try:
            if self._client is not None:
                await self._create_parent_directories(self._client, remote_path)
                response = await self._client.put(
                    remote_url,
                    content=content,
                    headers=headers,
                    auth=(self._username or "", self._password or ""),
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    await self._create_parent_directories(client, remote_path)
                    response = await client.put(
                        remote_url,
                        content=content,
                        headers=headers,
                        auth=(self._username or "", self._password or ""),
                    )
            response.raise_for_status()
        except httpx.HTTPError as error:
            return WebdavUploadResult(
                uploaded=False,
                skipped=False,
                remote_url=remote_url,
                warning=f"WebDAV upload failed: {error}",
            )

        return WebdavUploadResult(uploaded=True, skipped=False, remote_url=remote_url)

    async def _create_parent_directories(
        self, client: httpx.AsyncClient, remote_path: str
    ) -> None:
        assert self._webdav_url is not None
        parent_parts = PurePosixPath(remote_path.lstrip("/")).parent.parts
        for directory_url in _base_directory_urls(self._webdav_url):
            await self._mkcol(client, directory_url)

        current_path = ""
        for part in parent_parts:
            if part in ("", "."):
                continue
            current_path = str(PurePosixPath(current_path) / part)
            await self._mkcol(client, _join_webdav_url(self._webdav_url, current_path))

    async def _mkcol(self, client: httpx.AsyncClient, url: str) -> None:
        response = await client.request(
            "MKCOL",
            url,
            auth=(self._username or "", self._password or ""),
        )
        if response.status_code in {200, 201, 204, 405}:
            return
        response.raise_for_status()

    def _missing_config_warning(self) -> str | None:
        missing = []
        if not self._webdav_url:
            missing.append("webdav_url")
        if not self._username:
            missing.append("username")
        if not self._password:
            missing.append("password")
        if not missing:
            return None
        return f"WebDAV upload skipped; missing {', '.join(missing)}"


def _join_webdav_url(base_url: str, remote_path: str) -> str:
    clean_path = str(PurePosixPath(remote_path.lstrip("/")))
    return f"{base_url}/{clean_path}"


def _base_directory_urls(base_url: str) -> list[str]:
    parts = urlsplit(base_url)
    path_parts = PurePosixPath(parts.path).parts
    try:
        files_index = path_parts.index("files")
    except ValueError:
        return []

    user_index = files_index + 1
    if len(path_parts) <= user_index + 1:
        return []

    urls: list[str] = []
    current_parts = path_parts[: user_index + 1]
    for part in path_parts[user_index + 1 :]:
        current_parts = (*current_parts, part)
        path = "/" + "/".join(current_parts[1:])
        urls.append(urlunsplit((parts.scheme, parts.netloc, path, "", "")))
    return urls
