"""Tests for the sensors and the event entity."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adlerlicht_de.const import EVENT_NEW_REPORT


@pytest.fixture(name="loaded_entry")
async def loaded_entry_fixture(
    hass: HomeAssistant, mock_get, config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Return an entry that has been set up."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_report_count_sensor(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """The count sensor lists every current report and counts categories."""
    state = hass.states.get("sensor.gera_reports")

    assert state is not None
    assert state.state == "4"
    assert len(state.attributes["reports"]) == 4
    assert state.attributes["Verkehr"] == 2
    assert state.attributes["Einbruch"] == 1


async def test_latest_report_sensors(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """The latest sensors describe the most recent report."""
    latest = hass.states.get("sensor.gera_latest_report")
    assert latest is not None
    assert latest.state == "2026-09-18T09:00:00+00:00"
    assert latest.attributes["title"] == "Auffahrunfall auf der Bundesstraße"
    assert latest.attributes["url"] == "https://adlerlicht.de/fall/aaa2"
    assert latest.attributes["category"] == "Verkehr"

    category = hass.states.get("sensor.gera_latest_category")
    assert category is not None
    assert category.state == "Verkehr"


async def test_event_entity_starts_idle(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """Reports already present at startup must not trigger notifications."""
    state = hass.states.get("event.gera_new_report")

    assert state is not None
    assert state.state == "unknown"


async def test_new_report_triggers_event_and_bus(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    city_body: dict[str, Any],
    set_city_page,
) -> None:
    """A report appearing later triggers the entity and fires on the bus."""
    events = []
    hass.bus.async_listen(EVENT_NEW_REPORT, events.append)

    city_body["map"]["points"].append(
        {"id": "new1", "lat": 50.885, "lon": 12.085, "cat": "burglary"}
    )
    city_body["feed"]["neu"].insert(
        0,
        {
            "id": "new1",
            "title": "Neuer Einbruch in der Innenstadt",
            "summary": "Unbekannte hebeln eine Terrassentür auf.",
            "categories": ["burglary"],
            "city": "Innenstadt, Gera",
            "publishedAt": "2026-09-18T12:00:00.000Z",
            "incidentDate": "2026-09-18",
            "incidentTime": None,
            "incidentTimePrecision": "approximate",
            "moderator": {"schlagzeile": None},
            "votesUp": 0,
            "votesDown": 0,
        },
    )
    set_city_page(city_body)

    await loaded_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["external_id"] == "new1"
    assert events[0].data["category"] == "Einbruch"
    assert events[0].data["city"] == "Gera"
    assert events[0].data["url"] == "https://adlerlicht.de/fall/new1"

    state = hass.states.get("event.gera_new_report")
    assert state is not None
    assert state.attributes["event_type"] == "burglary"
    assert state.attributes["title"] == "Neuer Einbruch in der Innenstadt"


async def test_unchanged_feed_fires_nothing(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    city_body: dict[str, Any],
    set_city_page,
) -> None:
    """Polling the same reports again must not fire the event."""
    events = []
    hass.bus.async_listen(EVENT_NEW_REPORT, events.append)

    set_city_page(city_body)
    await loaded_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert events == []
    assert hass.states.get("event.gera_new_report").state == "unknown"


async def test_report_leaving_the_feed_removes_its_entity(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    city_body: dict[str, Any],
    set_city_page,
) -> None:
    """A report that drops out of the feed loses its map entity."""
    city_body["feed"]["neu"] = [
        entry for entry in city_body["feed"]["neu"] if entry["id"] != "aaa1"
    ]
    set_city_page(city_body)

    await loaded_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    remaining = {
        state.attributes["external_id"]
        for state in hass.states.async_all("geo_location")
        if "external_id" in state.attributes
    }
    assert "aaa1" not in remaining
    assert "aaa2" in remaining
