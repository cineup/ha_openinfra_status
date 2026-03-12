"""Binary sensor platform for OpenInfra Status integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OpenInfraConfigEntry, OpenInfraDataUpdateCoordinator
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class OpenInfraBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe an OpenInfra binary sensor entity."""

    value_fn: Callable[[dict[str, Any]], bool]


BINARY_SENSOR_DESCRIPTIONS: tuple[OpenInfraBinarySensorEntityDescription, ...] = (
    OpenInfraBinarySensorEntityDescription(
        key="network_connected",
        translation_key="network_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data: data.get("network_status") == "up",
    ),
    OpenInfraBinarySensorEntityDescription(
        key="planned_work_active",
        translation_key="planned_work_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: isinstance(data.get("planned_work"), dict),
    ),
    OpenInfraBinarySensorEntityDescription(
        key="disruption_active",
        translation_key="disruption_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: bool(data.get("is_down")),
    ),
    OpenInfraBinarySensorEntityDescription(
        key="error_active",
        translation_key="error_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: isinstance(data.get("error"), dict),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OpenInfraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenInfra Status binary sensor entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        OpenInfraBinarySensorEntity(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class OpenInfraBinarySensorEntity(
    CoordinatorEntity[OpenInfraDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of an OpenInfra Status binary sensor."""

    entity_description: OpenInfraBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OpenInfraDataUpdateCoordinator,
        description: OpenInfraBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
