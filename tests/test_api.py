"""Tests for the adlerlicht.de client."""

from __future__ import annotations

import pytest

from custom_components.adlerlicht_de.api import (
    AdlerlichtClient,
    AdlerlichtError,
    UnknownCity,
)


async def test_suggest_only_returns_cities_with_a_page(mock_get, hass) -> None:
    """Streets and cities without their own page cannot be polled."""
    client = AdlerlichtClient(None)

    places = await client.async_suggest_cities("Gera")

    assert [(place.label, place.path) for place in places] == [("Gera", "/gera")]
    assert places[0].bundesland == "Thüringen"


async def test_reports_are_joined_with_their_coordinates(mock_get, hass) -> None:
    """Feed entries are returned with the coordinates of their map point."""
    client = AdlerlichtClient(None)

    reports = await client.async_get_reports("/gera")

    by_id = {report.report_id: report for report in reports}
    assert by_id["aaa1"].latitude == 50.88
    assert by_id["aaa1"].longitude == 12.08
    assert by_id["aaa1"].category == "assault"
    assert by_id["aaa1"].url == "https://adlerlicht.de/fall/aaa1"
    assert by_id["aaa2"].published_at is not None


async def test_reports_without_coordinates_are_skipped(mock_get, hass) -> None:
    """A report the site could not geocode cannot be shown on a map."""
    client = AdlerlichtClient(None)

    reports = await client.async_get_reports("/gera")

    assert "ungeocoded" not in {report.report_id for report in reports}
    assert len(reports) == 4


async def test_unknown_city_raises(mock_get, hass) -> None:
    """A city without a page raises a dedicated error."""
    client = AdlerlichtClient(None)

    with pytest.raises(UnknownCity):
        await client.async_get_reports("/nonexistent")


async def test_unreadable_payload_raises(hass) -> None:
    """A page without the expected structure is reported as an error."""
    client = AdlerlichtClient(None)

    async def _get(path: str, **kwargs: object) -> str:
        return '1:"$Sreact.fragment"\n'

    client._get = _get

    with pytest.raises(AdlerlichtError):
        await client.async_get_reports("/gera")
