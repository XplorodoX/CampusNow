#!/usr/bin/env python3
"""Bulk-Upload von 360°-Panoramabildern für CampusNow.

Liest alle Bilder aus einem Verzeichnis und lädt sie via API hoch.
Der Dateiname (ohne Extension) wird als Node-ID verwendet.

Verwendung:
    python upload_panoramas.py --dir ./fotos/G2-EG --api-url http://localhost:6058 --api-key DEIN_KEY

Dateiname → Node-ID Beispiele:
    G2-EG-E01.jpg  → node_id: G2-EG-E01
    G2-1OG-G03.jpg → node_id: G2-1OG-G03

Unterstützte Formate: .jpg .jpeg .png .webp
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def upload_image(api_url: str, api_key: str, node_id: str, image_path: Path) -> bool:
    url = f"{api_url.rstrip('/')}/api/v1/images/rooms/{node_id}/upload"
    with image_path.open("rb") as f:
        mime = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else f"image/{image_path.suffix.lstrip('.')}"
        try:
            response = requests.post(
                url,
                headers={"X-API-Key": api_key},
                files={"file": (image_path.name, f, mime)},
                timeout=60,
            )
        except requests.RequestException as e:
            print(f"  ✗ Netzwerkfehler: {e}")
            return False

    if response.status_code in (200, 201):
        data = response.json()
        print(f"  ✓ {node_id} → {data.get('image_url_api', 'OK')}")
        return True

    print(f"  ✗ {node_id}: HTTP {response.status_code} – {response.text[:120]}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-Upload 360°-Panoramen für CampusNow")
    parser.add_argument("--dir", required=True, help="Verzeichnis mit Panoramabildern")
    parser.add_argument("--api-url", default="http://localhost:6058", help="API-Basisadresse (default: http://localhost:6058)")
    parser.add_argument("--api-key", required=True, help="Admin-API-Key (X-API-Key Header)")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen was hochgeladen würde, ohne zu uploaden")
    args = parser.parse_args()

    source_dir = Path(args.dir)
    if not source_dir.is_dir():
        print(f"Fehler: '{args.dir}' ist kein gültiges Verzeichnis.", file=sys.stderr)
        sys.exit(1)

    images = sorted(p for p in source_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not images:
        print(f"Keine Bilder ({', '.join(SUPPORTED_EXTENSIONS)}) in '{args.dir}' gefunden.")
        sys.exit(0)

    print(f"Gefunden: {len(images)} Bild(er) in '{args.dir}'")
    if args.dry_run:
        print("DRY-RUN – kein Upload:")
        for img in images:
            print(f"  {img.stem} ← {img.name}")
        return

    ok = 0
    fail = 0
    for img in images:
        node_id = img.stem
        result = upload_image(args.api_url, args.api_key, node_id, img)
        if result:
            ok += 1
        else:
            fail += 1

    print(f"\nFertig: {ok} erfolgreich, {fail} fehlgeschlagen.")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
