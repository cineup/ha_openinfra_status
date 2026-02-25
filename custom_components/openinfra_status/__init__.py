"""The OpenInfra Status integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any, TypeAlias

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_TIMEOUT,
    API_URL,
    CONF_COUNTRY,
    CONF_POSTCODE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

OpenInfraConfigEntry: TypeAlias = ConfigEntry


class OpenInfraDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from the OpenInfra Status API."""

    config_entry: OpenInfraConfigEntry

    def __init__(self, hass: HomeAssistant, entry: OpenInfraConfigEntry) -> None:
        """Initialize the coordinator."""
        self.country = entry.data[CONF_COUNTRY]
        self.postcode = entry.data[CONF_POSTCODE]
        self.session = async_get_clientsession(hass)
        self._disruption_since: datetime | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"OpenInfra Status {self.postcode}",
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
            config_entry=entry,
        )

    @property
    def disruption_since(self) -> datetime | None:
        """Return the timestamp when the current disruption started."""
        return self._disruption_since

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
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

        # Track disruption start time (is_down can be bool or dict)
        is_down = data.get("is_down", False)
        if is_down and self._disruption_since is None:
            self._disruption_since = datetime.now().astimezone()
        elif not is_down:
            self._disruption_since = None

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
