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
from homeassistant.const import EntityCategory
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


def _get_event_field(data: dict[str, Any], key: str, field: str) -> str | None:
    """Extract a field from an event object (planned_work, error, is_down)."""
    event = data.get(key)
    if isinstance(event, dict):
        return event.get(field)
    return None


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string into a timezone-aware datetime."""
    if not value:
        return None
    try:
        return dt_util.parse_datetime(value)
    except (ValueError, TypeError):
        return None


SENSOR_DESCRIPTIONS: tuple[OpenInfraSensorEntityDescription, ...] = (
    # --- Network status (ENUM) ---
    OpenInfraSensorEntityDescription(
        key="network_status",
        translation_key="network_status",
        device_class=SensorDeviceClass.ENUM,
        options=["up", "down", "maintenance", "disruption"],
        value_fn=lambda data, _coord: data.get("network_status"),
    ),
    # --- Context / diagnostic ---
    OpenInfraSensorEntityDescription(
        key="country_code",
        translation_key="country_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: data.get("country_code"),
    ),
    OpenInfraSensorEntityDescription(
        key="detected_region",
        translation_key="detected_region",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: data.get("detected_region"),
    ),
    # --- Planned work detail sensors ---
    OpenInfraSensorEntityDescription(
        key="planned_work_title",
        translation_key="planned_work_title",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_event_field(data, "planned_work", "title"),
    ),
    OpenInfraSensorEntityDescription(
        key="planned_work_description",
        translation_key="planned_work_description",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_event_field(
            data, "planned_work", "description"
        ),
    ),
    OpenInfraSensorEntityDescription(
        key="planned_work_start",
        translation_key="planned_work_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _parse_iso_timestamp(
            _get_event_field(data, "planned_work", "start_time")
        ),
    ),
    OpenInfraSensorEntityDescription(
        key="planned_work_end",
        translation_key="planned_work_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _parse_iso_timestamp(
            _get_event_field(data, "planned_work", "end_time")
        ),
    ),
    OpenInfraSensorEntityDescription(
        key="planned_work_status",
        translation_key="planned_work_status",
        device_class=SensorDeviceClass.ENUM,
        options=["upcoming", "active", "completed"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: data.get("planned_work_status"),
    ),
    # --- Error detail sensors ---
    OpenInfraSensorEntityDescription(
        key="error_title",
        translation_key="error_title",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_event_field(data, "error", "title"),
    ),
    OpenInfraSensorEntityDescription(
        key="error_description",
        translation_key="error_description",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_event_field(data, "error", "description"),
    ),
    # --- Disruption detail sensors ---
    OpenInfraSensorEntityDescription(
        key="disruption_title",
        translation_key="disruption_title",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_event_field(data, "is_down", "title"),
    ),
    OpenInfraSensorEntityDescription(
        key="disruption_description",
        translation_key="disruption_description",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_event_field(
            data, "is_down", "description"
        ),
    ),
    # --- Timestamp sensors (unchanged) ---
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
