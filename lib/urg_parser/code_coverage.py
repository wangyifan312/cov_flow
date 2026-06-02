"""Parse URG mod*.html files for code coverage gaps.

Supports 6 coverage types: line, branch, condition, toggle, fsm, assert.
All output gaps conform to schemas/coverage_gap.schema.json.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from lib.urg_parser.structure import ModuleInfo


def parse_code_coverage(
    report_dir: Path, modules: list[ModuleInfo], project_root: str | None = None
) -> list[dict]:
    """Parse mod*.html files and extract code coverage gaps.

    Returns a list of gap dicts with coverage_type set to one of:
    line, branch, condition, toggle, fsm, assert.

    Skips modules whose source files belong to Synopsys EDA tool libraries.
    """
    gaps: list[dict] = []
    for mod in modules:
        mod_path = report_dir / mod.mod_file
        if not mod_path.exists():
            continue
        with open(mod_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")

        source_file = _extract_source_file(soup)
        module_name = mod.name

        # Filter out Synopsys library modules
        if source_file and _is_synopsys_library(source_file):
            print(f"  Skipping Synopsys library module: {module_name} ({source_file})")
            continue

        if mod.line_score is not None and mod.line_score < 100:
            gaps.extend(_parse_line_coverage(soup, module_name, source_file))

        if mod.branch_score is not None and mod.branch_score < 100:
            gaps.extend(_parse_branch_coverage(soup, module_name, source_file))

        if mod.cond_score is not None and mod.cond_score < 100:
            gaps.extend(_parse_condition_coverage(soup, module_name, source_file))

        if mod.toggle_score is not None and mod.toggle_score < 100:
            gaps.extend(_parse_toggle_coverage(soup, module_name, source_file))

        if mod.fsm_score is not None and mod.fsm_score < 100:
            gaps.extend(_parse_fsm_coverage(soup, module_name, source_file))

        if mod.assert_score is not None and mod.assert_score < 100:
            gaps.extend(_parse_assert_coverage(soup, module_name, source_file))

    return gaps


def _is_synopsys_library(path: str) -> bool:
    """Check if a source file path belongs to Synopsys EDA tools.

    Only matches paths that are clearly Synopsys tool/library installations,
    not project paths that happen to contain these strings.
    """
    path_lower = path.lower()
    # Only match if the path starts with Synopsys installation directories
    # or contains specific Synopsys tool subdirectories
    if path_lower.startswith("/opt/synopsys/"):
        return True
    if path_lower.startswith("/synopsys/"):
        return True
    # Match Synopsys tool library paths (vcs, verdi, etc.)
    if "/etc/uvm-" in path_lower:  # UVM library shipped with VCS
        return True
    if "/vcs-mx/" in path_lower or "/vcs_mx/" in path_lower:
        return True
    return False


def _extract_source_file(soup: BeautifulSoup) -> str | None:
    """Extract source file path from the module page."""
    for span in soup.find_all("span", class_="repname"):
        if "Source File" in span.get_text():
            link = span.find_next("a")
            if link:
                onclick = link.get("onclick", "")
                if isinstance(onclick, str):
                    match = re.search(
                        r"openSrcFile\(['\"]([^'\"]+)['\"]\)", onclick
                    )
                    if match:
                        return match.group(1)
                text = link.get_text(strip=True)
                if text and "/" in text:
                    return text
    return None


# ---------------------------------------------------------------------------
# Line Coverage
# ---------------------------------------------------------------------------


def _parse_line_coverage(
    soup: BeautifulSoup, module_name: str, source_file: str | None
) -> list[dict]:
    """Parse line coverage from <pre class="code"> with red font markers.

    URG HTML pattern:
    - <pre class="code"> contains interleaved text nodes and <font> tags
    - Text nodes contain source lines prefixed with line numbers
    - <font color="red">0/N</font> marks an uncovered line
    """
    gaps: list[dict] = []
    seen_lines: set[int] = set()

    for pre in soup.find_all("pre", class_="code"):
        current_line = 0
        children = list(pre.children)

        for i, child in enumerate(children):
            # Text node: extract line number
            if not hasattr(child, "name") or child.name is None:
                text = str(child)
                # Look for line numbers in format "\nNNN  " or "\nNNN "
                for match in re.finditer(r"(?:^|\n)\s*(\d+)\s+", text):
                    current_line = int(match.group(1))

            # Font tag: check for red (uncovered)
            elif hasattr(child, "name") and child.name == "font":
                color = child.get("color", "")  # type: ignore[attr-defined]
                if color == "red" and current_line > 0:
                    text = child.get_text()
                    # Parse "0/N" format to get goal
                    hit_match = re.match(r"(\d+)/(\d+)", text)
                    goal = 1
                    if hit_match:
                        goal = int(hit_match.group(2)) or 1

                    if current_line not in seen_lines:
                        seen_lines.add(current_line)
                        gaps.append({
                            "coverage_type": "line",
                            "module": module_name,
                            "source_file": source_file,
                            "source_line": current_line,
                            "hit_count": 0,
                            "goal": goal,
                        })

    return gaps


# ---------------------------------------------------------------------------
# Branch Coverage
# ---------------------------------------------------------------------------


def _parse_branch_coverage(
    soup: BeautifulSoup, module_name: str, source_file: str | None
) -> list[dict]:
    """Parse branch coverage from <pre class="code"> + Branches tables.

    URG HTML pattern:
    - Summary table with [type, Line No., Total, Covered, Percent]
    - <pre class="code"> with source code (line number in first line)
    - <span class="repname">Branches:</span>
    - Truth table with -1-, -2-, ..., Status headers
    - uRed rows are uncovered branches
    """
    gaps: list[dict] = []

    # Step 1: Build branch_type map from summary table
    branch_type_map = _build_branch_type_map(soup)

    # Step 2: Find branch section
    branch_anchor = soup.find("a", attrs={"name": "Branch"})
    if not branch_anchor:
        return gaps

    # Step 3: Iterate through pre elements and their Branches tables
    current: Any = branch_anchor
    current_line = 0
    for _ in range(500):
        current = current.find_next()
        if current is None:
            break
        if not hasattr(current, "name"):
            continue

        # Stop at next section
        if current.name == "a":
            aname = current.get("name")
            if aname in ["Toggle", "Cond", "FSM", "Assert"]:
                break

        # Track line numbers from <pre class="code">
        if current.name == "pre":
            pre_class = current.get("class")
            if isinstance(pre_class, list) and "code" in pre_class:
                text = current.get_text()
                line_match = re.search(r"(?:^|\n)\s*(\d+)\s+", text)
                if line_match:
                    current_line = int(line_match.group(1))

        # Find Branches: span -> table
        if current.name == "span":
            span_class = current.get("class")
            if not isinstance(span_class, list) or "repname" not in span_class:
                continue
            if current.get_text(strip=True) != "Branches:":
                continue

            table = current.find_next("table")
            if not table:
                continue

            # Check if this is a truth table (has -1-, -2- headers)
            header_row = table.find("tr")
            if not header_row:
                continue
            headers = [
                th.get_text(strip=True) for th in header_row.find_all(["th", "td"])
            ]
            if not any(re.match(r"-\d+-", h) for h in headers):
                continue

            # Parse uRed rows
            for row in table.find_all("tr"):
                row_class_raw = row.get("class")
                row_class = (
                    row_class_raw if isinstance(row_class_raw, list) else []
                )
                if "uRed" not in row_class:
                    continue

                cells = row.find_all("td")
                if not cells:
                    continue

                # First cell is the branch direction
                direction_val = cells[0].get_text(strip=True)
                direction = "true" if direction_val == "1" else "false"
                btype = branch_type_map.get(current_line, "if")

                gaps.append({
                    "coverage_type": "branch",
                    "module": module_name,
                    "source_file": source_file,
                    "source_line": current_line,
                    "branch_type": btype,
                    "direction": direction,
                    "hit_count": 0,
                    "goal": 1,
                })

    return gaps


def _build_branch_type_map(soup: BeautifulSoup) -> dict[int, str]:
    """Build a map of line_number -> branch_type from the branch summary table.

    Looks for rows with IF/CASE/TERNARY in the first cell and line number
    in the second cell.
    """
    branch_type_map: dict[int, str] = {}

    branch_anchor = soup.find("a", attrs={"name": "Branch"})
    if not branch_anchor:
        return branch_type_map

    # Find the first table after the branch anchor (the summary table)
    current: Any = branch_anchor
    for _ in range(20):
        current = current.find_next()
        if current is None:
            break
        if not hasattr(current, "name"):
            continue
        if current.name == "table":
            rows = current.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    btype = cells[0].get_text(strip=True).upper()
                    if btype in ("IF", "CASE", "TERNARY"):
                        line_text = cells[1].get_text(strip=True)
                        try:
                            line_no = int(line_text)
                            branch_type_map[line_no] = btype.lower()
                        except ValueError:
                            pass
            break

    return branch_type_map


# ---------------------------------------------------------------------------
# Condition Coverage
# ---------------------------------------------------------------------------


def _parse_condition_coverage(
    soup: BeautifulSoup, module_name: str, source_file: str | None
) -> list[dict]:
    """Parse condition coverage from truth tables.

    URG HTML pattern:
    - <pre class="code"> contains "LINE N" and "EXPRESSION (expr)"
    - Truth table with -1-, -2-, ..., Status headers
    - uRed rows are uncovered condition combinations
    """
    gaps: list[dict] = []

    cond_anchor = soup.find("a", attrs={"name": "Cond"})
    if not cond_anchor:
        return gaps

    current: Any = cond_anchor
    current_line = 0
    current_expr = ""

    for _ in range(500):
        current = current.find_next()
        if current is None:
            break
        if not hasattr(current, "name"):
            continue

        # Stop at next section
        if current.name == "a":
            aname = current.get("name")
            if aname in ["Toggle", "Branch", "FSM", "Assert"]:
                break

        # Extract LINE and EXPRESSION from <pre class="code">
        if current.name == "pre":
            pre_class = current.get("class")
            if isinstance(pre_class, list) and "code" in pre_class:
                text = current.get_text()
                line_match = re.search(r"LINE\s+(\d+)", text)
                if line_match:
                    current_line = int(line_match.group(1))
                expr_match = re.search(r"EXPRESSION\s+\((.+)\)", text)
                if expr_match:
                    current_expr = expr_match.group(1).strip()

        # Parse truth tables
        if current.name == "table":
            header_row = current.find("tr")
            if not header_row:
                continue
            headers = [
                th.get_text(strip=True) for th in header_row.find_all(["th", "td"])
            ]
            if not any(re.match(r"-\d+-", h) for h in headers):
                continue

            for row in current.find_all("tr"):
                row_class_raw = row.get("class")
                row_class = (
                    row_class_raw if isinstance(row_class_raw, list) else []
                )
                if "uRed" not in row_class:
                    continue

                cells = row.find_all("td")
                if not cells:
                    continue

                # Combination = all cells except the last (Status) column
                combo_vals = [
                    c.get_text(strip=True) for c in cells[:-1]
                ]
                combo = "".join(combo_vals)

                gaps.append({
                    "coverage_type": "condition",
                    "module": module_name,
                    "source_file": source_file,
                    "source_line": current_line,
                    "condition_expr": current_expr,
                    "combination": combo,
                    "hit_count": 0,
                    "goal": 1,
                })

    return gaps


# ---------------------------------------------------------------------------
# Toggle Coverage
# ---------------------------------------------------------------------------


def _parse_toggle_coverage(
    soup: BeautifulSoup, module_name: str, source_file: str | None
) -> list[dict]:
    """Parse toggle coverage from Port/Signal Details tables.

    URG HTML pattern:
    - <caption>Port Details</caption> or <caption>Signal Details</caption>
    - Table columns: Name, Toggle, Toggle 1->0, Toggle 0->1 [, Direction]
    - "No" in Toggle 1->0 or Toggle 0->1 = missing transition
    - Generate one gap per missing direction per signal
    """
    gaps: list[dict] = []

    toggle_anchor = soup.find("a", attrs={"name": "Toggle"})
    if not toggle_anchor:
        return gaps

    for caption in soup.find_all("caption"):
        caption_text = caption.get_text(strip=True)
        if "Port Details" not in caption_text and "Signal Details" not in caption_text:
            continue

        table = caption.find_parent("table")
        if not table:
            continue

        rows = table.find_all("tr")[1:]  # Skip header

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            signal_name = cells[0].get_text(strip=True)
            toggle_1to0 = cells[2].get_text(strip=True)
            toggle_0to1 = cells[3].get_text(strip=True)

            # Each missing direction generates one gap
            if toggle_1to0 == "No":
                gaps.append({
                    "coverage_type": "toggle",
                    "module": module_name,
                    "signal": signal_name,
                    "toggle_dir": "1to0",
                    "hit_count": 0,
                    "goal": 1,
                })
            if toggle_0to1 == "No":
                gaps.append({
                    "coverage_type": "toggle",
                    "module": module_name,
                    "signal": signal_name,
                    "toggle_dir": "0to1",
                    "hit_count": 0,
                    "goal": 1,
                })

    return gaps


# ---------------------------------------------------------------------------
# FSM Coverage
# ---------------------------------------------------------------------------


def _parse_fsm_coverage(
    soup: BeautifulSoup, module_name: str, source_file: str | None
) -> list[dict]:
    """Parse FSM coverage from state/transition detail tables.

    URG HTML pattern:
    - <b>State, Transition and Sequence Details for FSM :: name</b>
    - States table: [states, Line No., Covered] with uRed rows
    - Transitions table: [transitions, Line No., Covered] with uRed rows
    """
    gaps: list[dict] = []

    fsm_anchor = soup.find("a", attrs={"name": "FSM"})
    if not fsm_anchor:
        return gaps

    # Find all FSM detail headings
    for b_tag in soup.find_all("b"):
        text = b_tag.get_text(strip=True)
        match = re.match(
            r"State, Transition and Sequence Details for FSM\s*::\s*(.+)", text
        )
        if not match:
            continue

        fsm_name = match.group(1).strip()

        # Look for tables after this heading
        current: Any = b_tag
        for _ in range(50):
            current = current.find_next()
            if current is None:
                break

            if not hasattr(current, "name"):
                continue

            # Stop at next FSM section or end
            if current.name == "b":
                next_text = current.get_text(strip=True)
                if "Details for FSM" in next_text:
                    break

            if current.name != "table":
                continue

            header_row = current.find("tr")
            if not header_row:
                continue
            headers = [
                th.get_text(strip=True).lower()
                for th in header_row.find_all(["th", "td"])
            ]
            if not headers:
                continue

            if "states" in headers[0]:
                # States table
                for row in current.find_all("tr"):
                    row_class_raw = row.get("class")
                    row_class = (
                        row_class_raw if isinstance(row_class_raw, list) else []
                    )
                    if "uRed" not in row_class:
                        continue
                    cells = row.find_all("td")
                    if cells:
                        state_name = cells[0].get_text(strip=True)
                        gaps.append({
                            "coverage_type": "fsm",
                            "module": module_name,
                            "fsm_name": fsm_name,
                            "state": state_name,
                            "hit_count": 0,
                            "goal": 1,
                        })

            elif "transitions" in headers[0]:
                # Transitions table
                for row in current.find_all("tr"):
                    row_class_raw = row.get("class")
                    row_class = (
                        row_class_raw if isinstance(row_class_raw, list) else []
                    )
                    if "uRed" not in row_class:
                        continue
                    cells = row.find_all("td")
                    if cells:
                        trans_name = cells[0].get_text(strip=True)
                        gaps.append({
                            "coverage_type": "fsm",
                            "module": module_name,
                            "fsm_name": fsm_name,
                            "state": trans_name,
                            "hit_count": 0,
                            "goal": 1,
                        })

    return gaps


# ---------------------------------------------------------------------------
# Assert Coverage
# ---------------------------------------------------------------------------


def _parse_assert_coverage(
    soup: BeautifulSoup, module_name: str, source_file: str | None
) -> list[dict]:
    """Parse assertion coverage from Assertion Details table.

    URG HTML pattern:
    - <b>Assertion Details</b> heading
    - Table: [Name, Attempts, Real Successes, Failures, Incomplete]
    - Rows where Real Successes == 0 are uncovered assertions
    """
    gaps: list[dict] = []

    assert_anchor = soup.find("a", attrs={"name": "Assert"})
    if not assert_anchor:
        return gaps

    details_heading = soup.find("b", string="Assertion Details")  # type: ignore[call-overload]
    if not details_heading:
        return gaps

    table = details_heading.find_next("table")
    if not table:
        return gaps

    rows = table.find_all("tr")[1:]  # Skip header
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        assert_name = cells[0].get_text(strip=True)
        try:
            successes = int(cells[2].get_text(strip=True))
            failures = int(cells[3].get_text(strip=True))
        except ValueError:
            continue

        # Uncovered if never succeeded
        if successes == 0:
            gaps.append({
                "coverage_type": "assert",
                "assert_name": assert_name,
                "module": module_name,
                "source_file": source_file or "",
                "source_line": 1,  # URG doesn't provide line; 1 is placeholder
                "fail_count": failures,
                "hit_count": successes,
                "goal": 1,
            })

    return gaps
