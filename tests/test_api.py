"""Tests for the adlerlicht.de client."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from custom_components.adlerlicht_de.api import (
    AdlerlichtClient,
    AdlerlichtError,
    UnknownCity,
)


@pytest.fixture(name="asked")
def asked_fixture():
    """Patch the transport with a suggest endpoint that only knows "köln".

    It records every spelling it is asked for, which is how the tests below
    check that the umlaut retries happen in the right order and stop early.
    """
    queries: list[str] = []

    async def _get(self, path: str, **kwargs: Any) -> str:
        query = kwargs["params"]["q"]
        queries.append(query)
        suggestions = (
            [{"kind": "city", "label": "Köln", "href": "/koeln"}] if query == "köln" else []
        )
        return json.dumps({"suggestions": suggestions})

    with patch("custom_components.adlerlicht_de.api.AdlerlichtClient._get", new=_get):
        yield queries


async def test_suggest_only_returns_cities_with_a_page(mock_get, hass) -> None:
    """Streets and cities without their own page cannot be polled."""
    client = AdlerlichtClient(None)

    places = await client.async_suggest_cities("Gera")

    assert [(place.label, place.path) for place in places] == [("Gera", "/gera")]
    assert places[0].bundesland == "Thüringen"


@pytest.mark.parametrize("typed", ["koeln", "koln", "Koeln", "KOLN"])
async def test_a_name_typed_without_umlauts_still_finds_the_city(asked, typed, hass) -> None:
    """The endpoint matches literally, so the umlaut spellings are retried."""
    client = AdlerlichtClient(None)

    places = await client.async_suggest_cities(typed)

    assert [place.label for place in places] == ["Köln"]
    assert asked[0] == typed
    assert asked[-1] == "köln"


async def test_the_spelling_as_typed_is_not_retried_when_it_matches(asked, hass) -> None:
    """A query that already matches costs exactly one request."""
    client = AdlerlichtClient(None)

    places = await client.async_suggest_cities("köln")

    assert [place.label for place in places] == ["Köln"]
    assert asked == ["köln"]


async def test_a_query_that_matches_nothing_is_retried_a_bounded_number_of_times(
    asked, hass
) -> None:
    """A miss must not fan out into a request per spelling of a long name."""
    client = AdlerlichtClient(None)

    assert await client.async_suggest_cities("gelsenkirchen") == []
    assert len(asked) <= 6


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("duesseldorf", "düsseldorf"),
        ("giessen", "gießen"),
        ("muenchengladbach", "münchengladbach"),
    ],
)
async def test_umlauts_and_the_sharp_s_are_substituted_separately(
    asked, typed, expected, hass
) -> None:
    """Replacing "ue" and "ss" at once would ask for "düßeldorf"."""
    client = AdlerlichtClient(None)

    await client.async_suggest_cities(typed)

    assert expected in asked


async def test_a_single_character_is_not_retried(asked, hass) -> None:
    """The endpoint ignores one-character queries, so variants are pointless."""
    client = AdlerlichtClient(None)

    assert await client.async_suggest_cities("k") == []
    assert asked == ["k"]


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
