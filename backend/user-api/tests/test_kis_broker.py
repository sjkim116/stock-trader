"""Unit tests for KISBroker + KISTokenManager — all mocked, no live calls.

Uses ``httpx.MockTransport`` so each test owns the exact responses KIS
would return. No credentials, no network. Two things this covers:
(1) the request shape we send matches KIS's documented contract, and
(2) the response decoding maps cleanly onto the Broker Protocol.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Callable, List, Tuple

import httpx
import pytest

from app.trading.kis.auth import KISTokenManager
from app.trading.kis.broker import KISBroker
from app.trading.kis.errors import KISError, KISOrderRejectedError
from app.trading.types import Order, OrderSide, OrderStatus, OrderType


BASE = "https://kis-mock.test"


def _build_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=BASE, transport=httpx.MockTransport(handler), timeout=5.0
    )


def _success_token_response() -> dict:
    return {
        "access_token": "fake-token-abc",
        "expires_in": 86400,
        "token_type": "Bearer",
    }


def _build_broker(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    paper_mode: bool = True,
) -> Tuple[KISBroker, List[httpx.Request]]:
    """Returns (broker, captured_requests). Tests append to
    captured_requests inside the handler to assert payload shape."""
    captured: List[httpx.Request] = []

    def capturing(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return handler(req)

    client = _build_client(capturing)
    broker = KISBroker(
        base_url=BASE,
        app_key="key",
        app_secret="secret",
        account_number="50100001",
        account_product_code="01",
        paper_mode=paper_mode,
        client=client,
    )
    return broker, captured


@pytest.mark.asyncio
async def test_token_manager_caches_token_across_calls():
    call_count = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/oauth2/tokenP"
        call_count["n"] += 1
        return httpx.Response(200, json=_success_token_response())

    client = _build_client(handler)
    mgr = KISTokenManager(base_url=BASE, app_key="k", app_secret="s", client=client)
    tok1 = await mgr.get_token()
    tok2 = await mgr.get_token()
    assert tok1 == tok2 == "fake-token-abc"
    assert call_count["n"] == 1  # second call reused the cache
    await client.aclose()


@pytest.mark.asyncio
async def test_token_manager_refreshes_when_expiry_window_breached():
    call_count = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        # First call: short-lived token that's already within the refresh
        # window (REFRESH_BEFORE = 15min, so anything <15min triggers refresh).
        body = {
            "access_token": f"tok-{call_count['n']}",
            "expires_in": 60 if call_count["n"] == 1 else 86400,
            "token_type": "Bearer",
        }
        return httpx.Response(200, json=body)

    client = _build_client(handler)
    mgr = KISTokenManager(base_url=BASE, app_key="k", app_secret="s", client=client)
    tok1 = await mgr.get_token()
    tok2 = await mgr.get_token()
    assert tok1 == "tok-1"
    assert tok2 == "tok-2"  # second call had to refresh
    await client.aclose()


@pytest.mark.asyncio
async def test_submit_market_buy_sends_correct_payload_and_tr_id():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json=_success_token_response())
        assert req.url.path == "/uapi/domestic-stock/v1/trading/order-cash"
        assert req.headers["tr_id"] == "VTTC0802U"  # paper buy
        assert req.headers["authorization"] == "Bearer fake-token-abc"
        body = json.loads(req.content)
        assert body == {
            "CANO": "50100001",
            "ACNT_PRDT_CD": "01",
            "PDNO": "005930",
            "ORD_DVSN": "01",
            "ORD_QTY": "10",
            "ORD_UNPR": "0",
        }
        return httpx.Response(
            200,
            json={
                "rt_cd": "0",
                "msg_cd": "OK",
                "msg1": "정상처리",
                "output": {"ODNO": "12345678", "KRX_FWDG_ORD_ORGNO": "ORGABC"},
            },
        )

    broker, _ = _build_broker(handler)
    order = Order(
        symbol="005930",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )
    result = await broker.submit_order(order)
    assert result.status == OrderStatus.SUBMITTED
    assert result.broker_order_id == "12345678"
    await broker.aclose()


@pytest.mark.asyncio
async def test_submit_sell_uses_sell_tr_id_in_paper_mode():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json=_success_token_response())
        assert req.headers["tr_id"] == "VTTC0801U"
        return httpx.Response(
            200, json={"rt_cd": "0", "msg1": "ok", "output": {"ODNO": "99"}}
        )

    broker, _ = _build_broker(handler)
    await broker.submit_order(
        Order(
            symbol="005930",
            side=OrderSide.SELL,
            quantity=Decimal("5"),
            order_type=OrderType.MARKET,
        )
    )
    await broker.aclose()


@pytest.mark.asyncio
async def test_real_mode_uses_T_prefixed_tr_ids():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json=_success_token_response())
        assert req.headers["tr_id"] == "TTTC0802U"  # real-mode buy
        return httpx.Response(
            200, json={"rt_cd": "0", "msg1": "ok", "output": {"ODNO": "1"}}
        )

    broker, _ = _build_broker(handler, paper_mode=False)
    await broker.submit_order(
        Order(
            symbol="005930",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.MARKET,
        )
    )
    await broker.aclose()


@pytest.mark.asyncio
async def test_kis_error_response_raises_order_rejected():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json=_success_token_response())
        return httpx.Response(
            200,
            json={
                "rt_cd": "1",
                "msg_cd": "EGW00121",
                "msg1": "주문 가능 수량을 초과하였습니다.",
            },
        )

    broker, _ = _build_broker(handler)
    with pytest.raises(KISOrderRejectedError) as exc_info:
        await broker.submit_order(
            Order(
                symbol="005930",
                side=OrderSide.BUY,
                quantity=Decimal("9999"),
                order_type=OrderType.MARKET,
            )
        )
    assert exc_info.value.rt_cd == "1"
    assert exc_info.value.msg_cd == "EGW00121"
    await broker.aclose()


@pytest.mark.asyncio
async def test_limit_order_rejected_at_local_level():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json=_success_token_response())
        pytest.fail("Should not have reached KIS — local validation should reject")

    broker, _ = _build_broker(handler)
    with pytest.raises(KISOrderRejectedError, match="MARKET"):
        await broker.submit_order(
            Order(
                symbol="005930",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                order_type=OrderType.LIMIT,
                price=Decimal("100"),
            )
        )
    await broker.aclose()


@pytest.mark.asyncio
async def test_get_positions_maps_kis_balance_rows():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json=_success_token_response())
        assert req.url.path == "/uapi/domestic-stock/v1/trading/inquire-balance"
        assert req.headers["tr_id"] == "VTTC8434R"
        return httpx.Response(
            200,
            json={
                "rt_cd": "0",
                "msg1": "ok",
                "output1": [
                    {
                        "pdno": "005930",
                        "hldg_qty": "10",
                        "pchs_avg_pric": "70000.50",
                    },
                    {
                        "pdno": "000660",
                        "hldg_qty": "0",  # zero ⇒ skipped
                        "pchs_avg_pric": "0",
                    },
                ],
                "output2": [
                    {
                        "dnca_tot_amt": "5000000",
                        "tot_evlu_amt": "5700000",
                        "rlzt_pfls": "1000",
                        "evlu_pfls_smtl_amt": "5000",
                    }
                ],
            },
        )

    broker, _ = _build_broker(handler)
    positions = await broker.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "005930"
    assert positions[0].quantity == Decimal("10")
    assert positions[0].avg_entry_price == Decimal("70000.50")

    account = await broker.get_account()
    assert account.cash == Decimal("5000000")
    assert account.equity == Decimal("5700000")
    assert account.realized_pnl_today == Decimal("1000")
    assert account.unrealized_pnl == Decimal("5000")
    await broker.aclose()


@pytest.mark.asyncio
async def test_get_position_filters_to_symbol():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json=_success_token_response())
        return httpx.Response(
            200,
            json={
                "rt_cd": "0",
                "msg1": "ok",
                "output1": [
                    {"pdno": "005930", "hldg_qty": "3", "pchs_avg_pric": "70000"},
                ],
                "output2": [{}],
            },
        )

    broker, _ = _build_broker(handler)
    assert (await broker.get_position("000660")) is None
    pos = await broker.get_position("005930")
    assert pos is not None
    assert pos.quantity == Decimal("3")
    await broker.aclose()


@pytest.mark.asyncio
async def test_balance_inquiry_error_raises_kis_error():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json=_success_token_response())
        return httpx.Response(200, json={"rt_cd": "1", "msg_cd": "X", "msg1": "boom"})

    broker, _ = _build_broker(handler)
    with pytest.raises(KISError):
        await broker.get_positions()
    await broker.aclose()


@pytest.mark.asyncio
async def test_token_http_error_raises_kis_error():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid appkey")

    client = _build_client(handler)
    mgr = KISTokenManager(base_url=BASE, app_key="bad", app_secret="bad", client=client)
    with pytest.raises(KISError):
        await mgr.get_token()
    await client.aclose()


def test_missing_credentials_rejected_at_construction():
    with pytest.raises(ValueError):
        KISBroker(
            base_url=BASE,
            app_key="",
            app_secret="s",
            account_number="50100001",
        )
    with pytest.raises(ValueError):
        KISBroker(
            base_url=BASE,
            app_key="k",
            app_secret="s",
            account_number="",
        )
