"""phx product command orchestration."""

from __future__ import annotations

from typing import Literal

from phx.client import ProductHuntClient
from phx.errors import InvalidInputError, NotFoundError
from phx.models import SuccessEnvelope
from phx.transform import normalize_product_detail

RefType = Literal["id", "slug"]
RefSource = Literal["auto", "explicit"]


def classify_product_ref(ref: str, *, force_id: bool = False, force_slug: bool = False) -> tuple[RefType, RefSource]:
    if force_id and force_slug:
        raise InvalidInputError("--id and --slug are mutually exclusive")
    if force_id:
        return "id", "explicit"
    if force_slug:
        return "slug", "explicit"
    if ref.isdigit():
        return "id", "auto"
    return "slug", "auto"


async def fetch_product(
    *,
    client: ProductHuntClient,
    ref: str,
    force_id: bool = False,
    force_slug: bool = False,
    include_raw: bool = False,
) -> SuccessEnvelope:
    ref_type, ref_source = classify_product_ref(ref, force_id=force_id, force_slug=force_slug)
    post, raw = await client.fetch_product(ref=ref, ref_type=ref_type, include_raw=include_raw)
    if post is None:
        raise NotFoundError(f"Product Hunt product not found: {ref}")
    detail = normalize_product_detail(post)
    return SuccessEnvelope(
        data=detail.model_dump(),
        query={
            "command": "product",
            "ref": ref,
            "ref_type": ref_type,
            "ref_source": ref_source,
            "raw": include_raw,
        },
        meta={"source": "producthunt_graphql", "returned": 1},
        raw=raw,
    )
