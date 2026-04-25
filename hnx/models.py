"""Typed models for hnx normalized output and envelopes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NormalizedStory(BaseModel):
    type: Literal["story"]
    id: int
    title: str
    url: str | None
    author: str
    score: int
    comment_count: int
    created_at: str
    hn_url: str
    text: str | None
    kids: list[int] = Field(default_factory=list)


class NormalizedComment(BaseModel):
    type: Literal["comment"]
    id: int
    author: str | None
    created_at: str
    hn_url: str
    parent: int
    text: str | None
    kids: list[int] = Field(default_factory=list)


class NormalizedJob(BaseModel):
    type: Literal["job"]
    id: int
    title: str
    url: str | None
    author: str
    score: int
    created_at: str
    hn_url: str
    text: str | None


class NormalizedPoll(BaseModel):
    type: Literal["poll"]
    id: int
    title: str
    author: str
    score: int
    comment_count: int
    created_at: str
    hn_url: str
    text: str | None
    parts: list[int] = Field(default_factory=list)


class NormalizedPollOpt(BaseModel):
    type: Literal["pollopt"]
    id: int
    author: str
    created_at: str
    hn_url: str
    parent: int
    score: int
    text: str | None


class NormalizedTombstone(BaseModel):
    """HN returned `deleted:true` or `dead:true` for this item.

    All fields except id/hn_url are optional because HN's reduced payload
    for deleted/dead items drops most content.
    """

    type: Literal["tombstone"]
    id: int
    original_type: str | None = None
    deleted: bool = False
    dead: bool = False
    created_at: str | None = None
    hn_url: str
    parent: int | None = None
    author: str | None = None


class ThreadedComment(BaseModel):
    """A comment with nested replies, used by hnx thread."""

    type: Literal["comment"] = "comment"
    id: int
    author: str | None
    created_at: str
    hn_url: str
    parent: int
    story_id: int
    text: str | None
    score: int | None = None
    children: list[ThreadedComment] = Field(default_factory=list)


class ThreadRoot(BaseModel):
    """Root story plus nested comments, used by hnx thread."""

    type: Literal["story"] = "story"
    id: int
    title: str
    url: str | None
    author: str
    score: int
    created_at: str
    hn_url: str
    text: str | None = None
    comment_count: int = 0
    children: list[ThreadedComment] = Field(default_factory=list)


NormalizedItem = (
    NormalizedStory | NormalizedComment | NormalizedJob | NormalizedPoll | NormalizedPollOpt | NormalizedTombstone
)


class SuccessEnvelope(BaseModel):
    ok: Literal[True] = True
    data: Any  # NormalizedItem | list[NormalizedItem] | list[int]; runtime-shaped
    query: dict = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)
    raw: Any = None  # ListRaw-shaped dict | single-item dict | None


class ErrorDetail(BaseModel):
    type: Literal[
        "upstream_error",
        "transform_error",
        "not_found",
        "filtered_out",
        "invalid_input",
    ]
    message: str
    details: dict = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    ok: Literal[False] = False
    error: ErrorDetail
