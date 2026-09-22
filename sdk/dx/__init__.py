"""Thin, hand-written developer experience layer over the generated ReplyNodes client.

This package is never touched by ``scripts/generate.sh``; only files under
``replynodes.api``, ``replynodes.models``, and the top-level generated modules
(``replynodes/__init__.py``, ``api_client.py``, ``configuration.py``,
``exceptions.py``, ``rest.py``, ``api_response.py``) are regenerated from the
canonical OpenAPI contract. Resource/method naming mirrors the merged
TypeScript reference SDK (replynodes/replynodes-typescript sdk/src/index.ts)
translated to idiomatic Python (snake_case attributes/methods instead of
camelCase; a client instance instead of a factory function).

Public surface:

* ``ReplyNodes(api_key, base_url=None, timeout=None)`` -- the client.
* ``ReplyNodesError`` -- raised for HTTP error responses; carries
  ``status``, ``code``, ``request_id`` and ``details``.
* ``ReplyNodesTimeoutError`` -- raised when ``timeout`` (seconds) elapses.
* ``PUBLIC_OPERATION_REGISTRY`` -- resource -> {method: operationId} for the
  canonical GET operations this wrapper exposes; used by
  ``scripts/check_surface_coverage.py`` to prevent silent surface drift.
"""
from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import urllib3

from replynodes.api.app_store_api import AppStoreApi
from replynodes.api.brand_api import BrandApi
from replynodes.api.fomo_api import FomoApi
from replynodes.api.google_api import GoogleApi
from replynodes.api.google_maps_api import GoogleMapsApi
from replynodes.api.google_play_api import GooglePlayApi
from replynodes.api.google_shopping_api import GoogleShoppingApi
from replynodes.api.hacker_news_api import HackerNewsApi
from replynodes.api.instagram_api import InstagramApi
from replynodes.api.reddit_api import RedditApi
from replynodes.api.tiktok_api import TiktokApi
from replynodes.api.web_api import WebApi
from replynodes.api.youtube_api import YoutubeApi
from replynodes.api_client import ApiClient
from replynodes.configuration import Configuration
from replynodes.exceptions import ApiException

__all__ = [
    "ReplyNodes",
    "ReplyNodesError",
    "ReplyNodesTimeoutError",
    "PUBLIC_OPERATION_REGISTRY",
]

_OFFICIAL_API_ORIGIN = "https://api.replynodes.com"
_SAFE_TEST_ORIGINS = {"https://test.invalid"}
_LOCAL_TEST_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}

