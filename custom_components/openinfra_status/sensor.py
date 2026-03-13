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


def _build_network_status_attrs(data: dict[str, Any]) -> dict[str, Any]:
    """Build extra_state_attributes for the network_status sensor.

    Consolidates planned work, disruption, error, and resolution details
    that were previously exposed as individual diagnostic sensors.
    """
    attrs: dict[str, Any] = {}

    # --- Planned work ---
    pw = data.get("planned_work")
    if isinstance(pw, dict):
        attrs["planned_work_title"] = pw.get("title")
        attrs["planned_work_description"] = pw.get("description")
        attrs["planned_work_start"] = pw.get("start_time")
        attrs["planned_work_end"] = pw.get("end_time")
    if data.get("planned_work_status"):
        attrs["planned_work_status"] = data["planned_work_status"]

    # --- Disruption ---
    if data.get("outage_start_time"):
        attrs["outage_start_time"] = data["outage_start_time"]
    comment_text = _get_latest_comment_text(data)
    if comment_text:
        attrs["latest_comment"] = comment_text
    comment_ts = _get_latest_comment_timestamp(data)
    if comment_ts:
        attrs["latest_comment_time"] = comment_ts.isoformat()

    # --- Resolution ---
    resolved_at = data.get("end_time") or data.get("outage_resolved_at")
    if resolved_at:
        attrs["outage_resolved_at"] = resolved_at
    if data.get("resolved_within_hours") is not None:
        attrs["resolved_within_hours"] = data["resolved_within_hours"]

    # --- Error ---
    if data.get("error") and data.get("error_message"):
        attrs["error_message"] = data["error_message"]

    return attrs


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
    # NOTE: Planned work, disruption, error, and resolution details are
    # exposed as extra_state_attributes on the network_status sensor
    # (see _build_network_status_attrs below) instead of individual sensors.
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
        if self.coordinator.data is None:
            return None

        key = self.entity_description.key

        if key == "network_status":
            attrs = _build_network_status_attrs(self.coordinator.data)
            return attrs or None

        if key == "general_info":
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

        return None
