"""Config flow for OpenInfra Status integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_TIMEOUT, API_URL, CONF_COUNTRY, CONF_POSTCODE, DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORTED_COUNTRIES = ["de", "se", "uk", "us"]

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_COUNTRY, default="de"): vol.In(SUPPORTED_COUNTRIES),
        vol.Required(CONF_POSTCODE): str,
    }
)


class OpenInfraStatusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenInfra Status."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            country = user_input[CONF_COUNTRY].lower().strip()
            postcode = user_input[CONF_POSTCODE].strip()

            await self.async_set_unique_id(f"{country}_{postcode}")
            self._abort_if_unique_id_configured()

            # Test API connectivity
            try:
                session = async_get_clientsession(self.hass)
                async with asyncio.timeout(API_TIMEOUT):
                    resp = await session.get(
                        API_URL,
                        params={"country": country, "postcode": postcode},
                    )
                    data = await resp.json()

                if not data.get("success"):
                    errors["base"] = "invalid_response"
                else:
                    return self.async_create_entry(
                        title=f"OpenInfra {postcode}",
                        data={CONF_COUNTRY: country, CONF_POSTCODE: postcode},
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
