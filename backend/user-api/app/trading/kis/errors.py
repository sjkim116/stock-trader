"""
KIS-specific exceptions.

The KIS API responds with HTTP 200 + a JSON ``rt_cd`` discriminator
(``"0"`` = success, anything else = failure). We translate those into
exceptions so the broker layer doesn't have to read response bodies
to know if a request worked.
"""

from __future__ import annotations

from app.trading.broker import BrokerError, OrderRejectedError


class KISError(BrokerError):
    """Generic KIS failure. Used for endpoints that aren't orders
    (token issuance, balance inquiry). The rt_cd + msg1 fields from
    the response are attached for diagnostics."""

    def __init__(self, rt_cd: str, msg_cd: str, msg: str) -> None:
        super().__init__(f"KIS error rt_cd={rt_cd} msg_cd={msg_cd}: {msg}")
        self.rt_cd = rt_cd
        self.msg_cd = msg_cd
        self.msg = msg


class KISOrderRejectedError(OrderRejectedError):
    """Order-specific failure with the original Order attached, plus
    the KIS response fields so the caller can correlate against KIS
    audit logs."""

    def __init__(self, order, rt_cd: str, msg_cd: str, msg: str) -> None:
        super().__init__(order, f"KIS rejected ({rt_cd}/{msg_cd}): {msg}")
        self.rt_cd = rt_cd
        self.msg_cd = msg_cd
        self.kis_msg = msg
