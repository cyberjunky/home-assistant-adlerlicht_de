"""Constants for the Adlerlicht integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "adlerlicht_de"

BASE_URL: Final = "https://adlerlicht.de"

CONF_CITY: Final = "city"
CONF_CITY_PATH: Final = "city_path"
CONF_BUNDESLAND: Final = "bundesland"
CONF_CATEGORIES: Final = "categories"
CONF_RADIUS: Final = "radius"
CONF_MAX_REPORTS: Final = "max_reports"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=15)
DEFAULT_RADIUS_KM: Final = 0.0
DEFAULT_MAX_REPORTS: Final = 20

ATTR_CATEGORY: Final = "category"
ATTR_CATEGORY_KEY: Final = "category_key"
ATTR_ENTRY_ID: Final = "entry_id"
ATTR_LATITUDE: Final = "latitude"
ATTR_LONGITUDE: Final = "longitude"
ATTR_REPORTS: Final = "reports"
ATTR_CATEGORIES: Final = "categories"
ATTR_CITY: Final = "city"
ATTR_LOCATION: Final = "location"
ATTR_EXTERNAL_ID: Final = "external_id"
ATTR_INCIDENT_DATE: Final = "incident_date"
ATTR_INCIDENT_TIME: Final = "incident_time"
ATTR_PUBLICATION_DATE: Final = "publication_date"
ATTR_SUMMARY: Final = "summary"
ATTR_TITLE: Final = "title"
ATTR_URL: Final = "url"

# Fired on the event bus for every report that appears after the first
# refresh, so automations can trigger on it directly.
EVENT_NEW_REPORT: Final = f"{DOMAIN}_new_report"

# Category keys used by adlerlicht.de, with their German labels.
CATEGORY_LABELS: Final[dict[str, str]] = {
    "arson": "Brandstiftung",
    "assault": "Körperverletzung",
    "burglary": "Einbruch",
    "drugs": "Drogen",
    "environmental": "Umwelt",
    "extremism": "Extremismus",
    "fraud": "Betrug",
    "knife": "Messer",
    "missing": "Vermisst",
    "murder": "Tötungsdelikt",
    "other": "Sonstiges",
    "public_order": "Öffentliche Ordnung",
    "robbery": "Raub",
    "sexual": "Sexualdelikt",
    "theft": "Diebstahl",
    "traffic": "Verkehr",
    "vandalism": "Sachbeschädigung",
    "weapons": "Waffen",
}
