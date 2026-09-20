"""Base entity for the Adlerlicht integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN
from .coordinator import AdlerlichtCoordinator


class AdlerlichtEntity(CoordinatorEntity[AdlerlichtCoordinator]):
    """An entity belonging to one configured city."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AdlerlichtCoordinator, key: str) -> None:
        """Initialise the entity for a configured city."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="adlerlicht.de",
            name=coordinator.city,
            model=coordinator.bundesland or "Deutschland",
            configuration_url=f"{BASE_URL}{coordinator.config_entry.data['city_path']}",
        )
