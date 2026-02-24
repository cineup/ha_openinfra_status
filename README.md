# OpenInfra Status - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

> **Hinweis:** Diese Integration befindet sich noch in aktiver Entwicklung. Funktionen können sich ändern oder erweitert werden.

Custom Integration für [Home Assistant](https://www.home-assistant.io/), die den Netzwerkstatus von [OpenInfra](https://openinfra.tech) abfragt.

Weitere Informationen zum Netzwerkstatus sind direkt auf der OpenInfra-Statusseite abrufbar:
https://openinfra.tech

## Funktionen

- Abfrage des aktuellen Netzwerkstatus für einen Standort (Land + Postleitzahl)
- Automatische Aktualisierung alle 10 Minuten
- 6 Sensor-Entities:
  - **Netzwerkstatus** – Enum-Sensor (`operational`, `down`, `scheduled_maintenance`, `recently_resolved`, `info`) mit Attributen: `country_code`, `detected_region`
  - **Geplante Wartung** – Titel als State, mit Attributen: `description`, `start_time`, `end_time`, `id`, `starts_in_days`, `status`
  - **Fehler** – Titel als State, mit Attributen: `description`, `id`, `start_time` (wenn die API ein Fehler-Objekt liefert)
  - **Störung** – Titel als State, mit Attributen: `description`, `id`, `start_time` (wenn die API ein Störungs-Objekt liefert)
  - **Letztes Update** – Zeitstempel der letzten API-Abfrage
  - **Störung seit** – Zeitstempel seit wann eine Störung besteht

## Unterstützte Länder

| Code | Land |
|------|------|
| `de` | Deutschland |
| `se` | Schweden |

## Installation

### Über HACS (empfohlen)

1. [HACS](https://hacs.xyz/) in Home Assistant installieren (falls noch nicht vorhanden)
2. In HACS: **Integrationen** → Menü (drei Punkte oben rechts) → **Benutzerdefinierte Repositories**
3. Repository-URL `https://github.com/cineup/ha_openinfra_status` eingeben, Kategorie **Integration** wählen
4. "OpenInfra Status" installieren
5. **Home Assistant neu starten**
6. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → "OpenInfra Status"
7. Ländercode (z.B. `de`) und Postleitzahl eingeben

### Manuell

1. Den Ordner `custom_components/openinfra_status` in dein Home Assistant `config/custom_components/` Verzeichnis kopieren
2. Home Assistant neu starten
3. Integration wie oben beschrieben einrichten

## Konfiguration

Bei der Einrichtung werden zwei Angaben benötigt:

- **Ländercode** – Zweistelliger Code (`de` oder `se`)
- **Postleitzahl** – Deine Postleitzahl zur Abfrage des lokalen Netzwerkstatus

## Entwicklung

Diese Integration ist ein Community-Projekt und steht in keiner offiziellen Verbindung zu OpenInfra.

Fehler und Verbesserungsvorschläge gerne als [Issue](https://github.com/cineup/ha_openinfra_status/issues) melden.
