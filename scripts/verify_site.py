#!/usr/bin/env python3
"""Verify the static EHL site without third-party dependencies."""

from __future__ import annotations

import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
FORBIDDEN_PUBLIC_COPY = re.compile(r"digital\s+harsh\s+noise", re.IGNORECASE)
EXPECTED_PLUGIN_COUNT = 45
EXPECTED_PLUGIN_FRAMEWORKS = {"juce": 23, "yup": 22}
REQUIRED_AI_DISCLOSURE = (
    "AI-native workflow",
    "Human direction and final judgment",
)
PUBLIC_TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".svg",
    ".txt",
    ".webmanifest",
    ".xml",
}


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.local_refs: set[str] = set()
        self.meta: dict[str, str] = {}
        self.plugin_frameworks: list[str] = []
        self.plugin_repositories: set[str] = set()
        self.plugin_filters: set[str] = set()

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

        if tag == "article" and values.get("class") == "project":
            if framework := values.get("data-category"):
                self.plugin_frameworks.append(framework)

        if tag == "button" and (plugin_filter := values.get("data-filter")):
            self.plugin_filters.add(plugin_filter)

        if tag == "a" and (label := values.get("aria-label", "")).startswith("Open "):
            href = values.get("href", "")
            if href.startswith("https://github.com/EsionHsrahLatigid/"):
                self.plugin_repositories.add(href.removeprefix("https://github.com/EsionHsrahLatigid/"))


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

    if len(index.plugin_frameworks) != EXPECTED_PLUGIN_COUNT:
        fail(f"plugin catalog must contain {EXPECTED_PLUGIN_COUNT} rows, got {len(index.plugin_frameworks)}")
    if len(index.plugin_repositories) != EXPECTED_PLUGIN_COUNT:
        fail(f"plugin catalog must link {EXPECTED_PLUGIN_COUNT} unique repositories, got {len(index.plugin_repositories)}")
    framework_counts = Counter(index.plugin_frameworks)
    if framework_counts != EXPECTED_PLUGIN_FRAMEWORKS:
        fail(f"plugin framework counts are wrong: {dict(framework_counts)}")
    if index.plugin_filters != {"all", "juce", "yup"}:
        fail(f"plugin filters are wrong: {sorted(index.plugin_filters)}")
    index_text = (SITE / "index.html").read_text(encoding="utf-8")
    for phrase in REQUIRED_AI_DISCLOSURE:
        if phrase not in index_text:
            fail(f"index.html is missing required AI disclosure: {phrase}")
    expected_counter = f'<span id="visible-count">{EXPECTED_PLUGIN_COUNT}</span>'
    if expected_counter not in index_text:
        fail(f"initial plugin counter must be {EXPECTED_PLUGIN_COUNT}")

    manifest = json.loads((SITE / "site.webmanifest").read_text(encoding="utf-8"))
    if manifest.get("start_url") != "/":
        fail("site.webmanifest start_url must be /")

    for path in sorted(SITE.rglob("*.svg")):
        try:
            ET.parse(path)
        except ET.ParseError as error:
            fail(f"invalid SVG {path.relative_to(ROOT)}: {error}")

    ET.parse(SITE / "sitemap.xml")

    public_text_files = [ROOT / "README.md"]
    public_text_files.extend(
        path
        for path in SITE.rglob("*")
        if path.is_file() and path.suffix.lower() in PUBLIC_TEXT_SUFFIXES
    )
    for path in public_text_files:
        if FORBIDDEN_PUBLIC_COPY.search(path.read_text(encoding="utf-8")):
            fail(f"forbidden public-facing brand phrase in {path.relative_to(ROOT)}")

    preview = (SITE / "assets/social/ehl-social-preview.png").read_bytes()
    if preview[:8] != b"\x89PNG\r\n\x1a\n":
        fail("social preview is not a PNG")
    width, height = struct.unpack(">II", preview[16:24])
    if (width, height) != (1200, 630):
        fail(f"social preview must be 1200x630, got {width}x{height}")

    print("PASS: public copy, HTML references, metadata, manifest, sitemap, SVGs, and 1200x630 social preview")


if __name__ == "__main__":
    main()
