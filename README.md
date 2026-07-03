# OpenInfra Status - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Custom integration for [Home Assistant](https://www.home-assistant.io/) that monitors the network status of [OpenInfra](https://openinfra.tech).

For more information about network status, visit the OpenInfra status page:
https://openinfra.tech

## Features

- Query current network status for a location (country + postal code)
- Automatic updates every 10 minutes
- Native HA entity types with `device_class` — standard cards (Entities, Glance, Badges) work out of the box
- 11 entities total: 6 binary sensors + 5 sensors

## Entities

### Binary Sensors

| Entity | device_class | entity_category | Description |
|--------|-------------|-----------------|-------------|
| `binary_sensor.network_connected` | `connectivity` | — | On when network status is `up`. Green/red icon in frontend. |
| `binary_sensor.planned_work_active` | `problem` | `diagnostic` | On when a planned maintenance object is present. |
| `binary_sensor.disruption_active` | `problem` | `diagnostic` | On when a disruption is active. |
| `binary_sensor.recently_resolved` | `problem` | `diagnostic` | On when an outage was recently resolved. |
| `binary_sensor.error_active` | `problem` | `diagnostic` | On when an error is present. |
| `binary_sensor.general_info_active` | `problem` | `diagnostic` | On when general info items are available. |

### Sensors

| Entity | device_class | entity_category | Description |
|--------|-------------|-----------------|-------------|
| `sensor.network_status` | `enum` | — | Current network status: `up`, `down`, `maintenance`, `disruption`. Details (planned work, disruption, error) are available as attributes. |
| `sensor.last_update` | `timestamp` | — | Timestamp of the last successful API call. |
| `sensor.general_info` | — | `diagnostic` | Number of active general info items. Item details available as attributes. |
| `sensor.country_code` | — | `diagnostic` | Country code returned by the API. |
| `sensor.detected_region` | — | `diagnostic` | Region detected by the API. |

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

## Custom Card

The integration ships with its own Lovelace card and registers it automatically —
no HACS frontend resource, no Mushroom, no manual resource setup required. After
installing/restarting, add a card and pick **OpenInfra Status Card**, or use YAML:

```yaml
type: custom:openinfra-status-card
entity: sensor.openinfra_YOUR_POSTCODE_netzwerkstatus
```

Only the `network_status` sensor is required. The card auto-discovers the
related entities (disruption, planned work, recently resolved, error, general
info) from the same device, so it is language-independent. It shows a single,
correct status derived from the binary sensors — with precedence
`error → disruption → planned work → recently resolved → up` — plus disruption
duration and latest comment, planned-work window, and any general info items.

> If auto-discovery ever needs overriding, the following optional config keys
> accept explicit entity IDs: `disruption_entity`, `planned_work_entity`,
> `recently_resolved_entity`, `error_entity`, `general_info_entity`,
> `general_info_binary_entity`.

## Example Dashboard (built-in cards)

You can also use the binary sensors directly in an **Entities Card** or
**Glance Card** — no custom card needed:

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
      message: "OpenInfra disruption: {{ state_attr('sensor.network_status', 'latest_comment') }}"
```

## Development

This integration is a community project and has no official affiliation with OpenInfra.

Bug reports and feature requests are welcome as [Issues](https://github.com/cineup/ha_openinfra_status/issues).
