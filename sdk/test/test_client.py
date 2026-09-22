from __future__ import annotations

import pytest
import urllib3

from replynodes.dx import ReplyNodes, ReplyNodesError, ReplyNodesTimeoutError
from replynodes.exceptions import ApiException

from .conftest import FakeHTTPResponse


def test_uses_bearer_auth_and_exposes_intentional_methods(rest_client):
    rest_client.respond_once(FakeHTTPResponse(200, {"data": [{"title": "ok"}], "meta": {"request_id": "req_test"}}))

    client = ReplyNodes(api_key="rn_test_never_sent", base_url="https://test.invalid")
    assert callable(client.youtube.search)
    assert not hasattr(client, "google_news")

    result = client.youtube.search(term="test")
    assert result.meta.request_id == "req_test"

    call = rest_client.calls[0]
    assert call["url"] == "https://test.invalid/v1/youtube/search?term=test"
    assert call["headers"]["Authorization"] == "Bearer rn_test_never_sent"


def test_base_url_v1_suffix_is_not_duplicated(rest_client):
    rest_client.respond_once(FakeHTTPResponse(200, {"data": [], "meta": {"request_id": "req_v1"}}))

    client = ReplyNodes(api_key="key", base_url="https://test.invalid/v1/")
    client.youtube.search(term="test")

    assert rest_client.calls[0]["url"] == "https://test.invalid/v1/youtube/search?term=test"


def test_web_brand_and_web_search_use_generated_paths_and_query_params(rest_client):
    rest_client.respond_with(lambda _call: FakeHTTPResponse(200, {"data": [], "meta": {"request_id": "req_web"}}))

    client = ReplyNodes(api_key="key", base_url="https://test.invalid")
    assert client.google.search is client.web.search

    brand = client.web.brand(url="https://example.com/brand page")
    assert brand.meta.request_id == "req_web"
    assert rest_client.calls[0]["url"] == (
        "https://test.invalid/v1/webcontext/brand?url=https%3A//example.com/brand%20page"
    )

    client.web.search(
        text="reply nodes",
        engines="google,bing",
        lang="en",
        region="us",
        var_date="2025-01-01",
        site="example.com",
        limit=10,
        start=20,
        cursor="next page",
    )
    second = rest_client.calls[1]
    assert second["url"] == (
        "https://test.invalid/v1/web/search?text=reply%20nodes&engines=google%2Cbing&lang=en&region=us"
        "&date=2025-01-01&site=example.com&limit=10&start=20&cursor=next%20page"
    )
    assert second["headers"]["Authorization"] == "Bearer key"


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.replynodes.com",
        "https://api.replynodes.com/v1",
        "http://localhost:8787",
        "https://test.invalid",
        None,
    ],
)
def test_accepts_official_api_and_allowed_test_origins(base_url):
    ReplyNodes(api_key="key", base_url=base_url)


@pytest.mark.parametrize(
    "base_url",
    ["not-a-url", "https://attacker.invalid", "http://api.replynodes.com", "https://api.replynodes.com.evil"],
)
def test_rejects_untrusted_base_url_before_sending_bearer_key(base_url, rest_client):
    with pytest.raises(ValueError, match="base_url"):
        ReplyNodes(api_key="rn_secret", base_url=base_url)
    assert rest_client.calls == []


@pytest.mark.parametrize("base_url", ["https://test.invalid?query=not-a-base", "https://test.invalid/v1#fragment"])
def test_rejects_base_url_query_or_fragment(base_url):
    with pytest.raises(ValueError, match="base_url"):
        ReplyNodes(api_key="key", base_url=base_url)


def test_requires_api_key():
    with pytest.raises(ValueError, match="api_key"):
        ReplyNodes(api_key="")


@pytest.mark.parametrize("timeout", [0, -1, "10"])
def test_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError, match="timeout"):
        ReplyNodes(api_key="key", timeout=timeout)


def test_missing_success_request_id_raises_because_schema_marks_it_required(rest_client):
    # The canonical contract marks meta.request_id as required even though the
    # backend may omit it (documented in README.md and the merged TypeScript
    # reference's sdk/README.md). Unlike the TS wrapper -- which just returns
    # `undefined` -- the generated pydantic model enforces the schema, so a
    # response missing request_id surfaces as a pydantic ValidationError
    # rather than a value with request_id=None. This test documents that
    # current, intentional-until-the-schema-is-fixed behavior.
    rest_client.respond_once(FakeHTTPResponse(200, {"data": [], "meta": {}}))
    client = ReplyNodes(api_key="key", base_url="https://test.invalid")
    with pytest.raises(Exception) as exc_info:
        client.web.scrape(url="https://example.com")
    assert "request_id" in str(exc_info.value)


