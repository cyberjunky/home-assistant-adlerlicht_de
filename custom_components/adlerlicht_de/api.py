"""Client for the adlerlicht.de website.

adlerlicht.de offers no documented API. Two endpoints are used here:

* ``/api/location/suggest`` - the typeahead used by the site's search box. It
  returns candidate places; only entries of kind ``city`` that carry an
  ``href`` have a city page and can therefore be polled.
* ``/<city>`` - the city page. It is a server-rendered Next.js route, and its
  React Server Component payload embeds both the map points (id, latitude,
  longitude, category) and the report feed (title, summary, timestamps) for
  that city. Fetching it with the ``RSC`` header returns the payload without
  the surrounding HTML.

Joining the two embedded structures on the report id yields fully geocoded
reports from a single request, which is what the geo_location platform needs.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

# The site rejects requests without a browser-like User-Agent with HTTP 403.
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
_TIMEOUT = ClientTimeout(total=30)

# The suggest endpoint ignores anything shorter and matches literally, so a
# name typed without umlauts is retried in these spellings instead.
_MIN_QUERY_LENGTH = 2
_MAX_UMLAUT_VARIANTS = 5
_UMLAUT_DIGRAPHS = (("ae", "ä"), ("oe", "ö"), ("ue", "ü"))
_UMLAUT_VOWELS = (("a", "ä"), ("o", "ö"), ("u", "ü"))
_SHARP_S = ("ss", "ß")


class AdlerlichtError(Exception):
    """Raised when adlerlicht.de cannot be reached or returns junk."""


class UnknownCity(AdlerlichtError):
    """Raised when a city has no page on adlerlicht.de."""


@dataclass(frozen=True, slots=True)
class Place:
    """A place suggested by the site's typeahead."""

    label: str
    bundesland: str | None
    path: str


@dataclass(frozen=True, slots=True)
class Report:
    """A single police report with its location."""

    report_id: str
    title: str
    summary: str | None
    location_text: str | None
    categories: tuple[str, ...]
    latitude: float
    longitude: float
    published_at: datetime | None
    incident_date: str | None
    incident_time: str | None

    @property
    def url(self) -> str:
        """Return the public page for this report."""
        return f"{BASE_URL}/fall/{self.report_id}"

    @property
    def category(self) -> str:
        """Return the primary category."""
        return self.categories[0] if self.categories else "other"


def _scan_json(text: str, start: int) -> Any:
    """Return the JSON value that begins at ``text[start]``.

    The payload is a stream of concatenated values rather than one document,
    so the value has to be delimited by counting brackets outside of strings.
    """
    opening = text[start]
    closing = "]" if opening == "[" else "}"
    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])

    raise AdlerlichtError("Unbalanced JSON in city page payload")


def _extract(payload: str, key: str) -> Any | None:
    """Return the object or array stored under ``key`` in the payload."""
    match = re.search(rf'"{re.escape(key)}":\s*(?=[\[{{])', payload)
    if match is None:
        return None
    return _scan_json(payload, match.end())