# The intentional public name for every canonical operation. Values are the
# generated operation IDs; this wrapper never constructs HTTP requests
# itself, it only binds generated methods under intentional resource/action
# names. ``web.search`` is a backward-compatible alias for ``google.search``
# (both resolve to the ``googleSearch`` operation), matching the naming
# convention documented in replynodes-fetcher/docs/sdk-openapi-naming.md.
PUBLIC_OPERATION_REGISTRY: Dict[str, Dict[str, str]] = {
    "app_store": {
        "app": "appStoreApp",
        "developer": "appStoreDeveloper",
        "list": "appStoreList",
        "privacy": "appStorePrivacy",
        "ratings": "appStoreRatings",
        "reviews": "appStoreReviews",
        "search": "appStoreSearch",
        "similar": "appStoreSimilar",
        "suggest": "appStoreSuggest",
    },
    "brand": {
        "fonts": "brandFonts",
        "retrieve": "brandRetrieve",
        "search": "brandSearch",
        "styleguide": "brandStyleguide",
    },
    "fomo": {
        "alerts": "fomoAlerts",
        "leaderboard": "fomoLeaderboard",
        "notifications": "fomoNotifications",
        "search": "fomoSearch",
        "thesis": "fomoThesis",
        "thesis_by_token": "fomoThesisByToken",
        "thesis_by_user": "fomoThesisByUser",
        "thesis_by_user_token": "fomoThesisByUserToken",
        "token_holders": "fomoTokenHolders",
        "tokens_graduated": "fomoTokensGraduated",
        "tokens_most_held": "fomoTokensMostHeld",
        "tokens_trending": "fomoTokensTrending",
        "trade": "fomoTrade",
        "user_balances": "fomoUserBalances",
        "user_profile": "fomoUserProfile",
        "user_trades": "fomoUserTrades",
    },
    "google": {
        "search": "googleSearch",
    },
    "google_maps": {
        "place_details": "googleMapsPlaceDetails",
        "place_reviews": "googleMapsPlaceReviews",
        "search_places": "googleMapsSearchPlaces",
    },
    "google_play": {
        "app_details": "googlePlayAppDetails",
        "availability": "googlePlayAvailability",
        "categories": "googlePlayCategories",
        "category_apps": "googlePlayCategoryApps",
        "data_safety": "googlePlayDataSafety",
        "developer": "googlePlayDeveloper",
        "permissions": "googlePlayPermissions",
        "reviews": "googlePlayReviews",
        "search": "googlePlaySearch",
        "similar_apps": "googlePlaySimilarApps",
        "suggest": "googlePlaySuggest",
    },
    "google_shopping": {
        "product_offers": "googleShoppingProductOffers",
        "search": "googleShoppingSearch",
    },
    "hacker_news": {
        "item": "hackerNewsItem",
        "search": "hackerNewsSearch",
        "stories_ask": "hackerNewsStoriesAsk",
        "stories_best": "hackerNewsStoriesBest",
        "stories_job": "hackerNewsStoriesJob",
        "stories_new": "hackerNewsStoriesNew",
        "stories_show": "hackerNewsStoriesShow",
        "stories_top": "hackerNewsStoriesTop",
        "user": "hackerNewsUser",
    },
    "instagram": {
        "posts": "instagramPosts",
        "profile": "instagramProfile",
    },
    "reddit": {
        "post_by_id": "redditPostById",
        "post_by_permalink": "redditPostByPermalink",
        "search": "redditSearch",
        "subreddit_posts": "redditSubredditPosts",
        "user_activity": "redditUserActivity",
        "user_posts": "redditUserPosts",
    },
    "tiktok": {
        "post": "tiktokPost",
        "user": "tiktokUser",
        "user_posts": "tiktokUserPosts",
    },
    "web": {
        "brand": "webBrand",
        "crawl": "webCrawl",
        "map": "webMap",
        "scrape": "webScrape",
        "search": "googleSearch",
    },
    "youtube": {
        "channel": "youtubeChannel",
        "comments": "youtubeComments",
        "playlist": "youtubePlaylist",
        "related": "youtubeRelated",
        "search": "youtubeSearch",
        "transcript": "youtubeTranscript",
        "video": "youtubeVideo",
    },
}

# (resource, method) -> resource whose generated API class actually
# implements the operation. Only ``web.search`` is an alias today; it is
# implemented by GoogleApi.google_search, not WebApi.
_ALIASES = {("web", "search"): "google"}

_API_CLASSES = {
    "app_store": AppStoreApi,
    "brand": BrandApi,
    "fomo": FomoApi,
    "google": GoogleApi,
    "google_maps": GoogleMapsApi,
    "google_play": GooglePlayApi,
    "google_shopping": GoogleShoppingApi,
    "hacker_news": HackerNewsApi,
    "instagram": InstagramApi,
    "reddit": RedditApi,
    "tiktok": TiktokApi,
    "web": WebApi,
    "youtube": YoutubeApi,
}


def operation_id_to_method_name(operation_id: str) -> str:
    """Convert a canonical camelCase operationId to the generated snake_case
    method name (matches OpenAPI Generator's own python naming exactly, e.g.
    ``youtubeChannel`` -> ``youtube_channel``, ``fomoThesisByToken`` ->
    ``fomo_thesis_by_token``)."""
    step1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", operation_id)
    step2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step1)
    return step2.lower()


