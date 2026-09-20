"""Sensor platform for the Adlerlicht integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import Report
from .const import ATTR_REPORTS, CATEGORY_LABELS
from .coordinator import AdlerlichtConfigEntry, AdlerlichtCoordinator
from .entity import AdlerlichtEntity
from .report import category_label, report_as_dict


def _newest(coordinator: AdlerlichtCoordinator) -> Report | None:
    """Return the most recent report, if there is one."""
    reports = coordinator.data or {}
    return next(iter(reports.values()), None)


@dataclass(frozen=True, kw_only=True)
class AdlerlichtSensorDescription(SensorEntityDescription):
    """Describes an Adlerlicht sensor."""

    value_fn: Callable[[AdlerlichtCoordinator], Any]
    attributes_fn: Callable[[AdlerlichtCoordinator], dict[str, Any]] | None = None


def _latest_value(coordinator: AdlerlichtCoordinator) -> datetime | None:
    """Return the publication time of the most recent report."""
    report = _newest(coordinator)
    return report.published_at if report else None


def _latest_attributes(coordinator: AdlerlichtCoordinator) -> dict[str, Any]:
    """Return the details of the most recent report."""
    report = _newest(coordinator)
    return report_as_dict(report) if report else {}


def _count_attributes(coordinator: AdlerlichtCoordinator) -> dict[str, Any]:
    """Return every current report, so templates can iterate over them."""
    reports = coordinator.data or {}
    return {ATTR_REPORTS: [report_as_dict(report) for report in reports.values()]}


def _category_counts(coordinator: AdlerlichtCoordinator) -> dict[str, Any]:
    """Return how many current reports each category has."""
    counts: dict[str, int] = {}
    for report in (coordinator.data or {}).values():
        for category in report.categories:
            counts[category_label(category)] = counts.get(category_label(category), 0) + 1
    return dict(sorted(counts.items()))


SENSORS: tuple[AdlerlichtSensorDescription, ...] = (
    AdlerlichtSensorDescription(
        key="report_count",
        translation_key="report_count",
        icon="mdi:police-badge",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="reports",
        value_fn=lambda coordinator: len(coordinator.data or {}),
        attributes_fn=lambda coordinator: {
            **_count_attributes(coordinator),
            **_category_counts(coordinator),
        },
    ),
    AdlerlichtSensorDescription(
        key="latest_report",
        translation_key="latest_report",
        icon="mdi:newspaper-variant-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_latest_value,
        attributes_fn=_latest_attributes,
    ),
    AdlerlichtSensorDescription(
        key="latest_category",
        translation_key="latest_category",
        icon="mdi:shape-outline",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(CATEGORY_LABELS.values())),
        value_fn=lambda coordinator: (
            category_label(report.category) if (report := _newest(coordinator)) else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdlerlichtConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors for a configured city."""
    coordinator = entry.runtime_data
    async_add_entities(AdlerlichtSensor(coordinator, description) for description in SENSORS)


class AdlerlichtSensor(AdlerlichtEntity, SensorEntity):
    """A sensor summarising the reports of one city."""

    entity_description: AdlerlichtSensorDescription

    def __init__(
        self,
        coordinator: AdlerlichtCoordinator,
        description: AdlerlichtSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the current value of the sensor."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the extra attributes of the sensor."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator)
