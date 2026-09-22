from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

import pytest
import urllib3

from replynodes.rest import RESTResponse


class FakeHTTPResponse:
    def __init__(self, status: int, body: Any, headers: Optional[Dict[str, str]] = None, reason: str = "") -> None:
        self.status = status
        self.reason = reason
        self.data = json.dumps(body).encode("utf-8") if not isinstance(body, (bytes, type(None))) else body
        self.headers = urllib3.HTTPHeaderDict(headers or {})
        self.headers.setdefault("content-type", "application/json")


class RecordingRestClient:
    """Patches replynodes.rest.RESTClientObject.request to avoid real HTTP calls."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: List[Dict[str, Any]] = []
        self._responder: Callable[[Dict[str, Any]], Any] = lambda call: FakeHTTPResponse(200, {"data": [], "meta": {"request_id": "req_default"}})

        recorder = self

        def request(_rest_client_obj, method, url, headers=None, body=None, post_params=None, _request_timeout=None):
            call = {
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
                "post_params": post_params,
                "_request_timeout": _request_timeout,
            }
            recorder.calls.append(call)
            result = recorder._responder(call)
            if isinstance(result, BaseException):
                raise result
            return RESTResponse(result)

        # `request` is a plain function (not a bound method) so assigning it
        # as a class attribute preserves normal descriptor binding, i.e. the
        # patched RESTClientObject instance is still passed as the first arg.
        monkeypatch.setattr("replynodes.rest.RESTClientObject.request", request)

    def respond_with(self, responder: Callable[[Dict[str, Any]], Any]) -> None:
        self._responder = responder

    def respond_once(self, result: Any) -> None:
        self.respond_with(lambda _call: result)


@pytest.fixture
def rest_client(monkeypatch: pytest.MonkeyPatch) -> RecordingRestClient:
    return RecordingRestClient(monkeypatch)
