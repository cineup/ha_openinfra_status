# Branding / Logo

Dieses Verzeichnis enthält die Branding-Dateien für die OpenInfra Status Integration.

## Dateien

| Datei | Beschreibung | Maße |
|-------|-------------|------|
| `icon.png` | Quadratisches Icon | 256x256 px |
| `icon@2x.png` | Quadratisches Icon (HiDPI) | 512x512 px |
| `logo.png` | Logo (Querformat) | min. 128px Höhe |

## Icon herunterladen

Das OpenInfra-Favicon kannst du direkt von der Website laden:

```bash
curl -o icon.png https://openinfra.tech/favicon.png
```

Falls nötig, mit ImageMagick auf die richtige Größe bringen:

```bash
# Icon 256x256
convert icon.png -resize 256x256 icon.png

# Icon 512x512 (HiDPI)
convert icon.png -resize 512x512 icon@2x.png
```

## Verwendung in Home Assistant

Damit das Icon in der HA-Oberfläche angezeigt wird, muss es im offiziellen
[home-assistant/brands](https://github.com/home-assistant/brands) Repository
unter `custom_integrations/openinfra_status/` eingereicht werden.
