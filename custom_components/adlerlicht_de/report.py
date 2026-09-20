"""Shared representation of a report for entity attributes and bus events."""

from __future__ import annotations

from typing import Any

from .api import Report
from .const import (
    ATTR_CATEGORIES,
    ATTR_CATEGORY,
    ATTR_CATEGORY_KEY,
    ATTR_EXTERNAL_ID,
    ATTR_INCIDENT_DATE,
    ATTR_INCIDENT_TIME,
    ATTR_LATITUDE,
    ATTR_LOCATION,
    ATTR_LONGITUDE,
    ATTR_PUBLICATION_DATE,
    ATTR_SUMMARY,
    ATTR_TITLE,
    ATTR_URL,
    CATEGORY_LABELS,
)


def category_label(key: str) -> str:
    """Return the German label of a category, or the raw key if unknown."""
    return CATEGORY_LABELS.get(key, key)


def report_as_dict(report: Report) -> dict[str, Any]:
    """Return a report as a flat dictionary for attributes and events."""
    return {
        ATTR_EXTERNAL_ID: report.report_id,
        ATTR_TITLE: report.title,
        ATTR_SUMMARY: report.summary,
        ATTR_CATEGORY: category_label(report.category),
        ATTR_CATEGORY_KEY: report.category,
        ATTR_CATEGORIES: list(report.categories),
        ATTR_LOCATION: report.location_text,
        ATTR_PUBLICATION_DATE: report.published_at.isoformat() if report.published_at else None,
        ATTR_INCIDENT_DATE: report.incident_date,
        ATTR_INCIDENT_TIME: report.incident_time,
        ATTR_LATITUDE: report.latitude,
        ATTR_LONGITUDE: report.longitude,
        ATTR_URL: report.url,
    }
