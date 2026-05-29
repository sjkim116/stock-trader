"""
KIS OAuth2 token manager.

KIS access tokens last ~24 hours but the issuance endpoint is rate
limited at "once per minute per appkey" — frequent refreshes will get
the connection blocked. The manager caches the live token, only calls
``/oauth2/tokenP`` when it's missing or near expiry, and serialises
concurrent callers behind an asyncio.Lock so the first request that
needs a token fires the network call and the rest wait.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.trading.kis.errors import KISError

logger = logging.getLogger(__name__)

# Refresh ``REFRESH_BEFORE`` seconds before actual expiry so a request
# in flight doesn't get a 401 mid-burst.
REFRESH_BEFORE = timedelta(minutes=15)


@dataclass
class TokenSnapshot:
    access_token: str
    expires_at: datetime  # UTC


class KISTokenManager:
    def __init__(
        self,
        *,
        base_url: str,
        app_key: str,
        app_secret: str,
        client: Optional[httpx.AsyncClient] = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._app_key = app_key
        self._app_secret = app_secret
        self._timeout = timeout_seconds
        # If a client is injected (tests), don't close it on aclose.
        self._client = client
        self._owns_client = client is None
        self._token: Optional[TokenSnapshot] = None
        import asyncio

        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        async with self._lock:
            if self._token is None or self._needs_refresh(self._token):
                self._token = await self._fetch()
            return self._token.access_token

    def _needs_refresh(self, snap: TokenSnapshot) -> bool:
        return datetime.now(timezone.utc) + REFRESH_BEFORE >= snap.expires_at

    async def _fetch(self) -> TokenSnapshot:
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.post(
                f"{self._base_url}/oauth2/tokenP",
                json={
                    "grant_type": "client_credentials",
                    "appkey": self._app_key,
                    "appsecret": self._app_secret,
                },
            )
        finally:
            if self._owns_client:
                await client.aclose()
        if resp.status_code >= 400:
            raise KISError(
                rt_cd=str(resp.status_code),
                msg_cd="HTTP",
                msg=f"token issuance failed: {resp.text[:200]}",
            )
        body = resp.json()
        if "access_token" not in body:
            raise KISError(
                rt_cd=body.get("rt_cd", "?"),
                msg_cd=body.get("msg_cd", "?"),
                msg=body.get("msg1", "no access_token in response"),
            )
        # KIS returns ``expires_in`` seconds (typically 86400 = 24h).
        expires_in = int(body.get("expires_in", 86400))
        snap = TokenSnapshot(
            access_token=body["access_token"],
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        )
        logger.info("Issued KIS token, expires_at=%s", snap.expires_at.isoformat())
        return snap

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
