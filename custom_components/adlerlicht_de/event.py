"""Event platform for the Adlerlicht integration."""

from __future__ import annotations

from typing import Final

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CATEGORY_LABELS
from .coordinator import AdlerlichtConfigEntry, AdlerlichtCoordinator
from .entity import AdlerlichtEntity
from .report import report_as_dict

# An "any category" type keeps the entity usable for categories the site adds
# after this integration was released.
EVENT_TYPE_REPORT = "report"

EVENT_TYPES: Final[list[str]] = [EVENT_TYPE_REPORT, *sorted(CATEGORY_LABELS)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdlerlichtConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event entity for a configured city."""
    async_add_entities([AdlerlichtNewReportEvent(entry.runtime_data)])


class AdlerlichtNewReportEvent(AdlerlichtEntity, EventEntity):
    """Fires whenever a new report appears for the configured city."""

    _attr_translation_key = "new_report"
    _attr_icon = "mdi:bell-alert-outline"

    def __init__(self, coordinator: AdlerlichtCoordinator) -> None:
        """Initialise the event entity."""
        super().__init__(coordinator, "new_report")
        self._attr_event_types = EVENT_TYPES

    @callback
    def _handle_coordinator_update(self) -> None:
        """Trigger the entity for every report that just appeared."""
        for report in self.coordinator.new_reports:
            event_type = (
                report.category if report.category in self._attr_event_types else EVENT_TYPE_REPORT
            )
            self._trigger_event(event_type, report_as_dict(report))
        super()._handle_coordinator_update()
