# OpenInfra Status - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

> **Breaking change in v2.0:** Entity IDs have changed. Old `sensor.*` entities for
> network_status, planned_work, error, and disruption have been replaced with native
> HA binary sensors and granular detail sensors. Please update your dashboards and
> automations after upgrading — see [Migration](#migration-from-v1x-to-v20) below.

Custom integration for [Home Assistant](https://www.home-assistant.io/) that monitors the network status of [OpenInfra](https://openinfra.tech).

For more information about network status, visit the OpenInfra status page:
https://openinfra.tech

## Features

- Query current network status for a location (country + postal code)
- Automatic updates every 10 minutes
- Native HA entity types with `device_class` — standard cards (Entities, Glance, Badges) work out of the box
- 17 entities total: 4 binary sensors + 13 sensors

## Entities

### Binary Sensors

| Entity | device_class | Description |
|--------|-------------|-------------|
| `binary_sensor.network_connected` | `connectivity` | On when network status is `up`. Green/red icon in frontend. |
| `binary_sensor.planned_work_active` | `problem` | On when a planned maintenance object is present. |
| `binary_sensor.disruption_active` | `problem` | On when a disruption is active (`is_down` is truthy). |
| `binary_sensor.error_active` | `problem` | On when an error object is present. |

### Sensors

| Entity | device_class | entity_category | Description |
|--------|-------------|-----------------|-------------|
| `sensor.network_status` | `enum` | — | Current network status: `up`, `down`, `maintenance`, `disruption` |
| `sensor.last_update` | `timestamp` | — | Timestamp of the last successful API call |
| `sensor.disruption_since` | `timestamp` | — | Timestamp since when a disruption has been active |
| `sensor.country_code` | — | `diagnostic` | Country code returned by the API |
| `sensor.detected_region` | — | `diagnostic` | Region detected by the API |
| `sensor.planned_work_title` | — | `diagnostic` | Title of the active planned maintenance |
| `sensor.planned_work_description` | — | `diagnostic` | Description of the active planned maintenance |
| `sensor.planned_work_start` | `timestamp` | `diagnostic` | Start time of the planned maintenance |
| `sensor.planned_work_end` | `timestamp` | `diagnostic` | End time of the planned maintenance |
| `sensor.planned_work_status` | `enum` | `diagnostic` | Status of planned work: `upcoming`, `active`, `completed` |
| `sensor.error_title` | — | `diagnostic` | Title of the current error |
| `sensor.error_description` | — | `diagnostic` | Description of the current error |
| `sensor.disruption_title` | — | `diagnostic` | Title of the current disruption |
| `sensor.disruption_description` | — | `diagnostic` | Description of the current disruption |

> Diagnostic entities are hidden from standard dashboards by default but remain
> available for automations and developer tools.

## Supported Countries

| Code | Country |
|------|---------|
| `de` | Germany |
| `no` | Norway |
| `se` | Sweden |
| `uk` | United Kingdom |
| `us` | United States |

## Installation

### Via HACS (recommended)

1. Install [HACS](https://hacs.xyz/) in Home Assistant (if not already installed)
2. In HACS: **Integrations** → Menu (three dots top right) → **Custom repositories**
3. Enter repository URL `https://github.com/cineup/ha_openinfra_status`, select category **Integration**
4. Install "OpenInfra Status"
5. **Restart Home Assistant**
6. Settings → Devices & Services → **Add Integration** → "OpenInfra Status"
7. Select your country and enter your postal code

### Manual

1. Copy the `custom_components/openinfra_status` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Set up the integration as described above

## Configuration

Two inputs are required during setup:

- **Country** – Select from the supported countries (de, no, se, uk, us)
- **Postal code** – Your postal code to check local network status

## Example Dashboard

Use the binary sensors directly in an **Entities Card** or **Glance Card** — no custom card needed:

```yaml
type: glance
entities:
  - entity: binary_sensor.network_connected
  - entity: binary_sensor.disruption_active
  - entity: binary_sensor.planned_work_active
  - entity: sensor.network_status
  - entity: sensor.last_update
```

## Example Automation

```yaml
trigger:
  - platform: state
    entity_id: binary_sensor.disruption_active
    to: "on"
action:
  - service: notify.mobile_app
    data:
      message: "OpenInfra disruption: {{ states('sensor.disruption_title') }}"
```

## Migration from v1.x to v2.0

v2.0 is a **breaking change**. The following old entities no longer exist:

| Old entity (v1.x) | Replacement (v2.0) |
|-------------------|--------------------|
| `sensor.network_status` (free text) | `binary_sensor.network_connected` + `sensor.network_status` (ENUM) |
| `sensor.planned_work` (title + attributes) | `binary_sensor.planned_work_active` + `sensor.planned_work_*` |
| `sensor.error` (title + attributes) | `binary_sensor.error_active` + `sensor.error_title/description` |
| `sensor.disruption` (title + attributes) | `binary_sensor.disruption_active` + `sensor.disruption_title/description` |

**Steps to migrate:**
1. Update the integration via HACS
2. Restart Home Assistant
3. Remove old entity references from dashboards and automations
4. Add the new entity IDs listed above

## Development

This integration is a community project and has no official affiliation with OpenInfra.

Bug reports and feature requests are welcome as [Issues](https://github.com/cineup/ha_openinfra_status/issues).
