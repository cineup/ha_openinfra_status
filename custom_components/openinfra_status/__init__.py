"""The OpenInfra Status integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from pathlib import Path
from typing import Any, TypeAlias

import aiohttp

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_GENERAL_URL,
    API_TIMEOUT,
    API_URL,
    CARD_FILENAME,
    CARD_URL_PATH,
    CARD_VERSION,
    CONF_COUNTRY,
    CONF_POSTCODE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

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


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve and register the custom Lovelace card (once per HA instance).

    The URL is versioned via ?v=CARD_VERSION, so browser caching is safe and
    keeps the card from loading too late for Lovelace on cold starts.
    """
    data = hass.data.setdefault(DOMAIN, {})
    if data.get("frontend_registered"):
        return

    card_path = str(Path(__file__).parent / "www" / CARD_FILENAME)
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, card_path, True)]
        )
    except ImportError:
        # Fallback for HA cores older than 2024.7.
        hass.http.register_static_path(CARD_URL_PATH, card_path, True)

    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={CARD_VERSION}")
    data["frontend_registered"] = True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the card as early as possible, before any entry is set up.

    Otherwise a frontend loaded during HA startup would miss the extra JS
    module and show an error card until the next page reload.
    """
    await _async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OpenInfraConfigEntry) -> bool:
    """Set up OpenInfra Status from a config entry."""
    await _async_register_frontend(hass)

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