class ReplyNodesError(Exception):
    """Raised for ReplyNodes HTTP error responses (4xx/5xx)."""

    def __init__(
        self,
        message: str,
        status: Optional[int],
        *,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.request_id = request_id
        self.details = details


class ReplyNodesTimeoutError(Exception):
    """Raised when a request exceeds the configured client ``timeout``."""

    def __init__(self, message: str = "ReplyNodes request timed out") -> None:
        super().__init__(message)


def _validate_base_url(base_url: Optional[str]) -> Optional[str]:
    if base_url is None:
        return None

    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            "ReplyNodes base_url must be an absolute URL for an allowed ReplyNodes or test origin"
        )
    if parsed.query or parsed.fragment:
        raise ValueError("ReplyNodes base_url must not include a query string or fragment")

    origin = f"{parsed.scheme}://{parsed.netloc}"
    is_local_test_origin = parsed.hostname in _LOCAL_TEST_HOSTNAMES and parsed.scheme in ("http", "https")
    if origin != _OFFICIAL_API_ORIGIN and not is_local_test_origin and origin not in _SAFE_TEST_ORIGINS:
        raise ValueError(
            "ReplyNodes base_url must use the official ReplyNodes API origin or an explicitly allowed test origin"
        )

    # Generated endpoint paths already include the public `/v1` prefix. Accept
    # the common server URL form with that suffix, but do not duplicate it.
    normalized_path = parsed.path.rstrip("/")
    if normalized_path == "/v1":
        return origin
    return base_url.rstrip("/")


def _error_details(exc: ApiException) -> Any:
    if not exc.body:
        return None
    try:
        return json.loads(exc.body)
    except (TypeError, ValueError):
        return None


def _to_replynodes_error(exc: ApiException) -> ReplyNodesError:
    details = _error_details(exc)
    error_field = details.get("error") if isinstance(details, dict) else None

    code = error_field.get("code") if isinstance(error_field, dict) else None
    message = error_field.get("message") if isinstance(error_field, dict) else None
    message = message or exc.reason or "ReplyNodes request failed"

    request_id = error_field.get("request_id") if isinstance(error_field, dict) else None
    if not request_id:
        headers = exc.headers or {}
        request_id = headers.get("X-Request-Id") or headers.get("x-request-id")

    return ReplyNodesError(message, exc.status, code=code, request_id=request_id, details=details)


class ReplyNodes:
    """ReplyNodes API client.

    ``timeout`` is a positive number of seconds applied to every request
    (unlike the merged TypeScript reference, which takes milliseconds; this
    follows Python HTTP client convention such as ``requests``/``httpx``).
    Omit it to use the platform's default (no client-side deadline).

    Retries are always explicitly disabled (``retries=False``); this SDK
    never silently retries a request, since a retried GET can still repeat a
    metered/billed read against the gateway.
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None, timeout: Optional[float] = None) -> None:
        if not api_key:
            raise ValueError("ReplyNodes requires an api_key")
        if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0):
            raise ValueError("ReplyNodes timeout must be a positive number of seconds")

        validated_base_url = _validate_base_url(base_url)
        self._timeout: Optional[float] = float(timeout) if timeout is not None else None

        configuration = Configuration(host=validated_base_url, access_token=api_key, retries=False)
        self._api_client = ApiClient(configuration)
        self._api_client.user_agent = f"replynodes-python/{_sdk_version()}"

        apis = {name: api_class(self._api_client) for name, api_class in _API_CLASSES.items()}

        bound_by_resource: Dict[str, Dict[str, Callable[..., Any]]] = {}
        for resource_name, methods in PUBLIC_OPERATION_REGISTRY.items():
            bound: Dict[str, Callable[..., Any]] = {}
            for method_name, operation_id in methods.items():
                alias_owner = _ALIASES.get((resource_name, method_name))
                if alias_owner is not None:
                    bound[method_name] = bound_by_resource[alias_owner][method_name]
                else:
                    bound[method_name] = self._bind(apis[resource_name], operation_id)
            bound_by_resource[resource_name] = bound
            setattr(self, resource_name, SimpleNamespace(**bound))

    def _bind(self, api: Any, operation_id: str) -> Callable[..., Any]:
        method_name = operation_id_to_method_name(operation_id)
        generated_method = getattr(api, method_name)

        def call(**kwargs: Any) -> Any:
            try:
                return generated_method(_request_timeout=self._timeout, **kwargs)
            except ApiException as exc:
                raise _to_replynodes_error(exc) from exc
            except urllib3.exceptions.MaxRetryError as exc:
                if isinstance(exc.reason, urllib3.exceptions.TimeoutError):
                    raise ReplyNodesTimeoutError() from exc
                raise
            except (urllib3.exceptions.ReadTimeoutError, urllib3.exceptions.ConnectTimeoutError) as exc:
                raise ReplyNodesTimeoutError() from exc

        call.__name__ = method_name
        call.__qualname__ = f"ReplyNodes.{method_name}"
        return call


def _sdk_version() -> str:
    from replynodes import __version__

    return __version__
