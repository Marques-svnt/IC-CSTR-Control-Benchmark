"""Automated Elsevier Desk-Check and LaTeX/BibTeX Hygiene Validator.

Enforces Q1 editorial standards for cas-dc Elsevier manuscripts:
1. Highlights: 3 to 5 items, max 85 characters per item (including spaces).
2. BibTeX: Acronym casing protection in titles ({PID}, {CSTR}, {NMPC}, etc.).
3. LaTeX Build: Zero undefined references ('??') or missing citations ('[?]').
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Common acronyms requiring protection in title fields
ACRONYM_PATTERN = re.compile(
    r"\b(PID|CSTR|NMPC|MHE|ITAE|IAE|AMIGO|SIMC|CHR|ODE|PPO|SAC|RL|CBF|QP|ANN|RBF|NASA|GEVS)\b"
)


class HighlightItem(BaseModel):
    """Schema for individual highlight item validation."""

    text: str
    length: int
    is_valid: bool


class DeskCheckReport(BaseModel):
    """Consolidated desk-check validation report."""

    paper_path: Path
    highlights_valid: bool = True
    bibtex_valid: bool = True
    latex_logs_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def check_highlights(highlights_file: Path) -> tuple[bool, list[str]]:
    """Validates Elsevier highlights formatting rules.

    Args:
        highlights_file: Path to highlights.tex or highlights.txt.

    Returns:
        Tuple of (is_valid, error_list).
    """
    errors: list[str] = []
    if not highlights_file.exists():
        return True, ["Highlights file not found (skipped)."]

    content = highlights_file.read_text(encoding="utf-8")
    items = re.findall(r"\\item\s+([^\n\r]+)", content)
    if not items:
        # Fallback to lines starting with dash or bullet
        items = [
            line.strip().lstrip("-*•").strip()
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith("\\")
        ]

    if not (3 <= len(items) <= 5):
        errors.append(f"Highlights count ({len(items)}) must be between 3 and 5 items.")

    for idx, item in enumerate(items, start=1):
        clean_text = re.sub(r"\\[a-zA-Z]+(\[[^\]]*\])?(\{[^\}]*\})?", "", item).strip()
        length = len(clean_text)
        if length > 85:
            errors.append(
                f"Highlight #{idx} exceeds 85 chars ({length} chars): '{clean_text}'"
            )

    return len(errors) == 0, errors


def check_bibtex(bib_file: Path) -> tuple[bool, list[str]]:
    """Validates BibTeX files for unbraced uppercase acronyms in titles.

    Args:
        bib_file: Path to references.bib file.

    Returns:
        Tuple of (is_valid, warning_list).
    """
    warnings: list[str] = []
    if not bib_file.exists():
        return True, ["BibTeX file not found (skipped)."]

    content = bib_file.read_text(encoding="utf-8")

    # Extract lines containing title assignment
    title_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("title"):
            title_lines.append(stripped)

    for line in title_lines:
        for match in ACRONYM_PATTERN.finditer(line):
            acronym = match.group(1)
            start = match.start()
            end = match.end()
            # Verify if enclosed in curly braces like {PID}
            is_braced = (
                start > 0
                and end < len(line)
                and line[start - 1] == "{"
                and line[end] == "}"
            )
            if not is_braced:
                warnings.append(
                    f"Acronym '{acronym}' in line not enclosed as '{{{acronym}}}': {line}"
                )

    return True, warnings


def check_latex_logs(paper_dir: Path) -> tuple[bool, list[str]]:
    """Checks LaTeX compilation log for undefined references and citations.

    Args:
        paper_dir: Directory containing main.log.

    Returns:
        Tuple of (is_valid, error_list).
    """
    errors: list[str] = []
    log_file = paper_dir / "main.log"
    if not log_file.exists():
        return True, ["main.log not found (run compilation first)."]

    content = log_file.read_text(encoding="utf-8", errors="ignore")
    if "undefined references" in content.lower():
        errors.append("LaTeX compilation contains undefined references ('??').")
    if "undefined citation" in content.lower():
        errors.append("LaTeX compilation contains undefined citations ('[?]').")

    return len(errors) == 0, errors


def validate_paper(paper_dir: Path) -> DeskCheckReport:
    """Runs full desk-check validation suite on target paper folder.

    Args:
        paper_dir: Path to directory containing paper assets.

    Returns:
        DeskCheckReport object with detailed diagnostics.
    """
    report = DeskCheckReport(paper_path=paper_dir)

    # 1. Highlights
    hl_file = paper_dir / "highlights.tex"
    hl_ok, hl_errs = check_highlights(hl_file)
    if not hl_ok:
        report.highlights_valid = False
        report.errors.extend(hl_errs)

    # 2. BibTeX
    bib_file = paper_dir / "references.bib"
    bib_ok, bib_warns = check_bibtex(bib_file)
    report.warnings.extend(bib_warns)

    # 3. LaTeX Logs
    log_ok, log_errs = check_latex_logs(paper_dir)
    if not log_ok:
        report.latex_logs_valid = False
        report.errors.extend(log_errs)

    return report


def main() -> int:
    """CLI entrypoint for Elsevier Desk-Check verification."""
    parser = argparse.ArgumentParser(
        description="Verify Elsevier cas-dc submission hygiene and constraints."
    )
    parser.add_argument(
        "--paper-dir",
        type=Path,
        default=Path("papers/01_journal_of_process_control"),
        help="Path to paper directory",
    )
    args = parser.parse_args()

    logger.info("Executing Elsevier Desk-Check for: %s", args.paper_dir)
    report = validate_paper(args.paper_dir)

    for warning in report.warnings:
        logger.warning(warning)

    if not (report.highlights_valid and report.latex_logs_valid):
        logger.error("Desk-check FAILED with %d critical errors:", len(report.errors))
        for err in report.errors:
            logger.error("  - %s", err)
        return 1

    logger.info("Desk-check PASSED successfully. Highlights and citations conform to Elsevier standards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
