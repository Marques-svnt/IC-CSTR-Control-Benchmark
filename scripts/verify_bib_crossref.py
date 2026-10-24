"""Checks every BibTeX entry that carries a DOI against the Crossref record of that DOI.

Compares title (fuzzy), year, volume, first page and first-author family name. Entries without
a DOI are listed for manual verification. Read-only: it never edits the .bib file.

Usage:
    .venv/bin/python scripts/verify_bib_crossref.py papers/01_*/references.bib [...]
"""

from __future__ import annotations

import argparse
import difflib
import json
import logging
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", re.S)
FIELD_RE = re.compile(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|\d+)", re.S)
TITLE_MIN_RATIO = 0.85


def _clean(text: str) -> str:
    """Lower-cases and strips braces, LaTeX accents and punctuation for fuzzy comparison."""
    text = text.replace("\\AA", "A").replace("\\o", "o").replace("\\v{c}", "c")
    text = re.sub(r"\\[`'^\"~=.]?\{?(\w)\}?", r"\1", text)
    text = re.sub(r"[{}\\$]", "", text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", "", text.lower().replace("&amp;", "and")).strip()


def parse_bib(path: Path) -> dict[str, dict[str, str]]:
    """Returns key -> lower-cased field dict for every entry of a .bib file."""
    entries: dict[str, dict[str, str]] = {}
    for _, key, body in ENTRY_RE.findall(path.read_text(encoding="utf-8")):
        fields = {}
        for name, value in FIELD_RE.findall(body):
            fields[name.lower()] = value.strip("{}\" \n")
        entries[key] = fields
    return entries


def fetch_crossref(doi: str) -> dict | None:
    """GET api.crossref.org/works/<doi>; None if the DOI does not resolve."""
    req = urllib.request.Request(
        f"https://api.crossref.org/works/{doi}",
        headers={"User-Agent": "bib-check (mailto:marques.svnt.002@gmail.com)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)["message"]
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def compare(fields: dict[str, str], rec: dict) -> list[str]:
    """Differences between a BibTeX entry and its Crossref record."""
    problems = []
    title = (rec.get("title") or [""])[0]
    ratio = difflib.SequenceMatcher(None, _clean(fields.get("title", "")), _clean(title)).ratio()
    if ratio < TITLE_MIN_RATIO:
        problems.append(f"title differs (ratio {ratio:.2f}): Crossref says '{title}'")
    year = str(rec["issued"]["date-parts"][0][0])
    if fields.get("year") and fields["year"] != year:
        problems.append(f"year {fields['year']} != {year}")
    if fields.get("volume") and rec.get("volume") and fields["volume"] != str(rec["volume"]):
        problems.append(f"volume {fields['volume']} != {rec['volume']}")
    first_page = re.split(r"[-–]+", fields.get("pages", ""))[0].strip()
    rec_page = re.split(r"[-–]+", str(rec.get("page", "")))[0].strip()
    if first_page and rec_page and first_page != rec_page:
        problems.append(f"first page {first_page} != {rec_page}")
    authors = rec.get("author") or []
    if authors and fields.get("author"):
        family = _clean(authors[0].get("family", ""))
        if family and family not in _clean(fields["author"]):
            problems.append(f"first author '{authors[0].get('family')}' not in author field")
    return problems


def main() -> int:
    """Verifies the given .bib files; returns the number of entries with problems."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bibs", nargs="+", type=Path)
    bad = 0
    for bib in parser.parse_args().bibs:
        entries = parse_bib(bib)
        manual = [k for k, f in entries.items() if "doi" not in f]
        logger.info("%s: %d entries, %d with DOI", bib, len(entries), len(entries) - len(manual))
        for key, fields in entries.items():
            if "doi" not in fields:
                continue
            rec = fetch_crossref(fields["doi"])
            time.sleep(0.3)
            problems = ["DOI does not resolve"] if rec is None else compare(fields, rec)
            if problems:
                bad += 1
                logger.error("%s [%s]: %s", key, fields["doi"], "; ".join(problems))
        logger.info("No DOI (verify by hand): %s", ", ".join(manual) or "-")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
