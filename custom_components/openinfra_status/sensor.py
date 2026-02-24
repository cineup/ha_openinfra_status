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


def _get_planned_work_timerange(
    data: dict[str, Any], _coordinator: OpenInfraDataUpdateCoordinator
) -> str | None:
    """Extract planned work time range as a readable string."""
    planned = data.get("planned_work")
    if not planned:
        return None
    start = planned.get("start_time", "")
    end = planned.get("end_time", "")
    if not start or not end:
        return None
    return f"{start} - {end}"


def _get_description(
    data: dict[str, Any], _coordinator: OpenInfraDataUpdateCoordinator
) -> str | None:
    """Extract description text from planned work."""
    planned = data.get("planned_work")
    if planned:
        return planned.get("description")
    return None


def _get_network_status_attrs(data: dict[str, Any]) -> dict[str, Any]:
    """Return extra attributes for the network status sensor."""
    attrs: dict[str, Any] = {
        "is_down": data.get("is_down"),
        "is_planned_work": data.get("is_planned_work"),
        "country_code": data.get("country_code"),
        "detected_region": data.get("detected_region"),
        "planned_work_status": data.get("planned_work_status"),
    }
    planned = data.get("planned_work")
    if planned:
        attrs["planned_work_title"] = planned.get("title")
        attrs["planned_work_id"] = planned.get("id")
    return attrs


SENSOR_DESCRIPTIONS: tuple[OpenInfraSensorEntityDescription, ...] = (
    OpenInfraSensorEntityDescription(
        key="network_status",
        translation_key="network_status",
        value_fn=lambda data, _coord: data.get("network_status"),
        extra_attrs_fn=_get_network_status_attrs,
    ),
    OpenInfraSensorEntityDescription(
        key="description",
        translation_key="description",
        value_fn=_get_description,
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
    OpenInfraSensorEntityDescription(
        key="planned_work",
        translation_key="planned_work",
        value_fn=_get_planned_work_timerange,
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
