"""
KISBroker — Broker Protocol over the 한국투자증권 OpenAPI.

This file is deliberately conservative: market orders only, no streaming,
no partial-fill reconciliation. Strategies submit a MARKET order; KIS
returns an order id; we surface it without polling for fills (the broker
balance inquiry shows positions a couple seconds later anyway).

Mode handling:
* ``paper_mode=True`` → 모의투자 (sandbox) URL + ``V*``-prefixed tr_id.
* ``paper_mode=False`` → 실전 URL + ``T*``-prefixed tr_id. **Real money.**

Untested against live KIS as of this PR — the user hasn't issued an
APP_KEY yet. All paths are covered by httpx MockTransport tests so the
contract is solid; the first live run still needs eyes on it.
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import List, Optional

import httpx

from app.trading.broker import Broker
from app.trading.kis.auth import KISTokenManager
from app.trading.kis.errors import KISError, KISOrderRejectedError
from app.trading.types import (
    AccountInfo,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)

logger = logging.getLogger(__name__)


_TR_IDS_PAPER = {
    "buy": "VTTC0802U",
    "sell": "VTTC0801U",
    "cancel": "VTTC0803U",
    "balance": "VTTC8434R",
}
_TR_IDS_REAL = {
    "buy": "TTTC0802U",
    "sell": "TTTC0801U",
    "cancel": "TTTC0803U",
    "balance": "TTTC8434R",
}


class KISBroker(Broker):
    """KIS OpenAPI adapter. Construct one per process — the underlying
    httpx client + token cache are not safe to share across event loops."""

    def __init__(
        self,
        *,
        base_url: str,
        app_key: str,
        app_secret: str,
        account_number: str,
        account_product_code: str = "01",
        paper_mode: bool = True,
        timeout_seconds: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
        token_manager: Optional[KISTokenManager] = None,
    ) -> None:
        if not (app_key and app_secret and account_number):
            raise ValueError("KISBroker requires app_key, app_secret, account_number")
        self._base_url = base_url.rstrip("/")
        self._app_key = app_key
        self._app_secret = app_secret
        self._cano = account_number
        self._acnt_prdt_cd = account_product_code
        self._paper_mode = paper_mode
        self._tr = _TR_IDS_PAPER if paper_mode else _TR_IDS_REAL
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = client is None
        self._token_mgr = token_manager or KISTokenManager(
            base_url=base_url,
            app_key=app_key,
            app_secret=app_secret,
            client=self._client,
            timeout_seconds=timeout_seconds,
        )
        # KIS rate-limits ~5 rps on paper, 20 rps on live. Serialise per
        # broker — strategies that need throughput should batch upstream
        # instead of hammering this layer.
        self._lock = asyncio.Lock()

    @property
    def paper_mode(self) -> bool:
        return self._paper_mode

    # ----------------------------------------------------------- helpers
    async def _headers(self, tr_id: str) -> dict:
        token = await self._token_mgr.get_token()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
            "tr_id": tr_id,
            "custtype": "P",  # personal account
        }

    async def _post(self, path: str, tr_id: str, body: dict) -> dict:
        async with self._lock:
            resp = await self._client.post(
                f"{self._base_url}{path}",
                headers=await self._headers(tr_id),
                json=body,
            )
        return _decode(resp)

    async def _get(self, path: str, tr_id: str, params: dict) -> dict:
        async with self._lock:
            resp = await self._client.get(
                f"{self._base_url}{path}",
                headers=await self._headers(tr_id),
                params=params,
            )
        return _decode(resp)

    # ----------------------------------------------------- Broker Protocol
    async def submit_order(self, order: Order) -> Order:
        # KIS supports MARKET via ORD_DVSN="01"; price is ignored.
        # Limit ("00") requires a non-zero ORD_UNPR. Strategies use
        # MARKET in this codebase, so we only validate that here.
        if order.order_type != OrderType.MARKET:
            raise KISOrderRejectedError(
                order,
                rt_cd="LOCAL",
                msg_cd="UNSUPPORTED_TYPE",
                msg="KISBroker currently only supports MARKET orders",
            )
        if order.quantity <= 0:
            raise KISOrderRejectedError(
                order,
                rt_cd="LOCAL",
                msg_cd="BAD_QTY",
                msg="quantity must be positive",
            )

        tr = self._tr["buy"] if order.side == OrderSide.BUY else self._tr["sell"]
        body = {
            "CANO": self._cano,
            "ACNT_PRDT_CD": self._acnt_prdt_cd,
            "PDNO": order.symbol,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(int(order.quantity)),
            "ORD_UNPR": "0",
        }
        data = await self._post("/uapi/domestic-stock/v1/trading/order-cash", tr, body)
        if data.get("rt_cd") != "0":
            raise KISOrderRejectedError(
                order,
                rt_cd=data.get("rt_cd", "?"),
                msg_cd=data.get("msg_cd", "?"),
                msg=data.get("msg1", "unknown KIS rejection"),
            )

        output = data.get("output") or {}
        order.broker_order_id = (
            output.get("ODNO") or output.get("KRX_FWDG_ORD_ORGNO") or "KIS-UNKNOWN"
        )
        # KIS doesn't synchronously report fills; the order has been
        # accepted, not necessarily executed.
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = order.created_at
        return order

    async def cancel_order(self, order_id: str) -> bool:
        # Cancel needs the original org-ord-no + KRX-FWDG-ORD-ORGNO that
        # the original submit response gave us; passing just our local
        # order_id can't be wired through here. Surface it so callers
        # see the limitation rather than getting a silent True.
        logger.warning(
            "KISBroker.cancel_order(%s) called — needs ORG_ODNO + KRX fwd "
            "org-no to actually cancel; returning False for now",
            order_id,
        )
        return False

    async def get_position(self, symbol: str) -> Optional[Position]:
        for pos in await self.get_positions():
            if pos.symbol == symbol:
                return pos
        return None

    async def get_positions(self) -> List[Position]:
        rows = await self._inquire_balance_rows()
        positions: List[Position] = []
        for row in rows:
            qty = Decimal(row.get("hldg_qty", "0"))
            if qty == 0:
                continue
            positions.append(
                Position(
                    symbol=row.get("pdno", ""),
                    quantity=qty,
                    avg_entry_price=Decimal(row.get("pchs_avg_pric", "0")),
                )
            )
        return positions

    async def get_account(self) -> AccountInfo:
        rows, summary = await self._inquire_balance()
        # ``dnca_tot_amt`` = total cash deposit, ``tot_evlu_amt`` = total
        # equity (cash + market value). Names differ slightly across
        # API revisions; fall back gracefully.
        cash = Decimal(summary.get("dnca_tot_amt") or summary.get("nass_amt", "0"))
        equity = Decimal(summary.get("tot_evlu_amt") or summary.get("nass_amt", "0"))
        realized = Decimal(summary.get("rlzt_pfls", "0"))
        unrealized = Decimal(summary.get("evlu_pfls_smtl_amt", "0"))
        return AccountInfo(
            cash=cash,
            equity=equity,
            realized_pnl_today=realized,
            unrealized_pnl=unrealized,
        )

    # ----------------------------------------------- balance inquiry helpers
    async def _inquire_balance(self):
        params = {
            "CANO": self._cano,
            "ACNT_PRDT_CD": self._acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        data = await self._get(
            "/uapi/domestic-stock/v1/trading/inquire-balance",
            self._tr["balance"],
            params,
        )
        if data.get("rt_cd") != "0":
            raise KISError(
                rt_cd=data.get("rt_cd", "?"),
                msg_cd=data.get("msg_cd", "?"),
                msg=data.get("msg1", "balance inquiry failed"),
            )
        rows = data.get("output1") or []
        summary_list = data.get("output2") or [{}]
        summary = summary_list[0] if isinstance(summary_list, list) else summary_list
        return rows, summary

    async def _inquire_balance_rows(self):
        rows, _ = await self._inquire_balance()
        return rows

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _decode(resp: httpx.Response) -> dict:
    if resp.status_code >= 400:
        raise KISError(
            rt_cd=str(resp.status_code),
            msg_cd="HTTP",
            msg=f"KIS HTTP {resp.status_code}: {resp.text[:200]}",
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise KISError(
            rt_cd="?",
            msg_cd="DECODE",
            msg=f"non-JSON response: {resp.text[:200]}",
        ) from exc
