"""Tests for the Adlerlicht config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adlerlicht_de.const import (
    CONF_CATEGORIES,
    CONF_CITY,
    CONF_CITY_PATH,
    CONF_MAX_REPORTS,
    CONF_RADIUS,
    DOMAIN,
)


async def test_single_match_creates_entry(hass: HomeAssistant, mock_get) -> None:
    """A search matching one city skips the selection step."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"query": "Gera"})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Gera"
    assert result["data"][CONF_CITY] == "Gera"
    assert result["data"][CONF_CITY_PATH] == "/gera"


async def test_unknown_city_shows_error(hass: HomeAssistant, mock_get) -> None:
    """A search without a usable city keeps the user on the form."""
    import json

    with patch(
        "custom_components.adlerlicht_de.api.AdlerlichtClient._get",
        return_value=json.dumps({"suggestions": []}),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"query": "Nirgendwo"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"query": "no_city_found"}


async def test_connection_error_shows_error(hass: HomeAssistant) -> None:
    """A failing request keeps the user on the form."""
    from custom_components.adlerlicht_de.api import AdlerlichtError

    with patch(
        "custom_components.adlerlicht_de.api.AdlerlichtClient._get",
        side_effect=AdlerlichtError("boom"),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"query": "Gera"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_city_aborts(
    hass: HomeAssistant, mock_get, config_entry: MockConfigEntry
) -> None:
    """The same city cannot be added twice."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"query": "Gera"})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, mock_get, config_entry: MockConfigEntry) -> None:
    """The options flow stores the filters."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_CATEGORIES: ["traffic"], CONF_RADIUS: 25, CONF_MAX_REPORTS: 5},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_CATEGORIES] == ["traffic"]
    assert config_entry.options[CONF_RADIUS] == 25.0
    assert config_entry.options[CONF_MAX_REPORTS] == 5


async def test_multiple_matches_show_selection_step(hass: HomeAssistant, mock_get) -> None:
    """A search matching several cities asks which one to add."""
    import json

    suggestions = json.dumps(
        {
            "suggestions": [
                {
                    "kind": "city",
                    "label": "Neustadt",
                    "href": "/neustadt-sachsen",
                    "filter": {"bundesland": "Sachsen"},
                },
                {
                    "kind": "city",
                    "label": "Neustadt",
                    "href": "/neustadt-hessen",
                    "filter": {"bundesland": "Hessen"},
                },
            ]
        }
    )
    mock_get["/api/location/suggest"] = suggestions

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"query": "Neustadt"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "place"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"place": "/neustadt-hessen"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CITY_PATH] == "/neustadt-hessen"