def test_maps_api_errors_with_request_id_and_never_retries(rest_client):
    rest_client.respond_with(
        lambda _call: FakeHTTPResponse(
            400, {"error": {"code": "bad_request", "message": "Nope", "request_id": "req_error"}}
        )
    )
    client = ReplyNodes(api_key="key", base_url="https://test.invalid")
    with pytest.raises(ReplyNodesError) as exc_info:
        client.reddit.search(query="x")

    error = exc_info.value
    assert error.status == 400
    assert error.code == "bad_request"
    assert error.request_id == "req_error"
    assert len(rest_client.calls) == 1


def test_falls_back_to_x_request_id_header_for_errors(rest_client):
    rest_client.respond_once(
        FakeHTTPResponse(
            400,
            {"error": {"code": "bad_request", "message": "Nope"}},
            headers={"x-request-id": "req_header"},
        )
    )
    client = ReplyNodes(api_key="key", base_url="https://test.invalid")
    with pytest.raises(ReplyNodesError) as exc_info:
        client.reddit.search(query="x")
    assert exc_info.value.request_id == "req_header"


def test_preserves_documented_402_payment_error_shape_and_request_id(rest_client):
    payment = {
        "x402Version": 2,
        "error": "Payment Required",
        "resource": {"url": "https://api.replynodes.com"},
        "accepts": [],
        "extensions": {},
    }
    rest_client.respond_once(FakeHTTPResponse(402, payment, headers={"x-request-id": "req_payment"}))
    client = ReplyNodes(api_key="key", base_url="https://test.invalid")
    with pytest.raises(ReplyNodesError) as exc_info:
        client.web.scrape(url="https://example.com")

    error = exc_info.value
    assert error.status == 402
    assert error.request_id == "req_payment"
    assert error.details == payment


def test_enforces_timeout_without_retry(rest_client):
    def raise_timeout(_call):
        return urllib3.exceptions.ReadTimeoutError(None, "https://test.invalid/v1/webcontext/scrape", "Read timed out.")

    rest_client.respond_with(raise_timeout)
    client = ReplyNodes(api_key="key", base_url="https://test.invalid", timeout=0.01)
    with pytest.raises(ReplyNodesTimeoutError):
        client.web.scrape(url="https://example.com")
    assert len(rest_client.calls) == 1
    assert rest_client.calls[0]["_request_timeout"] == 0.01


def test_max_retry_error_wrapping_timeout_is_reported_as_timeout(rest_client):
    def raise_wrapped_timeout(_call):
        reason = urllib3.exceptions.ConnectTimeoutError(None, "connect timed out")
        return urllib3.exceptions.MaxRetryError(None, "https://test.invalid/v1/webcontext/scrape", reason=reason)

    rest_client.respond_with(raise_wrapped_timeout)
    client = ReplyNodes(api_key="key", base_url="https://test.invalid", timeout=0.01)
    with pytest.raises(ReplyNodesTimeoutError):
        client.web.scrape(url="https://example.com")


def test_max_retry_error_without_timeout_cause_propagates_unchanged(rest_client):
    # NewConnectionError is (perhaps surprisingly) a urllib3.exceptions.TimeoutError
    # subclass, so it is intentionally treated as a timeout above. SSLError is
    # not, and is used here to prove genuinely unrelated MaxRetryError causes
    # are never misreported as a client-side deadline.
    def raise_ssl_error(_call):
        reason = urllib3.exceptions.SSLError("certificate verify failed")
        return urllib3.exceptions.MaxRetryError(None, "https://test.invalid/v1/webcontext/scrape", reason=reason)

    rest_client.respond_with(raise_ssl_error)
    client = ReplyNodes(api_key="key", base_url="https://test.invalid")
    with pytest.raises(urllib3.exceptions.MaxRetryError):
        client.web.scrape(url="https://example.com")


def test_retries_are_explicitly_disabled():
    client = ReplyNodes(api_key="key", base_url="https://test.invalid")
    assert client._api_client.configuration.retries is False


def test_no_timeout_by_default_omits_request_timeout_kwarg(rest_client):
    rest_client.respond_once(FakeHTTPResponse(200, {"data": [], "meta": {"request_id": "req"}}))
    client = ReplyNodes(api_key="key", base_url="https://test.invalid")
    client.web.scrape(url="https://example.com")
    assert rest_client.calls[0]["_request_timeout"] is None
