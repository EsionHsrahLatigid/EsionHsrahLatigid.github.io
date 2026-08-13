#!/usr/bin/env python3
"""Verify the static EHL site without third-party dependencies."""

from __future__ import annotations

import json
import struct
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.local_refs: set[str] = set()
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if element_id := values.get("id"):
            self.ids.add(element_id)

        for attribute in ("href", "src"):
            if ref := values.get(attribute):
                parsed = urlparse(ref)
                if not parsed.scheme and not parsed.netloc and not ref.startswith(("#", "mailto:")):
                    self.local_refs.add(parsed.path)

        if tag == "meta":
            key = values.get("name") or values.get("property")
            if key and values.get("content"):
                self.meta[key] = values["content"]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def verify_html(path: Path) -> SiteParser:
    parser = SiteParser()
    parser.feed(path.read_text(encoding="utf-8"))
    for ref in sorted(parser.local_refs):
        target = SITE / ref.lstrip("/") if ref.startswith("/") else path.parent / ref
        if not target.exists():
            fail(f"{path.name} references missing file: {ref}")
    return parser


def main() -> None:
    index = verify_html(SITE / "index.html")
    verify_html(SITE / "404.html")

    required_ids = {"main", "top", "signal", "plugins", "systems", "visible-count", "year"}
    missing_ids = required_ids - index.ids
    if missing_ids:
        fail(f"index.html is missing IDs: {', '.join(sorted(missing_ids))}")

    required_meta = {"description", "og:title", "og:description", "og:url", "og:image"}
    missing_meta = required_meta - index.meta.keys()
    if missing_meta:
        fail(f"index.html is missing metadata: {', '.join(sorted(missing_meta))}")

    manifest = json.loads((SITE / "site.webmanifest").read_text(encoding="utf-8"))
    if manifest.get("start_url") != "/":
        fail("site.webmanifest start_url must be /")

    for path in sorted(SITE.rglob("*.svg")):
        try:
            ET.parse(path)
        except ET.ParseError as error:
            fail(f"invalid SVG {path.relative_to(ROOT)}: {error}")

    ET.parse(SITE / "sitemap.xml")

    preview = (SITE / "assets/social/ehl-social-preview.png").read_bytes()
    if preview[:8] != b"\x89PNG\r\n\x1a\n":
        fail("social preview is not a PNG")
    width, height = struct.unpack(">II", preview[16:24])
    if (width, height) != (1200, 630):
        fail(f"social preview must be 1200x630, got {width}x{height}")

    print("PASS: HTML references, metadata, manifest, sitemap, SVGs, and 1200x630 social preview")


if __name__ == "__main__":
    main()
