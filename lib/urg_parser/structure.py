"""Parse URG modlist.html and groups.html for structural mapping."""

from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup


@dataclass
class ModuleInfo:
    """Module definition from modlist.html."""
    name: str
    mod_file: str  # e.g., "mod23.html"
    score: float | None
    line_score: float | None
    cond_score: float | None
    toggle_score: float | None
    fsm_score: float | None
    branch_score: float | None
    assert_score: float | None


@dataclass
class GroupInfo:
    """Functional coverage group from groups.html."""
    name: str
    grp_file: str  # e.g., "grp0.html"
    score: float | None
    instances: int | None


def parse_module_list(report_dir: Path) -> list[ModuleInfo]:
    """Parse modlist.html to extract module definitions and file mappings.

    Args:
        report_dir: Path to URG report directory.

    Returns:
        List of ModuleInfo, one per module definition.
    """
    modlist_path = report_dir / "modlist.html"
    if not modlist_path.exists():
        raise FileNotFoundError(f"modlist.html not found in {report_dir}")

    with open(modlist_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    modules: list[ModuleInfo] = []
    table = soup.find("table", class_="sortable")
    if table is None:
        return modules

    for row in table.find_all("tr"):
        # Skip header rows
        if row.find("th"):
            continue

        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        # Module rows have data-tt-id="mod_{N}"
        tt_id = row.get("data-tt-id", "")
        if not isinstance(tt_id, str) or not tt_id.startswith("mod_"):
            continue

        # First cell: module name with link
        # The cell may have multiple <a> tags, we need the one with href
        name_cell = cells[0]
        name_link = name_cell.find("a", href=True)
        if name_link is None:
            continue
        module_name = name_link.get_text(strip=True)
        mod_href = name_link.get("href", "")
        if not isinstance(mod_href, str) or not mod_href:
            continue

        # Coverage score cells (SCORE, LINE, COND, TOGGLE, FSM, BRANCH, ASSERT)
        def _cell_score(idx: int) -> float | None:
            if idx >= len(cells):
                return None
            text = cells[idx].get_text(strip=True)
            if not text or "wht" in (cells[idx].get("class") or []):
                return None
            try:
                return float(text)
            except ValueError:
                return None

        modules.append(ModuleInfo(
            name=module_name,
            mod_file=mod_href.split("#")[0],  # strip anchor
            score=_cell_score(1),
            line_score=_cell_score(2),
            cond_score=_cell_score(3),
            toggle_score=_cell_score(4),
            fsm_score=_cell_score(5),
            branch_score=_cell_score(6),
            assert_score=_cell_score(7),
        ))

    return modules


def parse_group_list(report_dir: Path) -> list[GroupInfo]:
    """Parse groups.html to extract functional coverage group definitions.

    Args:
        report_dir: Path to URG report directory.

    Returns:
        List of GroupInfo, one per functional coverage group.
    """
    groups_path = report_dir / "groups.html"
    if not groups_path.exists():
        raise FileNotFoundError(f"groups.html not found in {report_dir}")

    with open(groups_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    groups: list[GroupInfo] = []
    table = soup.find("table", class_="sortable")
    if table is None:
        return groups

    for row in table.find_all("tr"):
        if row.find("th"):
            continue

        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        # Group rows have data-tt-id starting with "grpinst_hash_"
        tt_id = row.get("data-tt-id", "")
        if not isinstance(tt_id, str) or not tt_id.startswith("grpinst_hash_"):
            continue

        # First cell: group name with link to grp file
        name_cell = cells[0]
        name_link = name_cell.find("a", href=True)
        if name_link is None:
            continue

        # Extract group name from the anchor text or <a name="tag_...">
        group_name = name_link.get_text(strip=True)
        grp_href = name_link.get("href", "")
        if not isinstance(grp_href, str) or not grp_href:
            continue

        score = None
        if len(cells) > 1:
            text = cells[1].get_text(strip=True)
            try:
                score = float(text.rstrip("%"))
            except ValueError:
                pass

        # Instances cell
        instances = None
        if len(cells) > 2:
            text = cells[2].get_text(strip=True)
            try:
                instances = int(text)
            except ValueError:
                pass

        groups.append(GroupInfo(
            name=group_name,
            grp_file=grp_href.split("#")[0],
            score=score,
            instances=instances,
        ))

    return groups
