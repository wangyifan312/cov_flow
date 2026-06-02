"""Parse URG session.xml for metadata and aggregate metrics."""

import xml.etree.ElementTree as ET
from pathlib import Path


def parse_session_xml(report_dir: Path) -> dict:
    """Parse session.xml and return metadata + aggregate metrics.

    Args:
        report_dir: Path to the URG report directory containing session.xml.

    Returns:
        dict with keys:
            version: str — URG release version
            datetime: str — report generation timestamp
            command: str — URG command used
            top_instance: str — top-level instance name
            metrics: dict — per-type coverage metrics {type: {covered, total, percent}}
            groups: list — functional coverage group names with scores
    """
    session_path = report_dir / "session.xml"
    if not session_path.exists():
        raise FileNotFoundError(f"session.xml not found in {report_dir}")

    tree = ET.parse(session_path)
    root = tree.getroot()

    # Extract info attributes
    info = root.find("info")
    attrs = {}
    if info is not None:
        for attr in info.findall("attr"):
            name = attr.get("name", "")
            value = attr.get("value", "")
            attrs[name] = value

    # Parse top_instance (comma-separated, take last one)
    top_inst_raw = attrs.get("top_instance", "")
    top_instance = top_inst_raw.split(",")[-1].strip() if top_inst_raw else "unknown"

    # Extract metrics from scope type="top"
    metrics = {}
    old_cov = root.find("old_coverage")
    if old_cov is not None:
        top_scope = old_cov.find('.//scope[@type="top"]')
        if top_scope is not None:
            for metric in top_scope.findall("metric"):
                name = metric.get("name", "")
                value = metric.get("value", "")
                if name and value:
                    metrics[name] = _parse_metric_value(value)

    # Extract group scores
    groups = []
    if old_cov is not None:
        group_scope = old_cov.find('.//scope[@type="group"][@name="top"]')
        if group_scope is not None:
            for child in group_scope.findall('scope[@type="group"]'):
                group_name = child.get("name", "")
                group_metric = child.find('metric[@name="Group"]')
                group_score = None
                if group_metric is not None:
                    parsed = _parse_metric_value(group_metric.get("value", "0%"))
                    group_score = parsed.get("percent")
                groups.append({
                    "name": group_name,
                    "score": group_score,
                })

    return {
        "version": root.get("release", "unknown"),
        "command": attrs.get("command", ""),
        "top_instance": top_instance,
        "metrics": metrics,
        "groups": groups,
    }


def _parse_metric_value(value: str) -> dict:
    """Parse a URG metric value string.

    Handles two formats:
    - Ratio: "708/1194" → {"covered": 708, "total": 1194, "percent": round(708/1194*100, 2)}
    - Percentage: "82.7381%" → {"covered": None, "total": None, "percent": 82.74}
    """
    value = value.strip()
    if value.endswith("%"):
        pct = float(value.rstrip("%"))
        return {"covered": None, "total": None, "percent": round(pct, 2)}
    elif "/" in value:
        parts = value.split("/")
        covered = int(parts[0])
        total = int(parts[1])
        pct = round(covered / total * 100, 2) if total > 0 else 0.0
        return {"covered": covered, "total": total, "percent": pct}
    return {"covered": None, "total": None, "percent": None}
