"""Nextcloud WebDAV upload support."""

from pathlib import PurePosixPath

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
                response = await self._client.put(
                    remote_url,
                    content=content,
                    headers=headers,
                    auth=(self._username or "", self._password or ""),
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
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
