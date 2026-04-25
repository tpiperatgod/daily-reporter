"""Async Product Hunt GraphQL client."""

from __future__ import annotations

import asyncio
import json as jsonlib
from typing import Literal

import httpx

from phx.errors import UpstreamError

LAUNCHES_QUERY = """
query PhxLaunches($first: Int!, $postedAfter: DateTime!, $postedBefore: DateTime!) {
  posts(first: $first, postedAfter: $postedAfter, postedBefore: $postedBefore, featured: true, order: RANKING) {
    nodes {
      id
      slug
      name
      tagline
      description
      url
      website
      votesCount
      commentsCount
      dailyRank
      createdAt
      featuredAt
      thumbnail { type url videoUrl }
      makers { id name username url twitterUsername }
      topics(first: 10) { nodes { id name slug url } }
    }
    pageInfo { hasNextPage endCursor startCursor hasPreviousPage }
    totalCount
  }
}
"""

PRODUCT_QUERY = """
query PhxProduct($id: ID, $slug: String) {
  post(id: $id, slug: $slug) {
    id
    slug
    name
    tagline
    description
    url
    website
    votesCount
    commentsCount
    reviewsCount
    reviewsRating
    dailyRank
    weeklyRank
    monthlyRank
    yearlyRank
    createdAt
    featuredAt
    thumbnail { type url videoUrl }
    makers { id name username url twitterUsername headline websiteUrl }
    media { type url videoUrl }
    productLinks { type url }
    topics(first: 20) { nodes { id name slug url } }
  }
}
"""


class ProductHuntClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.producthunt.com/v2/api/graphql",
        timeout: float = 30.0,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
        retry_backoff: float = 0.5,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        self._max_attempts = max_attempts
        self._retry_backoff = retry_backoff

    async def fetch_launches(
        self,
        *,
        posted_after: str,
        posted_before: str,
        limit: int,
        include_raw: bool = False,
    ) -> tuple[dict, dict | None]:
        variables = {"first": limit, "postedAfter": posted_after, "postedBefore": posted_before}
        payload = await self._execute(operation="PhxLaunches", query=LAUNCHES_QUERY, variables=variables)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise UpstreamError("GraphQL response missing data object", details={"operation": "PhxLaunches"})
        return data, payload if include_raw else None

    async def fetch_product(
        self,
        *,
        ref: str,
        ref_type: Literal["id", "slug"],
        include_raw: bool = False,
    ) -> tuple[dict | None, dict | None]:
        variables = {
            "id": ref if ref_type == "id" else None,
            "slug": ref if ref_type == "slug" else None,
        }
        payload = await self._execute(operation="PhxProduct", query=PRODUCT_QUERY, variables=variables)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise UpstreamError("GraphQL response missing data object", details={"operation": "PhxProduct"})
        post = data.get("post")
        if post is not None and not isinstance(post, dict):
            raise UpstreamError("GraphQL post field must be object or null", details={"operation": "PhxProduct"})
        return post, payload if include_raw else None

    async def _execute(self, *, operation: str, query: str, variables: dict) -> dict:
        body = {"query": query, "variables": variables}
        last_exc: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.post("", json=body)
            except httpx.HTTPError as exc:
                last_exc = UpstreamError(
                    f"HTTP transport error: {exc}",
                    details={"operation": operation, "retryable": True},
                )
                if attempt < self._max_attempts:
                    await self._sleep(attempt)
                    continue
                raise last_exc from exc

            status = response.status_code
            if status >= 500 or status == 429:
                last_exc = UpstreamError(
                    f"Upstream HTTP {status}",
                    details={"operation": operation, "status_code": status, "retryable": True},
                )
                if attempt < self._max_attempts:
                    await self._sleep(attempt)
                    continue
                raise last_exc
            if 400 <= status < 500:
                raise UpstreamError(
                    f"Upstream HTTP {status}",
                    details={"operation": operation, "status_code": status, "retryable": False},
                )

            try:
                payload = response.json()
            except (ValueError, jsonlib.JSONDecodeError) as exc:
                raise UpstreamError(
                    f"Invalid JSON from upstream: {exc}",
                    details={"operation": operation, "status_code": status, "retryable": False},
                ) from exc
            if not isinstance(payload, dict):
                raise UpstreamError(
                    f"expected dict JSON payload, got {type(payload).__name__}",
                    details={"operation": operation, "status_code": status, "retryable": False},
                )

            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                message = "GraphQL error"
                first = errors[0]
                if isinstance(first, dict) and first.get("message"):
                    message = str(first["message"])
                raise UpstreamError(
                    message,
                    details={"operation": operation, "graphql_errors": errors},
                )

            return payload

        assert last_exc is not None
        raise last_exc

    async def _sleep(self, attempt: int) -> None:
        if self._retry_backoff <= 0:
            return
        await asyncio.sleep(self._retry_backoff * attempt)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ProductHuntClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
