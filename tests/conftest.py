"""Fixtures for the Adlerlicht tests."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adlerlicht_de.const import (
    CONF_BUNDESLAND,
    CONF_CATEGORIES,
    CONF_CITY,
    CONF_CITY_PATH,
    CONF_MAX_REPORTS,
    CONF_RADIUS,
    DOMAIN,
)

FIXTURES = Path(__file__).parent / "fixtures"


def render_city_page(body: dict[str, Any]) -> str:
    """Return ``body`` wrapped the way a city page embeds it.

    The real page is a React Server Component stream: numbered rows, one of
    which carries the page data as JSON. The client only looks for the keys it
    needs, so the surrounding rows are reproduced only roughly.
    """
    return (
        '1:"$Sreact.fragment"\n'
        '2:I[33750,["/_next/static/chunks/45de945f3784fcac.js"],"LanguageProvider"]\n'
        f'3:["$","div",null,{{"children":{json.dumps(body, ensure_ascii=False)}}}]\n'
        "4:null\n"
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in every test."""
    return


@pytest.fixture(name="city_body")
def city_body_fixture() -> dict[str, Any]:
    """Return the data a city page embeds, as a mutable dictionary."""
    return json.loads((FIXTURES / "city_page.json").read_text(encoding="utf-8"))


@pytest.fixture(name="city_payload")
def city_payload_fixture(city_body: dict[str, Any]) -> str:
    """Return a stub of the payload served for a city page."""
    return render_city_page(city_body)


@pytest.fixture(name="suggest_payload")
def suggest_payload_fixture() -> str:
    """Return a stub response of the location suggest endpoint."""
    return json.dumps(
        {
            "suggestions": [
                {
                    "kind": "city",
                    "label": "Gera",
                    "href": "/gera",
                    "filter": {"city": "Gera", "bundesland": "Thüringen"},
                },
                # No page of its own, so it cannot be polled.
                {"kind": "city", "label": "Geratal", "href": None},
                {"kind": "street", "label": "Geraer Straße", "href": None},
            ]
        }
    )


@pytest.fixture(name="config_entry")
def config_entry_fixture() -> MockConfigEntry:
    """Return a configured entry for Gera."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Gera",
        unique_id="/gera",
        data={
            CONF_CITY: "Gera",
            CONF_CITY_PATH: "/gera",
            CONF_BUNDESLAND: "Thüringen",
        },
        options={CONF_CATEGORIES: [], CONF_RADIUS: 0, CONF_MAX_REPORTS: 20},
    )


@pytest.fixture(name="mock_get")
def mock_get_fixture(city_payload: str, suggest_payload: str):
    """Patch the client transport so the tests never reach the network."""
    from custom_components.adlerlicht_de.api import UnknownCity

    responses = {"/api/location/suggest": suggest_payload, "/gera": city_payload}

    async def _get(self, path: str, **kwargs: Any) -> str:
        try:
            return responses[path]
        except KeyError:
            raise UnknownCity(f"{path} does not exist") from None

    with patch("custom_components.adlerlicht_de.api.AdlerlichtClient._get", new=_get):
        yield responses


@pytest.fixture(name="set_city_page")
def set_city_page_fixture(mock_get: dict[str, str]) -> Callable[[dict[str, Any]], None]:
    """Return a callback that replaces what the city page serves next."""

    def _set(body: dict[str, Any]) -> None:
        mock_get["/gera"] = render_city_page(body)

    return _set
