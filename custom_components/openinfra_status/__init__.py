"""The OpenInfra Status integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, TypeAlias

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_GENERAL_URL,
    API_TIMEOUT,
    API_URL,
    CONF_COUNTRY,
    CONF_POSTCODE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

OpenInfraConfigEntry: TypeAlias = ConfigEntry


class OpenInfraDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from the OpenInfra Status API."""

    config_entry: OpenInfraConfigEntry

    def __init__(self, hass: HomeAssistant, entry: OpenInfraConfigEntry) -> None:
        """Initialize the coordinator."""
        self.country = entry.data[CONF_COUNTRY]
        self.postcode = entry.data[CONF_POSTCODE]
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=f"OpenInfra Status {self.postcode}",
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
            config_entry=entry,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from both API endpoints."""
        try:
            async with asyncio.timeout(API_TIMEOUT):
                resp = await self.session.get(
                    API_URL,
                    params={
                        "country": self.country,
                        "postcode": self.postcode,
                    },
                )
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        if not data.get("success"):
            raise UpdateFailed(
                f"API returned error: {data.get('error', 'unknown error')}"
            )

        _LOGGER.debug("OpenInfra API response: %s", data)

        # Fetch general info (non-postcode-specific maintenance/outage info).
        # This is a secondary call; failures here should not block the main data.
        try:
            async with asyncio.timeout(API_TIMEOUT):
                # JS uses "gb" for "uk" country code
                country_param = "gb" if self.country == "uk" else self.country
                general_resp = await self.session.get(
                    API_GENERAL_URL,
                    params={"country": country_param},
                )
                general_data = await general_resp.json()

            if general_data.get("has_info") and general_data.get("info"):
                info = general_data["info"]
                data["general_info"] = info if isinstance(info, list) else [info]
            else:
                data["general_info"] = []
        except (aiohttp.ClientError, asyncio.TimeoutError):
            _LOGGER.debug("Failed to fetch general info, continuing without it")
            data["general_info"] = []

        return data


async def async_setup_entry(hass: HomeAssistant, entry: OpenInfraConfigEntry) -> bool:
    """Set up OpenInfra Status from a config entry."""
    coordinator = OpenInfraDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: OpenInfraConfigEntry
) -> None:
    """Reload integration when config entry is updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: OpenInfraConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
