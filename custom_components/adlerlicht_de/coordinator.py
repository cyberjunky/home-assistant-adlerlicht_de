"""Data update coordinator for the Adlerlicht integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.location import distance

from .api import AdlerlichtClient, AdlerlichtError, Report
from .const import (
    ATTR_CITY,
    ATTR_ENTRY_ID,
    CONF_BUNDESLAND,
    CONF_CATEGORIES,
    CONF_CITY,
    CONF_CITY_PATH,
    CONF_MAX_REPORTS,
    CONF_RADIUS,
    DEFAULT_MAX_REPORTS,
    DEFAULT_RADIUS_KM,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_NEW_REPORT,
)
from .report import report_as_dict

_LOGGER = logging.getLogger(__name__)

_UNDATED = datetime.min.replace(tzinfo=UTC)


def _published_at(report: Report) -> datetime:
    """Return a sortable publication time, oldest for reports without one."""
    return report.published_at or _UNDATED


type AdlerlichtConfigEntry = ConfigEntry[AdlerlichtCoordinator]


class AdlerlichtCoordinator(DataUpdateCoordinator[dict[str, Report]]):
    """Poll a city page and keep the current set of reports."""

    config_entry: AdlerlichtConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: AdlerlichtConfigEntry) -> None:
        """Initialise the coordinator for one configured city."""
        self.city: str = config_entry.data[CONF_CITY]
        self.bundesland: str | None = config_entry.data.get(CONF_BUNDESLAND)
        # Reports that appeared in the most recent update, newest first.
        self.new_reports: list[Report] = []
        self._city_path: str = config_entry.data[CONF_CITY_PATH]
        self._client = AdlerlichtClient(async_get_clientsession(hass))
        self._seen: set[str] | None = None

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} {self.city}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    @property
    def _categories(self) -> set[str]:
        """Return the categories to keep, empty meaning all of them."""
        return set(self.config_entry.options.get(CONF_CATEGORIES) or ())

    @property
    def _radius(self) -> float:
        """Return the radius around home in kilometres, 0 meaning no limit."""
        return float(self.config_entry.options.get(CONF_RADIUS, DEFAULT_RADIUS_KM))

    @property
    def _max_reports(self) -> int:
        """Return how many reports to keep as entities."""
        return int(self.config_entry.options.get(CONF_MAX_REPORTS, DEFAULT_MAX_REPORTS))

    def _keep(self, report: Report) -> bool:
        """Return whether a report passes the configured filters."""
        categories = self._categories
        if categories and not categories.intersection(report.categories):
            return False

        radius = self._radius
        if radius > 0:
            metres = distance(
                self.hass.config.latitude,
                self.hass.config.longitude,
                report.latitude,
                report.longitude,
            )
            if metres is None or metres / 1000 > radius:
                return False

        return True

    async def _async_update_data(self) -> dict[str, Report]:
        """Fetch the city page and return the reports to expose."""
        try:
            reports = await self._client.async_get_reports(self._city_path)
        except AdlerlichtError as err:
            raise UpdateFailed(str(err)) from err

        selected = [report for report in reports if self._keep(report)]
        selected.sort(key=_published_at, reverse=True)
        current = {report.report_id: report for report in selected[: self._max_reports]}

        self._async_track_new(current)
        return current

    @callback
    def _async_track_new(self, current: dict[str, Report]) -> None:
        """Record which reports are new and announce them on the event bus.

        The reports already present on the first refresh are not new: firing
        for those would send a notification for every report in the feed each
        time Home Assistant restarts.
        """
        if self._seen is None:
            self.new_reports = []
            self._seen = set(current)
            return

        self.new_reports = [
            report for report in current.values() if report.report_id not in self._seen
        ]
        self._seen = set(current)

        for report in self.new_reports:
            self.hass.bus.async_fire(
                EVENT_NEW_REPORT,
                {
                    ATTR_ENTRY_ID: self.config_entry.entry_id,
                    ATTR_CITY: self.city,
                    **report_as_dict(report),
                },
            )
