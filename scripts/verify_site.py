#!/usr/bin/env python3
"""Verify the static EHL site without third-party dependencies."""

from __future__ import annotations

import hashlib
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
FORBIDDEN_TOKEN_DIGESTS = frozenset(
    {
        "977c2908e358e8dcae6fbb4db30ba9c8270086a256010014f553a960855cf56b",
    }
)
FORBIDDEN_COMPACT_DIGESTS = frozenset(
    {
        "df72b45f82869a738a4b6548b7860129cd368209ac73577210765c4b929b17ee",
    }
)
TOKEN_RE = re.compile(r"[a-z0-9]+")
ALNUM_RE = re.compile(r"[a-z0-9]")
REGEX_QUANTIFIER_RE = r"(?:[+*?]|\{\d+(?:,\d*)?\})?"
WHITESPACE_ESCAPE_RE = (
    r"\\{1,2}(?:[sbdwnrt]|x(?:09|0a|0d|20|a0)|u(?:0009|000a|000d|0020|00a0)"
    r"|U(?:00000009|0000000a|0000000d|00000020|000000a0))"
)
PERCENT_WHITESPACE_RE = r"%(?:09|0a|0d|20|a0)"
HTML_WHITESPACE_RE = r"&(?:nbsp|\#(?:0*9|0*10|0*13|0*32|0*160|x0*(?:9|a|d|20|a0)));"
REGEX_SEPARATOR_RE = re.compile(
    "|".join(
        (
            rf"(?:{WHITESPACE_ESCAPE_RE}{REGEX_QUANTIFIER_RE})",
            rf"(?:{PERCENT_WHITESPACE_RE}{REGEX_QUANTIFIER_RE})",
            rf"(?:{HTML_WHITESPACE_RE}{REGEX_QUANTIFIER_RE})",
            rf"(?:\[(?:{WHITESPACE_ESCAPE_RE}|[^\]])+\]{REGEX_QUANTIFIER_RE})",
            r"(?:\(\?[:=!<][^)]*\))",
            r"(?:[\\|+*?^$()[\]{}.,;:_/\-]+)",
        )
    ),
    re.IGNORECASE | re.VERBOSE,
)
EXPECTED_PLUGIN_COUNT = 55
EXPECTED_PLUGIN_FRAMEWORKS = {"juce": 33, "yup": 22}
EXPECTED_JUCE_RELEASES = {
    "BandRiot": ("003", "v0.1.1"),
    "BinGrave": ("007", "v0.1.2"),
    "BitRash": ("009", "v0.1.2"),
    "BrickMaw": ("011", "v0.1.2"),
    "DeltaSpine": ("016", "v0.1.1"),
    "FoldKnife": ("019", "v0.1.2"),
    "FormantWound": ("021", "v0.1.1"),
    "GrainLatch": ("023", "v0.1.1"),
    "HarshNoise": ("025", "v1.0.1"),
    "IronPress": ("026", "v0.1.1"),
    "IRRot": ("027", "v0.1.1"),
    "JetScab": ("028", "v0.1.1"),
    "NailComb": ("032", "v0.1.1"),
    "PacketRot": ("035", "v0.1.1"),
    "PhaseCoffin": ("036", "v0.1.2"),
    "PhaseShred": ("037", "v0.1.1"),
    "RuptureDelay": ("043", "v0.1.2"),
    "ScaleWound": ("045", "v0.1.1"),
    "SidebandMaw": ("046", "v0.1.1"),
    "StaticCathedral": ("050", "v0.1.2"),
}
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


def window_digests(values: list[str], window_size: int) -> set[str]:
    if len(values) < window_size:
        return set()
    digests: set[str] = set()
    for index in range(0, len(values) - window_size + 1):
        window = " ".join(values[index : index + window_size])
        digests.add(hashlib.sha256(window.encode("utf-8")).hexdigest())
    return digests


def compact_digests(text: str, window_size: int) -> set[str]:
    compact = "".join(ALNUM_RE.findall(text.casefold()))
    if len(compact) < window_size:
        return set()
    digests: set[str] = set()
    for index in range(0, len(compact) - window_size + 1):
        window = compact[index : index + window_size]
        digests.add(hashlib.sha256(window.encode("utf-8")).hexdigest())
    return digests


def reconstructable_text_variants(text: str) -> tuple[str, str]:
    return (text, REGEX_SEPARATOR_RE.sub(" ", text))


def contains_forbidden_public_copy(text: str) -> bool:
    tokens = TOKEN_RE.findall(text.casefold())
    return bool(
        window_digests(tokens, 3) & FORBIDDEN_TOKEN_DIGESTS
        or any(
            compact_digests(variant, 17) & FORBIDDEN_COMPACT_DIGESTS
            for variant in reconstructable_text_variants(text)
        )
    )


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
    project_indices = re.findall(r'<span class="project-index">(\d{3})</span>', index_text)
    expected_indices = [f"{number:03d}" for number in range(1, EXPECTED_PLUGIN_COUNT + 1)]
    if project_indices != expected_indices:
        fail("plugin indices are not sequential from 001 to "
             f"{EXPECTED_PLUGIN_COUNT:03d}")
    for repo, (index_number, version) in EXPECTED_JUCE_RELEASES.items():
        release_url = f"https://github.com/EsionHsrahLatigid/{repo}/releases/tag/{version}"
        within_article = r"(?:(?!</article>).)*?"
        article_pattern = (
            rf'<article class="project" data-category="juce" '
            rf'data-version="{re.escape(version)}" '
            rf'data-release-url="{re.escape(release_url)}">'
            rf'\s*<span class="project-index">{re.escape(index_number)}</span>'
            rf'{within_article}<h3>{re.escape(repo)}</h3>{within_article}'
            rf'<a href="https://github.com/EsionHsrahLatigid/{re.escape(repo)}" '
        )
        if not re.search(article_pattern, index_text, re.DOTALL):
            fail(f"missing verified JUCE catalog entry for {repo} {index_number} {version}")
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
        if contains_forbidden_public_copy(path.read_text(encoding="utf-8")):
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
