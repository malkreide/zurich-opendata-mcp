"""Structured output models for the catalog tools.

These tools feed their results back into follow-up tool calls (search →
get_dataset → datastore query), so the dataset/resource IDs must travel
machine-readably rather than buried in Markdown prose. Each tool therefore
returns *both* a human-readable Markdown ``content`` block and a validated
``structuredContent`` JSON payload, via ``Annotated[CallToolResult, Model]``.

The ``error`` field plus permissive defaults let the error path emit a
schema-valid payload (``structuredContent`` is validated even on failure).
"""

from __future__ import annotations

from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field


class ResourceInfo(BaseModel):
    """A single downloadable resource of a dataset."""

    id: str = Field(description="Resource UUID — use as resource_id for DataStore queries")
    name: str
    format: str
    datastore_active: bool = Field(
        default=False,
        description="True if the resource is queryable via the CKAN DataStore API",
    )
    url: str | None = None


class DatasetSummary(BaseModel):
    """Compact, machine-readable view of a CKAN dataset."""

    id: str = Field(description="CKAN dataset name/slug — use as dataset_id in zurich_get_dataset")
    title: str
    author: str | None = None
    license: str | None = None
    num_resources: int = 0
    modified: str | None = Field(default=None, description="Last modified date (YYYY-MM-DD)")
    update_interval: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    resources: list[ResourceInfo] = Field(default_factory=list)
    notes: str | None = None
    url: str


class SearchResult(BaseModel):
    """Result of a dataset search."""

    query: str
    total: int = 0
    count: int = Field(default=0, description="Number of datasets in this page")
    offset: int = 0
    next_offset: int | None = Field(
        default=None, description="Offset for the next page, or null if exhausted"
    )
    datasets: list[DatasetSummary] = Field(default_factory=list)
    error: str | None = None


class GetDatasetResult(BaseModel):
    """Full metadata for a single dataset."""

    dataset: DatasetSummary | None = None
    extras: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class FieldInfo(BaseModel):
    """A DataStore field (column) definition."""

    id: str
    type: str


class DatasetAnalysis(BaseModel):
    """Per-dataset slice of an analysis run."""

    id: str
    title: str
    formats: list[str] = Field(default_factory=list)
    resources: list[ResourceInfo] = Field(default_factory=list)
    modified: str | None = None
    update_interval: list[str] = Field(default_factory=list)
    datastore_records: int | None = None
    fields: list[FieldInfo] | None = None
    url: str


class AnalysisResult(BaseModel):
    """Result of an analysis run across several datasets."""

    query: str
    total: int = 0
    analyzed: int = 0
    datasets: list[DatasetAnalysis] = Field(default_factory=list)
    error: str | None = None


def tool_result(markdown: str, model: BaseModel, *, is_error: bool = False) -> CallToolResult:
    """Bundle a Markdown ``content`` block with a validated structured payload.

    FastMCP validates ``structuredContent`` against the tool's output model on
    every call (success and error alike), so callers must pass a fully-valid
    model instance — the permissive defaults on the result models make the
    error path (empty data + ``error`` message) valid.
    """
    structured: dict[str, Any] = model.model_dump(mode="json")
    return CallToolResult(
        content=[TextContent(type="text", text=markdown)],
        structuredContent=structured,
        isError=is_error,
    )
