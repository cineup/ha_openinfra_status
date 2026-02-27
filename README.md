# OpenInfra Status - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

> **Note:** This integration is under active development. Features may change or be extended.

Custom integration for [Home Assistant](https://www.home-assistant.io/) that monitors the network status of [OpenInfra](https://openinfra.tech).

For more information about network status, visit the OpenInfra status page:
https://openinfra.tech

## Features

- Query current network status for a location (country + postal code)
- Automatic updates every 10 minutes
- 6 sensor entities:
  - **Network status** – Enum sensor (`operational`, `down`, `scheduled_maintenance`, `recently_resolved`, `info`) with attributes: `country_code`, `detected_region`
  - **Planned work** – Title as state, with attributes: `description`, `start_time`, `end_time`, `id`, `starts_in_days`, `status`
  - **Error** – Title as state, with attributes: `description`, `id`, `start_time` (when the API returns an error object)
  - **Disruption** – Title as state, with attributes: `description`, `id`, `start_time` (when the API returns a disruption object)
  - **Last update** – Timestamp of the last API call
  - **Disruption since** – Timestamp since when a disruption has been active

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

## Development

This integration is a community project and has no official affiliation with OpenInfra.

Bug reports and feature requests are welcome as [Issues](https://github.com/cineup/ha_openinfra_status/issues).
