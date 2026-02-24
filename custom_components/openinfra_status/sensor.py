"""Sensor platform for OpenInfra Status integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import OpenInfraConfigEntry, OpenInfraDataUpdateCoordinator
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class OpenInfraSensorEntityDescription(SensorEntityDescription):
    """Describe an OpenInfra sensor entity."""

    value_fn: Callable[[dict[str, Any], OpenInfraDataUpdateCoordinator], Any]
    extra_attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _get_event_title(data: dict[str, Any], key: str) -> str | None:
    """Extract title from an event object (planned_work, error, is_down)."""
    event = data.get(key)
    if isinstance(event, dict):
        return event.get("title")
    return None


def _get_event_attrs(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Extract all attributes from an event object.

    Handles both boolean and dict responses from the API.
    Known fields are mapped explicitly; unknown fields are passed through.
    """
    event = data.get(key)
    if not isinstance(event, dict):
        return {}
    known_keys = {"title"}
    attrs: dict[str, Any] = {}
    for field in ("description", "id", "start_time", "end_time"):
        if field in event:
            attrs[field] = event[field]
    # Pass through any extra fields the API may add
    for field, value in event.items():
        if field not in known_keys and field not in attrs:
            attrs[field] = value
    return attrs


def _get_network_status_attrs(data: dict[str, Any]) -> dict[str, Any]:
    """Return extra attributes for the network status sensor."""
    return {
        "country_code": data.get("country_code"),
        "detected_region": data.get("detected_region"),
    }


def _get_planned_work_attrs(data: dict[str, Any]) -> dict[str, Any]:
    """Return planned work attributes including top-level status."""
    attrs = _get_event_attrs(data, "planned_work")
    status = data.get("planned_work_status")
    if status is not None:
        attrs["status"] = status
    return attrs


NETWORK_STATUS_OPTIONS = [
    "operational",
    "down",
    "scheduled_maintenance",
    "recently_resolved",
    "info",
]

SENSOR_DESCRIPTIONS: tuple[OpenInfraSensorEntityDescription, ...] = (
    OpenInfraSensorEntityDescription(
        key="network_status",
        translation_key="network_status",
        device_class=SensorDeviceClass.ENUM,
        options=NETWORK_STATUS_OPTIONS,
        value_fn=lambda data, _coord: data.get("network_status"),
        extra_attrs_fn=_get_network_status_attrs,
    ),
    OpenInfraSensorEntityDescription(
        key="planned_work",
        translation_key="planned_work",
        value_fn=lambda data, _coord: _get_event_title(data, "planned_work"),
        extra_attrs_fn=_get_planned_work_attrs,
    ),
    OpenInfraSensorEntityDescription(
        key="error",
        translation_key="error",
        value_fn=lambda data, _coord: _get_event_title(data, "error"),
        extra_attrs_fn=lambda data: _get_event_attrs(data, "error"),
    ),
    OpenInfraSensorEntityDescription(
        key="disruption",
        translation_key="disruption",
        value_fn=lambda data, _coord: _get_event_title(data, "is_down"),
        extra_attrs_fn=lambda data: _get_event_attrs(data, "is_down"),
    ),
    OpenInfraSensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data, _coord: dt_util.now(),
    ),
    OpenInfraSensorEntityDescription(
        key="disruption_since",
        translation_key="disruption_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _data, coord: coord.disruption_since,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OpenInfraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenInfra Status sensor entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        OpenInfraSensorEntity(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class OpenInfraSensorEntity(
    CoordinatorEntity[OpenInfraDataUpdateCoordinator], SensorEntity
):
    """Representation of an OpenInfra Status sensor."""

    entity_description: OpenInfraSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OpenInfraDataUpdateCoordinator,
        description: OpenInfraSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.country}_{coordinator.postcode}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, f"{coordinator.country}_{coordinator.postcode}")
            },
            name=f"OpenInfra {coordinator.postcode}",
            manufacturer="OpenInfra",
            model="Network Status",
        )

    @property
    def native_value(self) -> datetime | str | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(
            self.coordinator.data, self.coordinator
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if (
            self.entity_description.extra_attrs_fn is not None
            and self.coordinator.data is not None
        ):
            return self.entity_description.extra_attrs_fn(self.coordinator.data)
        return None
