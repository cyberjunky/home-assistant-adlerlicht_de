"""The Adlerlicht integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import AdlerlichtConfigEntry, AdlerlichtCoordinator

PLATFORMS: list[Platform] = [
    Platform.EVENT,
    Platform.GEO_LOCATION,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: AdlerlichtConfigEntry) -> bool:
    """Set up Adlerlicht from a config entry."""
    coordinator = AdlerlichtCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AdlerlichtConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: AdlerlichtConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
