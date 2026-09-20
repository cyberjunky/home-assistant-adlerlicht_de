"""Tests for setting up and filtering an Adlerlicht entry."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adlerlicht_de.const import (
    CONF_CATEGORIES,
    CONF_MAX_REPORTS,
    CONF_RADIUS,
)

# The fixture places three reports around Gera and one in Berlin.
GERA_LATITUDE = 50.88
GERA_LONGITUDE = 12.08


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, **options: Any) -> dict[str, Any]:
    """Set up the entry with optional option overrides and return its reports."""
    entry.add_to_hass(hass)
    if options:
        hass.config_entries.async_update_entry(entry, options={**entry.options, **options})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data.data


async def test_setup_and_unload(
    hass: HomeAssistant, mock_get, config_entry: MockConfigEntry
) -> None:
    """The entry loads and unloads cleanly."""
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_fails_when_site_is_unreachable(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """An unreachable site leaves the entry in the retry state."""
    from unittest.mock import patch

    from custom_components.adlerlicht_de.api import AdlerlichtError

    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.adlerlicht_de.api.AdlerlichtClient._get",
        side_effect=AdlerlichtError("boom"),
    ):
        assert not await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_category_filter(
    hass: HomeAssistant, mock_get, config_entry: MockConfigEntry
) -> None:
    """Only reports in the selected categories are kept."""
    reports = await _setup(hass, config_entry, **{CONF_CATEGORIES: ["traffic"]})

    assert {report.category for report in reports.values()} == {"traffic"}


async def test_radius_filter(hass: HomeAssistant, mock_get, config_entry: MockConfigEntry) -> None:
    """Reports outside the radius around home are dropped."""
    await hass.config.async_update(latitude=GERA_LATITUDE, longitude=GERA_LONGITUDE)

    reports = await _setup(hass, config_entry, **{CONF_RADIUS: 25})

    # The Berlin report is roughly 200 km away and must be gone.
    assert "aaa4" not in reports
    assert "aaa1" in reports


async def test_max_reports(hass: HomeAssistant, mock_get, config_entry: MockConfigEntry) -> None:
    """Only the newest reports are kept."""
    reports = await _setup(hass, config_entry, **{CONF_MAX_REPORTS: 2})

    assert list(reports) == ["aaa2", "aaa1"]


async def test_options_change_reloads_entry(
    hass: HomeAssistant, mock_get, config_entry: MockConfigEntry
) -> None:
    """Changing the options re-applies the filters."""
    await _setup(hass, config_entry)
    assert len(config_entry.runtime_data.data) == 4

    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, CONF_MAX_REPORTS: 1}
    )
    await hass.async_block_till_done()

    assert len(config_entry.runtime_data.data) == 1
