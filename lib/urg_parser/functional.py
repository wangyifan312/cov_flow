"""Parse URG grp*.html files for functional coverage gaps.

All output gaps conform to schemas/coverage_gap.schema.json.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from lib.urg_parser.structure import GroupInfo


def parse_functional_coverage(
    report_dir: Path, groups: list[GroupInfo]
) -> list[dict]:
    """Parse grp*.html files and extract uncovered bins for all covergroups."""
    gaps: list[dict] = []
    for grp in groups:
        grp_path = report_dir / grp.grp_file
        if not grp_path.exists():
            continue
        with open(grp_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")
        source_file = _extract_source_file(soup)
        group_name = _extract_group_name(soup)
        gaps.extend(_parse_coverpoint_gaps(soup, group_name, source_file))
    return gaps


def _extract_source_file(soup: BeautifulSoup) -> str | None:
    """Extract source file path from onclick="openSrcFile(\'/path\')"."""
    for script in soup.find_all("script"):
        text = script.string or ""
        match = re.search(r"openSrcFile\(['\"]([^'\"]+)['\"]\)", text)
        if match:
            return match.group(1)
    for a_tag in soup.find_all("a", onclick=True):
        onclick = a_tag.get("onclick", "")
        if isinstance(onclick, str):
            match = re.search(r"openSrcFile\(['\"]([^'\"]+)['\"]\)", onclick)
            if match:
                return match.group(1)
    return None


def _extract_group_name(soup: BeautifulSoup) -> str:
    """Extract covergroup name from 'Summary for Group <name>' text."""
    for span in soup.find_all("span", class_="repname"):
        text = span.get_text(strip=True)
        match = re.match(r"Summary for Group\s+(.+)", text)
        if match:
            return match.group(1).strip()
    # Fallback: "Group : <name>"
    for span in soup.find_all("span", class_="repname"):
        text = span.get_text(strip=True)
        match = re.match(r"Group\s*:\s*(.+)", text)
        if match:
            return match.group(1).strip()
    return "unknown_group"


def _parse_coverpoint_gaps(
    soup: BeautifulSoup, group_name: str, source_file: str | None
) -> list[dict]:
    """Parse all coverpoint sections within a group HTML file."""
    gaps: list[dict] = []
    seen_coverpoints: set[str] = set()

    for anchor in soup.find_all("a", attrs={"name": True}):
        anchor_name = anchor.get("name")
        if not isinstance(anchor_name, str) or not anchor_name.startswith("inst_tag_"):
            continue

        tag_id = anchor_name[len("inst_tag_"):]
        parts = tag_id.rsplit(".", 1)
        if len(parts) < 2:
            continue

        coverpoint_name = parts[1]

        if coverpoint_name in seen_coverpoints:
            continue
        seen_coverpoints.add(coverpoint_name)

        is_cross = coverpoint_name.startswith("cr_")
        uncovered_label = "Element holes" if is_cross else "Uncovered bins"

        current: Any = anchor
        while current is not None:
            current = current.next_sibling
            if current is None:
                break

            if hasattr(current, "name") and current.name == "a":
                next_name = current.get("name")
                if isinstance(next_name, str) and next_name.startswith("inst_tag_"):
                    break

            if hasattr(current, "name") and current.name == "span":
                span_class = current.get("class")
                if isinstance(span_class, list) and "repname" in span_class:
                    text = current.get_text(strip=True)
                    if uncovered_label in text:
                        table = current.find_next("table")
                        if table:
                            bin_gaps = _parse_bin_table(
                                table, group_name, coverpoint_name,
                                is_cross, source_file,
                            )
                            gaps.extend(bin_gaps)
                            break

    return gaps


def _parse_bin_table(
    table: Any,
    group_name: str,
    coverpoint_name: str,
    is_cross: bool,
    source_file: str | None,
) -> list[dict]:
    """Parse a bin table to extract uncovered bin entries."""
    gaps: list[dict] = []
    rows = table.find_all("tr")
    if not rows:
        return gaps

    # Find header row
    header_cells: list[str] = []
    for row in rows:
        cells = row.find_all(["th", "td"])
        if cells:
            header_cells = [c.get_text(strip=True).upper() for c in cells]
            break

    if not header_cells:
        return gaps

    # Determine column indices
    name_col = 0
    count_col = -1

    for i, h in enumerate(header_cells):
        if "NAME" in h or "BIN" in h:
            name_col = i
            break

    for i, h in enumerate(header_cells):
        if h == "COUNT":
            count_col = i
            break
    else:
        for i, h in enumerate(header_cells):
            if "COUNT" in h or "NUMBER" in h:
                count_col = i
                break

    if count_col == -1:
        count_col = 1

    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue

        bin_name = cells[name_col].get_text(strip=True) if name_col < len(cells) else ""

        count_text = (
            cells[count_col].get_text(strip=True) if count_col < len(cells) else "0"
        )
        try:
            count = int(count_text)
        except ValueError:
            count = 0

        # Only include uncovered bins (count == 0)
        if count > 0:
            continue

        # For cross coverage, construct a descriptive bin name
        if is_cross and len(cells) > 2:
            dim_values = []
            for i, cell in enumerate(cells):
                if i < len(cells) - 3:  # Skip last 3 metadata columns
                    val = cell.get_text(strip=True)
                    if val:
                        dim_values.append(val)
            if dim_values:
                bin_name = " x ".join(dim_values)

        if not bin_name:
            continue

        gap: dict = {
            "coverage_type": "functional",
            "covergroup": group_name,
            "coverpoint": coverpoint_name,
            "bin": bin_name,
            "hit_count": 0,
            "goal": 1,
        }
        if source_file:
            gap["source_file"] = source_file
        gaps.append(gap)

    return gaps
