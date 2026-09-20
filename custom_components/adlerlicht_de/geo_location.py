"""Geolocation platform for the Adlerlicht integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.location import distance
from homeassistant.util.unit_conversion import DistanceConverter

from .api import Report
from .const import ATTR_CITY, DOMAIN
from .coordinator import AdlerlichtConfigEntry, AdlerlichtCoordinator
from .report import report_as_dict

CATEGORY_ICONS: dict[str, str] = {
    "arson": "mdi:fire",
    "assault": "mdi:hand-back-right",
    "burglary": "mdi:door-open",
    "drugs": "mdi:pill",
    "environmental": "mdi:leaf",
    "extremism": "mdi:bullhorn",
    "fraud": "mdi:credit-card-off",
    "knife": "mdi:knife",
    "missing": "mdi:account-question",
    "murder": "mdi:skull",
    "public_order": "mdi:account-group",
    "robbery": "mdi:bag-personal-off",
    "sexual": "mdi:gender-male-female",
    "theft": "mdi:hand-coin",
    "traffic": "mdi:car-emergency",
    "vandalism": "mdi:spray",
    "weapons": "mdi:pistol",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdlerlichtConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the geolocation entities for a configured city."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _async_add_new_reports() -> None:
        """Create entities for reports that appeared since the last update."""
        current = set(coordinator.data or {})
        known.intersection_update(current)
        new = current - known
        if not new:
            return
        known.update(new)
        async_add_entities(AdlerlichtEvent(coordinator, report_id) for report_id in new)

    _async_add_new_reports()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_reports))


class AdlerlichtEvent(GeolocationEvent):
    """A single police report shown on the map."""

    _attr_should_poll = False
    _attr_source = DOMAIN
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS

    def __init__(self, coordinator: AdlerlichtCoordinator, report_id: str) -> None:
        """Initialise the entity for one report."""
        self._coordinator = coordinator
        self._report_id = report_id
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{report_id}"
        self._update_from_report(coordinator.data[report_id])

    @callback
    def _update_from_report(self, report: Report) -> None:
        """Copy the values of a report onto the entity."""
        self._report = report
        self._attr_name = report.title or report.report_id
        self._attr_latitude = report.latitude
        self._attr_longitude = report.longitude
        self._attr_icon = CATEGORY_ICONS.get(report.category, "mdi:police-badge")

    @property
    def available(self) -> bool:
        """Return whether the report is still in the current feed."""
        return self._coordinator.last_update_success and (
            self._report_id in (self._coordinator.data or {})
        )

    @property
    def distance(self) -> float | None:
        """Return the distance from home in kilometres."""
        if self.hass is None:
            return None
        metres = distance(
            self.hass.config.latitude,
            self.hass.config.longitude,
            self._report.latitude,
            self._report.longitude,
        )
        if metres is None:
            return None
        return DistanceConverter.convert(metres, UnitOfLength.METERS, UnitOfLength.KILOMETERS)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the details of the report."""
        return {ATTR_CITY: self._coordinator.city, **report_as_dict(self._report)}

    async def async_added_to_hass(self) -> None:
        """Start listening for coordinator updates."""
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        """Refresh the cached report, or remove the entity once it is gone."""
        report = (self._coordinator.data or {}).get(self._report_id)
        if report is not None:
            self._update_from_report(report)
            self.async_write_ha_state()
            return

        if self._coordinator.last_update_success:
            self.hass.async_create_task(self.async_remove(force_remove=True))
