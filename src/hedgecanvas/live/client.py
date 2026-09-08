"""Minimal synchronous Deribit public JSON-RPC HTTP client.

Public methods only: no API key, no authentication, no private endpoints,
no order placement. The underlying ``httpx.Client`` is injectable so tests
can supply a mocked transport instead of hitting the network.
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, Optional

import httpx

from hedgecanvas.live.states import MarketState

DERIBIT_PRODUCTION_BASE_URL = "https://www.deribit.com/api/v2"

DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_READ_TIMEOUT = 10.0


class DeribitAdapterError(Exception):
    """Base class for errors raised by the low-level Deribit client."""


class DeribitNetworkError(DeribitAdapterError):
    """The request could not reach the server (connection, DNS, timeout)."""


class DeribitHTTPError(DeribitAdapterError):
    """The server responded with a non-success HTTP status code."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class DeribitRPCError(DeribitAdapterError):
    """The server returned a well-formed JSON-RPC error object."""

    def __init__(self, code: Any, message: str) -> None:
        super().__init__(message)
        self.code = code


class DeribitMalformedResponseError(DeribitAdapterError):
    """The response body was not valid/expected JSON-RPC shape."""


def error_to_market_state(exc: DeribitAdapterError) -> MarketState:
    """Map a low-level client exception to a structured MarketState."""
    if isinstance(exc, DeribitNetworkError):
        return MarketState.NETWORK_ERROR
    if isinstance(exc, DeribitHTTPError):
        return MarketState.HTTP_ERROR
    if isinstance(exc, DeribitRPCError):
        return MarketState.RPC_ERROR
    if isinstance(exc, DeribitMalformedResponseError):
        return MarketState.MALFORMED_RESPONSE
    return MarketState.MALFORMED_RESPONSE


class DeribitClient:
    """Synchronous public-only Deribit JSON-RPC client.

    No credentials are accepted or stored. Only ``public/*`` methods are
    intended to be called through this client.
    """

    def __init__(
        self,
        http_client: Optional[httpx.Client] = None,
        base_url: str = DERIBIT_PRODUCTION_BASE_URL,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
    ) -> None:
        self._owns_client = http_client is None
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client or httpx.Client(
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=read_timeout,
                pool=read_timeout,
            )
        )
        self._id_counter = itertools.count(1)

    def close(self) -> None:
        if self._owns_client:
            self._http_client.close()

    def __enter__(self) -> "DeribitClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # -- JSON-RPC plumbing --------------------------------------------------

    def _call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not method.startswith("public/"):
            raise ValueError("DeribitClient only issues public/* methods")

        payload = {
            "jsonrpc": "2.0",
            "id": next(self._id_counter),
            "method": method,
            "params": params,
        }

        try:
            response = self._http_client.post(f"{self._base_url}/{method}", json=payload)
        except httpx.TimeoutException as exc:
            raise DeribitNetworkError(f"Timed out calling {method}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise DeribitNetworkError(f"Network error calling {method}: {exc}") from exc

        if response.status_code < 200 or response.status_code >= 300:
            raise DeribitHTTPError(
                response.status_code,
                f"{method} returned HTTP {response.status_code}",
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise DeribitMalformedResponseError(
                f"{method} returned malformed JSON: {exc}"
            ) from exc

        if not isinstance(body, dict):
            raise DeribitMalformedResponseError(f"{method} returned a non-object JSON body")

        if "error" in body and body["error"] is not None:
            error = body["error"]
            code = error.get("code") if isinstance(error, dict) else None
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise DeribitRPCError(code, f"{method} RPC error: {message}")

        if "result" not in body:
            raise DeribitMalformedResponseError(f"{method} response missing 'result'")

        return body["result"]

    # -- public methods used in Phase 2 -------------------------------------

    def get_instruments(self, currency: str, kind: str = "option", expired: bool = False) -> Any:
        return self._call(
            "public/get_instruments",
            {"currency": currency, "kind": kind, "expired": expired},
        )

    def get_index_price(self, index_name: str) -> Any:
        return self._call("public/get_index_price", {"index_name": index_name})

    def get_order_book(self, instrument_name: str, depth: int = 1) -> Any:
        return self._call(
            "public/get_order_book",
            {"instrument_name": instrument_name, "depth": depth},
        )

    def test(self) -> Any:
        """Optional public connectivity check, used only by the live smoke test."""
        return self._call("public/test", {})
