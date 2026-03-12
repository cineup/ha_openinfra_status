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
    """Extract a field from a nested dict (e.g. planned_work.title)."""
    event = data.get(key)
    if isinstance(event, dict):
        return event.get(field)
    return None


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    """Parse a timestamp string into a timezone-aware datetime.

    The API uses format "YYYY-MM-DD HH:MM:SS" (no timezone).
    Following the website JS behaviour, naive timestamps are treated as UTC.
    """
    if not value:
        return None
    try:
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            return None
        # API timestamps lack timezone info; treat as UTC (matches website JS).
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt_util.UTC)
        return parsed
    except (ValueError, TypeError):
        return None


def _get_latest_comment_text(data: dict[str, Any]) -> str | None:
    """Get the text of the latest comment/update.

    JS-CONFIRMED: website uses comments[0].text with latest_comment as fallback.
    """
    comments = data.get("comments")
    if isinstance(comments, list) and comments:
        first = comments[0]
        if isinstance(first, dict):
            return first.get("text")
    latest = data.get("latest_comment")
    if isinstance(latest, dict):
        return latest.get("text")
    return None


def _get_latest_comment_timestamp(data: dict[str, Any]) -> datetime | None:
    """Get the timestamp of the latest comment/update."""
    comments = data.get("comments")
    if isinstance(comments, list) and comments:
        first = comments[0]
        if isinstance(first, dict):
            return _parse_iso_timestamp(first.get("timestamp"))
    latest = data.get("latest_comment")
    if isinstance(latest, dict):
        return _parse_iso_timestamp(latest.get("timestamp"))
    return None


def _get_general_info_count(data: dict[str, Any]) -> int | None:
    """Return the number of active general info items (from /api/general)."""
    info_list = data.get("general_info")
    if not isinstance(info_list, list):
        return None
    return len(info_list)


SENSOR_DESCRIPTIONS: tuple[OpenInfraSensorEntityDescription, ...] = (
    # --- Network status (ENUM) ---
    # CONFIRMED: "network_status" field exists, value "up" observed.
    OpenInfraSensorEntityDescription(
        key="network_status",
        translation_key="network_status",
        device_class=SensorDeviceClass.ENUM,
        options=["up", "down", "maintenance", "disruption"],
        value_fn=lambda data, _coord: data.get("network_status"),
    ),
    # --- Context / diagnostic ---
    # CONFIRMED: "country_code" exists (e.g. "DE").
    OpenInfraSensorEntityDescription(
        key="country_code",
        translation_key="country_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: data.get("country_code"),
    ),
    # CONFIRMED: "detected_region" exists (e.g. "se").
    OpenInfraSensorEntityDescription(
        key="detected_region",
        translation_key="detected_region",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: data.get("detected_region"),
    ),
    # --- Planned work detail sensors ---
    # JS-CONFIRMED: "planned_work" is a dict with title, description,
    # start_time, end_time when is_planned_work is true.
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
    # JS-CONFIRMED: "planned_work_status" is "scheduled" for future work,
    # other values indicate active. NOT "upcoming" as previously assumed.
    OpenInfraSensorEntityDescription(
        key="planned_work_status",
        translation_key="planned_work_status",
        device_class=SensorDeviceClass.ENUM,
        options=["scheduled", "active", "completed"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: data.get("planned_work_status"),
    ),
    # --- Error sensors ---
    # JS-CONFIRMED: "error" stays boolean. Error text is in "error_message".
    OpenInfraSensorEntityDescription(
        key="error_message",
        translation_key="error_message",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: data.get("error_message")
        if data.get("error")
        else None,
    ),
    # --- Disruption detail sensors ---
    # JS-CONFIRMED: "is_down" stays boolean. Disruption details come from
    # "comments" array and "outage_start_time".
    OpenInfraSensorEntityDescription(
        key="latest_comment",
        translation_key="latest_comment",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_latest_comment_text(data),
    ),
    OpenInfraSensorEntityDescription(
        key="latest_comment_time",
        translation_key="latest_comment_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_latest_comment_timestamp(data),
    ),
    # JS-CONFIRMED: API provides outage_start_time (no local tracking needed).
    OpenInfraSensorEntityDescription(
        key="outage_start_time",
        translation_key="outage_start_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _parse_iso_timestamp(
            data.get("outage_start_time")
        ),
    ),
    # JS-CONFIRMED: resolution timestamp when outage was recently resolved.
    OpenInfraSensorEntityDescription(
        key="outage_resolved_at",
        translation_key="outage_resolved_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _parse_iso_timestamp(
            data.get("end_time") or data.get("outage_resolved_at")
        ),
    ),
    # JS-CONFIRMED: hours since outage was resolved.
    OpenInfraSensorEntityDescription(
        key="resolved_within_hours",
        translation_key="resolved_within_hours",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: data.get("resolved_within_hours"),
    ),
    # --- General info (from /api/general) ---
    # CONFIRMED: info items have id, title, message, type, start_time, end_time.
    OpenInfraSensorEntityDescription(
        key="general_info",
        translation_key="general_info",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _coord: _get_general_info_count(data),
    ),
    # --- Timestamp sensors ---
    # LOCAL: generated client-side, not from API.
    OpenInfraSensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data, _coord: dt_util.now(),
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
    def native_value(self) -> datetime | str | int | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(
            self.coordinator.data, self.coordinator
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.entity_description.key != "general_info":
            return None
        if self.coordinator.data is None:
            return None
        info_list = self.coordinator.data.get("general_info")
        if not isinstance(info_list, list) or not info_list:
            return None
        attrs: dict[str, Any] = {}
        for i, item in enumerate(info_list):
            if not isinstance(item, dict):
                continue
            prefix = f"item_{i}"
            attrs[f"{prefix}_id"] = item.get("id")
            attrs[f"{prefix}_title"] = item.get("title")
            attrs[f"{prefix}_message"] = item.get("message")
            attrs[f"{prefix}_type"] = item.get("type")
            attrs[f"{prefix}_start_time"] = item.get("start_time")
            attrs[f"{prefix}_end_time"] = item.get("end_time")
        return attrs
