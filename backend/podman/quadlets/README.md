# CampusNow Quadlets

Diese Quadlets bilden die bisherige Compose-Konfiguration auf Podman + systemd ab.

## Ablage

Für einen rootless Start die Dateien mit `make quadlet-install` nach `~/.config/containers/systemd/campusnow/` verlinken.

## Start

```bash
systemctl --user daemon-reload
systemctl --user start mongodb.service api.service scraper.service
```

Der Mock-Seeder ist optional:

```bash
systemctl --user start mock-seeder.service
```

## Status

```bash
systemctl --user status mongodb.service api.service scraper.service
```

## Hinweise

- Die Units erwarten das Repository in diesem Checkout unter `/home/flo/CampusNow`.
- Die Units sind selbständig konfiguriert; Anpassungen machst du direkt in den Quadlets oder per systemd Drop-in.
- Die API ist danach unter `http://localhost:6058/docs` erreichbar.