"""Config flow for the Adlerlicht integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import AdlerlichtClient, AdlerlichtError, Place
from .const import (
    CATEGORY_LABELS,
    CONF_BUNDESLAND,
    CONF_CATEGORIES,
    CONF_CITY,
    CONF_CITY_PATH,
    CONF_MAX_REPORTS,
    CONF_RADIUS,
    DEFAULT_MAX_REPORTS,
    DEFAULT_RADIUS_KM,
    DOMAIN,
)
from .coordinator import AdlerlichtConfigEntry

CONF_QUERY = "query"
CONF_PLACE = "place"

_CATEGORY_OPTIONS = [
    SelectOptionDict(value=key, label=f"{label} ({key})")
    for key, label in sorted(CATEGORY_LABELS.items(), key=lambda item: item[1])
]

_OPTIONS_SCHEMA_FIELDS = {
    vol.Optional(CONF_CATEGORIES): SelectSelector(
        SelectSelectorConfig(
            options=_CATEGORY_OPTIONS,
            multiple=True,
            mode=SelectSelectorMode.DROPDOWN,
        )
    ),
    vol.Optional(CONF_RADIUS): NumberSelector(
        NumberSelectorConfig(
            min=0, max=250, step=0.5, mode=NumberSelectorMode.BOX, unit_of_measurement="km"
        )
    ),
    vol.Optional(CONF_MAX_REPORTS): NumberSelector(
        NumberSelectorConfig(min=1, max=80, step=1, mode=NumberSelectorMode.BOX)
    ),
}


class AdlerlichtConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Adlerlicht."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._places: dict[str, Place] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for a city name and look it up on adlerlicht.de."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = AdlerlichtClient(async_get_clientsession(self.hass))
            try:
                places = await client.async_suggest_cities(user_input[CONF_QUERY])
            except AdlerlichtError:
                errors["base"] = "cannot_connect"
            else:
                if not places:
                    errors[CONF_QUERY] = "no_city_found"
                else:
                    self._places = {place.path: place for place in places}
                    if len(places) == 1:
                        return await self._async_create(places[0])
                    return await self.async_step_place()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_QUERY): str}),
            errors=errors,
        )

    async def async_step_place(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Let the user pick one of the matching cities."""
        if user_input is not None:
            return await self._async_create(self._places[user_input[CONF_PLACE]])

        options = [
            SelectOptionDict(
                value=path,
                label=(f"{place.label} ({place.bundesland})" if place.bundesland else place.label),
            )
            for path, place in self._places.items()
        ]
        return self.async_show_form(
            step_id="place",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PLACE): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    async def _async_create(self, place: Place) -> ConfigFlowResult:
        """Create the entry for the chosen city."""
        await self.async_set_unique_id(place.path)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=place.label,
            data={
                CONF_CITY: place.label,
                CONF_CITY_PATH: place.path,
                CONF_BUNDESLAND: place.bundesland,
            },
            options={
                CONF_CATEGORIES: [],
                CONF_RADIUS: DEFAULT_RADIUS_KM,
                CONF_MAX_REPORTS: DEFAULT_MAX_REPORTS,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: AdlerlichtConfigEntry,
    ) -> AdlerlichtOptionsFlow:
        """Return the options flow."""
        return AdlerlichtOptionsFlow()


class AdlerlichtOptionsFlow(OptionsFlow):
    """Handle the filter options of a configured city."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Let the user change the category, radius and count filters."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_CATEGORIES: user_input.get(CONF_CATEGORIES, []),
                    CONF_RADIUS: float(user_input.get(CONF_RADIUS, DEFAULT_RADIUS_KM)),
                    CONF_MAX_REPORTS: int(user_input.get(CONF_MAX_REPORTS, DEFAULT_MAX_REPORTS)),
                }
            )

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(_OPTIONS_SCHEMA_FIELDS),
                {
                    CONF_CATEGORIES: options.get(CONF_CATEGORIES, []),
                    CONF_RADIUS: options.get(CONF_RADIUS, DEFAULT_RADIUS_KM),
                    CONF_MAX_REPORTS: options.get(CONF_MAX_REPORTS, DEFAULT_MAX_REPORTS),
                },
            ),
        )