def _umlaut_variants(query: str) -> list[str]:
    """Return the spellings to retry for a query typed without umlauts.

    Both conventions are covered: the digraphs used on keyboards without
    umlauts ("koeln", "muenchen") and a bare vowel left unmarked ("koln",
    "munchen"). Only one bare vowel is replaced per variant, which is enough
    for German city names and keeps the number of extra requests small.
    """
    if len(query) < _MIN_QUERY_LENGTH:
        return []

    lowered = query.lower()
    variants: list[str] = []

    def add(candidate: str) -> None:
        if candidate != lowered and candidate not in variants:
            variants.append(candidate)

    umlauted = lowered
    for digraph, umlaut in _UMLAUT_DIGRAPHS:
        umlauted = umlauted.replace(digraph, umlaut)

    # The umlauts and the sharp s are substituted separately as well as
    # together: applying both at once turns "duesseldorf" into "düßeldorf"
    # instead of "düsseldorf", while "giessen" needs the sharp s on its own.
    add(umlauted)
    add(lowered.replace(*_SHARP_S))
    add(umlauted.replace(*_SHARP_S))

    for index, char in enumerate(lowered):
        for vowel, umlaut in _UMLAUT_VOWELS:
            if char == vowel:
                add(f"{lowered[:index]}{umlaut}{lowered[index + 1 :]}")

    return variants[:_MAX_UMLAUT_VARIANTS]


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO timestamp as used by the site."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class AdlerlichtClient:
    """Fetch reports for a city from adlerlicht.de."""

    def __init__(self, session: ClientSession) -> None:
        """Initialise the client with a shared aiohttp session."""
        self._session = session

    async def _get(self, path: str, **kwargs: Any) -> str:
        """Perform a GET request and return the body as text."""
        headers = {"User-Agent": _USER_AGENT, **kwargs.pop("headers", {})}
        try:
            async with self._session.get(
                f"{BASE_URL}{path}", headers=headers, timeout=_TIMEOUT, **kwargs
            ) as response:
                if response.status == 404:
                    raise UnknownCity(f"{path} does not exist")
                response.raise_for_status()
                return await response.text()
        except UnknownCity:
            raise
        except (ClientError, TimeoutError) as err:
            raise AdlerlichtError(f"Error fetching {path}: {err}") from err

    async def async_suggest_cities(self, query: str) -> list[Place]:
        """Return the cities matching ``query`` that have their own page.

        The suggest endpoint matches literally, so a name typed without umlauts
        finds nothing. When the query as typed has no match, the umlaut
        spellings are tried in turn so "koeln" and "koln" still reach "Köln".
        """
        places = await self._async_suggest(query)
        if places:
            return places

        for variant in _umlaut_variants(query):
            if places := await self._async_suggest(variant):
                return places

        return []

    async def _async_suggest(self, query: str) -> list[Place]:
        """Return the cities the endpoint reports for exactly this spelling."""
        body = await self._get(
            "/api/location/suggest",
            params={"q": query},
            headers={"Accept": "application/json"},
        )
        try:
            suggestions = json.loads(body)["suggestions"]
        except (ValueError, KeyError, TypeError) as err:
            raise AdlerlichtError("Unexpected response from suggest endpoint") from err

        return [
            Place(
                label=item["label"],
                bundesland=(item.get("filter") or {}).get("bundesland"),
                path=item["href"],
            )
            for item in suggestions
            if item.get("kind") == "city" and item.get("href")
        ]

    async def async_get_reports(self, city_path: str) -> list[Report]:
        """Return the most recent geocoded reports for a city page."""
        payload = await self._get(city_path, headers={"RSC": "1"})

        points = _extract(payload, "points")
        feed = _extract(payload, "feed")
        if not isinstance(points, list) or not isinstance(feed, dict):
            raise AdlerlichtError(f"Could not read report data from {city_path}")

        coordinates = {
            point["id"]: point for point in points if isinstance(point, dict) and "id" in point
        }
        entries = feed.get("neu")
        if not isinstance(entries, list):
            raise AdlerlichtError(f"No report feed on {city_path}")

        reports: list[Report] = []
        for entry in entries:
            point = coordinates.get(entry.get("id"))
            if point is None:
                # Reports the site could not geocode have no map point and
                # cannot be shown on the map, so they are skipped.
                continue
            categories = entry.get("categories") or [point.get("cat", "other")]
            reports.append(
                Report(
                    report_id=entry["id"],
                    title=entry.get("title") or "",
                    summary=entry.get("summary"),
                    location_text=entry.get("city"),
                    categories=tuple(categories),
                    latitude=float(point["lat"]),
                    longitude=float(point["lon"]),
                    published_at=_parse_timestamp(entry.get("publishedAt")),
                    incident_date=entry.get("incidentDate"),
                    incident_time=entry.get("incidentTime"),
                )
            )

        _LOGGER.debug(
            "Fetched %s geocoded reports of %s feed entries for %s",
            len(reports),
            len(entries),
            city_path,
        )
        return reports
