"""Tests for the Adlerlicht geolocation entities."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adlerlicht_de.const import (
    ATTR_CATEGORY,
    ATTR_URL,
    CONF_CATEGORIES,
    CONF_MAX_REPORTS,
    CONF_RADIUS,
    DOMAIN,
)


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, **options: object) -> list:
    """Set up the entry with optional option overrides and return its states."""
    entry.add_to_hass(hass)
    if options:
        hass.config_entries.async_update_entry(entry, options={**entry.options, **options})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return [
        state
        for state in hass.states.async_all("geo_location")
        if state.attributes.get("source") == DOMAIN
    ]


async def test_entities_created_for_each_report(
    hass: HomeAssistant, mock_get, config_entry: MockConfigEntry
) -> None:
    """Every geocoded report becomes a geolocation entity."""
    states = await _setup(hass, config_entry)

    assert len(states) == 4
    for state in states:
        # The state of a geolocation entity is its distance from home.
        assert float(state.state) >= 0
        assert state.attributes[ATTR_URL].startswith("https://adlerlicht.de/fall/")
        assert state.attributes[ATTR_CATEGORY]
        assert state.attributes["latitude"]
        assert state.attributes["longitude"]


async def test_max_reports_limits_entities(
    hass: HomeAssistant, mock_get, config_entry: MockConfigEntry
) -> None:
    """Only the newest reports are exposed when a limit is set."""
    states = await _setup(hass, config_entry, **{CONF_MAX_REPORTS: 1})

    assert len(states) == 1


async def test_category_filter(
    hass: HomeAssistant, mock_get, config_entry: MockConfigEntry
) -> None:
    """A category filter drops reports of other categories."""
    states = await _setup(hass, config_entry, **{CONF_CATEGORIES: ["__no_such_category__"]})

    assert states == []


async def test_radius_filter(hass: HomeAssistant, mock_get, config_entry: MockConfigEntry) -> None:
    """A small radius around a distant home location drops every report."""
    await hass.config.async_update(latitude=52.37, longitude=4.89)
    states = await _setup(hass, config_entry, **{CONF_RADIUS: 5})

    assert states == []
