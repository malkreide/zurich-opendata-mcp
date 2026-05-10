"""Reusable formatting helpers for tool output."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import CKAN_BASE_URL

logger = logging.getLogger(__name__)


def format_dataset_summary(dataset: dict[str, Any]) -> str:
    """Format a CKAN dataset into a readable Markdown summary."""
    title = dataset.get("title", "Unbekannt")
    name = dataset.get("name", "")
    author = dataset.get("author", "Unbekannt")
    notes = (dataset.get("notes") or "")[:300]
    license_title = dataset.get("license_title", "Unbekannt")
    num_resources = dataset.get("num_resources", 0)
    modified = dataset.get("metadata_modified", "")[:10]
    update_interval = dataset.get("updateInterval", [])
    groups = [g.get("title", g.get("name", "")) for g in dataset.get("groups", [])]
    tags = [t.get("display_name", t.get("name", "")) for t in dataset.get("tags", [])]
    resources = dataset.get("resources", [])

    url = f"{CKAN_BASE_URL}/dataset/{name}"

    lines = [
        f"### {title}",
        f"- **ID**: `{name}`",
        f"- **Autor**: {author}",
        f"- **Lizenz**: {license_title}",
        f"- **Ressourcen**: {num_resources}",
        f"- **Letzte Änderung**: {modified}",
    ]
    if update_interval:
        lines.append(f"- **Aktualisierung**: {', '.join(update_interval)}")
    if groups:
        lines.append(f"- **Kategorien**: {', '.join(groups)}")
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags[:10])}")
    if resources:
        for res in resources:
            res_id = res.get("id", "")
            res_name = res.get("name", "Unbenannt")
            res_format = res.get("format", "?")
            ds_active = " ✔ DataStore" if res.get("datastore_active") else ""
            lines.append(f"  - `{res_id}` — {res_name} ({res_format}){ds_active}")
    if notes:
        lines.append(f"- **Beschreibung**: {notes}...")
    lines.append(f"- **URL**: {url}")

    return "\n".join(lines)


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
