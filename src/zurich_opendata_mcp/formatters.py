"""Reusable formatting helpers for tool output."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import CKAN_BASE_URL
from .models import DatasetSummary, ResourceInfo

logger = logging.getLogger(__name__)


def to_resource_info(resource: dict[str, Any]) -> ResourceInfo:
    """Map a CKAN resource dict onto the structured ``ResourceInfo`` model."""
    return ResourceInfo(
        id=resource.get("id", ""),
        name=resource.get("name") or "Unbenannt",
        format=resource.get("format") or "?",
        datastore_active=bool(resource.get("datastore_active")),
        url=resource.get("url") or None,
    )


def to_dataset_summary(dataset: dict[str, Any]) -> DatasetSummary:
    """Map a CKAN dataset dict onto the structured ``DatasetSummary`` model."""
    name = dataset.get("name", "")
    return DatasetSummary(
        id=name,
        title=dataset.get("title") or "Unbekannt",
        author=dataset.get("author") or None,
        license=dataset.get("license_title") or None,
        num_resources=dataset.get("num_resources", 0),
        modified=(dataset.get("metadata_modified") or "")[:10] or None,
        update_interval=list(dataset.get("updateInterval") or []),
        groups=[g.get("title", g.get("name", "")) for g in dataset.get("groups", [])],
        tags=[t.get("display_name", t.get("name", "")) for t in dataset.get("tags", [])],
        resources=[to_resource_info(r) for r in dataset.get("resources", [])],
        notes=((dataset.get("notes") or "")[:300]) or None,
        url=f"{CKAN_BASE_URL}/dataset/{name}",
    )


def render_dataset_summary(ds: DatasetSummary) -> str:
    """Render a ``DatasetSummary`` model as a readable Markdown summary."""
    lines = [
        f"### {ds.title}",
        f"- **ID**: `{ds.id}`",
        f"- **Autor**: {ds.author or 'Unbekannt'}",
        f"- **Lizenz**: {ds.license or 'Unbekannt'}",
        f"- **Ressourcen**: {ds.num_resources}",
        f"- **Letzte Änderung**: {ds.modified or ''}",
    ]
    if ds.update_interval:
        lines.append(f"- **Aktualisierung**: {', '.join(ds.update_interval)}")
    if ds.groups:
        lines.append(f"- **Kategorien**: {', '.join(ds.groups)}")
    if ds.tags:
        lines.append(f"- **Tags**: {', '.join(ds.tags[:10])}")
    for res in ds.resources:
        ds_active = " ✔ DataStore" if res.datastore_active else ""
        lines.append(f"  - `{res.id}` — {res.name} ({res.format}){ds_active}")
    if ds.notes:
        lines.append(f"- **Beschreibung**: {ds.notes}...")
    lines.append(f"- **URL**: {ds.url}")

    return "\n".join(lines)


def format_dataset_summary(dataset: dict[str, Any]) -> str:
    """Format a CKAN dataset into a readable Markdown summary."""
    return render_dataset_summary(to_dataset_summary(dataset))


def format_resource_info(resource: dict[str, Any]) -> str:
    """Format a CKAN resource into a readable summary."""
    res_id = resource.get("id", "")
    ds_active = " ✔ DataStore" if resource.get("datastore_active") else ""
    return (
        f"  - `{res_id}` **{resource.get('name', 'Unbenannt')}** "
        f"({resource.get('format', '?')}){ds_active} – "
        f"{resource.get('url', 'Keine URL')}"
    )


def md_cell(value: object) -> str:
    # Markdown table cells break on '|' and on line breaks. Upstream APIs
    # (ParkenDD lot names, hystreet weather labels) occasionally return both,
    # so escape pipes and collapse whitespace before interpolating.
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def handle_api_error(e: Exception, context: str = "") -> str:
    """Consistent error formatting. Also logs the failure so stdio
    deployments leave a trail when an upstream API hiccups."""
    logger.warning(
        "API error in %s: %s: %s",
        context or "tool",
        type(e).__name__,
        e,
        exc_info=True,
    )
    prefix = f"Fehler bei {context}: " if context else "Fehler: "
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 404:
            return f"{prefix}Ressource nicht gefunden. Bitte ID/Name prüfen."
        elif status == 403:
            return f"{prefix}Zugriff verweigert."
        elif status == 429:
            return f"{prefix}Zu viele Anfragen. Bitte warten."
        return f"{prefix}HTTP-Fehler {status}"
    elif isinstance(e, httpx.TimeoutException):
        return f"{prefix}Zeitüberschreitung. Bitte erneut versuchen."
    return f"{prefix}{type(e).__name__}: {e}"
