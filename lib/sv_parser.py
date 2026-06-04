"""Generic SystemVerilog parser for UVM testbench analysis.

Regex-based extraction of classes, modules, methods, config_db usage,
and feature tag inference. Project-agnostic: no hardcoded names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SVMethodInfo:
    """A task or function declaration."""

    name: str
    signature: str
    return_type: str | None
    is_virtual: bool
    is_task: bool
    description: str = ""


@dataclass
class SVClassInfo:
    """A SystemVerilog class declaration."""

    name: str
    file: str
    extends: str | None
    utils_macro: str | None  # "uvm_component_utils" | "uvm_object_utils" | None
    methods: list[SVMethodInfo] = field(default_factory=list)
    feature_tags: list[str] = field(default_factory=list)


@dataclass
class SVModuleInfo:
    """A SystemVerilog module declaration."""

    name: str
    file: str
    line_range: tuple[int, int] = (0, 0)
    ports: list[str] = field(default_factory=list)
    parameters: list[dict] = field(default_factory=list)
    instances: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    fsm_states: list[str] = field(default_factory=list)


@dataclass
class ParsedFile:
    """All extracted items from a single .sv/.svh file."""

    file: str
    classes: list[SVClassInfo] = field(default_factory=list)
    modules: list[SVModuleInfo] = field(default_factory=list)
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Compiled regex patterns (all generic, no hardcoded names)
# ---------------------------------------------------------------------------

RE_CLASS = re.compile(
    r"class\s+(\w+)"
    r"(?:\s*#\s*\([^)]*\))?"
    r"(?:\s+extends\s+(\w+)"
    r"(?:\s*#\s*\([^)]*\))?"
    r")?"
    r"(?:\s+implements\s+[\w\s,]+)?"
    r"\s*;",
    re.MULTILINE,
)

RE_UVM_COMPONENT_UTILS = re.compile(
    r"`uvm_component_utils\s*\(\s*(\w+)\s*\)", re.MULTILINE
)
RE_UVM_OBJECT_UTILS = re.compile(
    r"`uvm_object_utils\s*\(\s*(\w+)\s*\)", re.MULTILINE
)

RE_TASK = re.compile(
    r"(virtual\s+)?task\s+(?:automatic\s+)?(\w+)\s*\(([^)]*)\)\s*;",
    re.MULTILINE | re.DOTALL,
)

RE_FUNCTION = re.compile(
    r"(virtual\s+)?"
    r"function\s+(?:automatic\s+)?"
    r"([\w\s\[\]:.*$]+?\s+)?"
    r"(\w+)\s*\(([^)]*)\)\s*;",
    re.MULTILINE | re.DOTALL,
)

RE_MODULE = re.compile(
    r"module\s+(\w+)"
    r"(?:\s*#\s*\((.*?)\))?"
    r"\s*\((.*?)\)\s*;",
    re.MULTILINE | re.DOTALL,
)

RE_PORT = re.compile(
    r"(input|output|inout)\s+"
    r"(?:logic\s+)?"
    r"(?:\[([^\]]+)\]\s+)?"
    r"(\w+)",
    re.MULTILINE,
)

RE_ENUM = re.compile(
    r"typedef\s+enum\s+(?:\w+(?:\s*\[[^\]]*\])?\s+)?"
    r"\{([^}]+)\}"
    r"\s*(\w+)?\s*;",
    re.MULTILINE | re.DOTALL,
)

RE_CONFIG_DB = re.compile(
    r"uvm_config_db\s*#\s*\(\s*([\w\s:.*$]+?)\s*\)"
    r"\s*::\s*(set|get)\s*\(([^)]+)\)",
    re.MULTILINE | re.DOTALL,
)

RE_PLUSARG = re.compile(
    r'(?:get_arg_value|value\$plusargs|uvm_cmdline_proc_get_arg)'
    r'\s*\(\s*"[+]?(\w+)='
    ,
    re.MULTILINE,
)

RE_INCLUDE = re.compile(r'`include\s+"([^"]+)"', re.MULTILINE)

RE_SEQ_START = re.compile(r"(\w+)\s*\.\s*start\s*\(", re.MULTILINE)

RE_MEMBER_VAR = re.compile(
    r"^[ \t]*"
    r"((?:int\s+unsigned|bit|logic|reg|int|integer|byte|shortint|longint"
    r"|unsigned\s+int|real|string"
    r"|\w+(?:\s*#\s*\([^)]*\))?))"
    r"(?:\s*\[([^\]]+)\])?"
    r"\s+(\w+)"
    r"""(?:\s*=\s*("[^"]*"|[^;]+?))?"""
    r"\s*;",
    re.MULTILINE,
)

# UVM base class names for role classification (framework constants)
_UVM_ROLES: dict[str, set[str]] = {
    "test": {"uvm_test"},
    "sequence": {"uvm_sequence", "uvm_sequence_base"},
    "env": {"uvm_env"},
    "agent": {"uvm_agent"},
    "scoreboard": {"uvm_scoreboard"},
    "subscriber": {"uvm_subscriber"},
    "sequencer": {"uvm_sequencer"},
    "driver": {"uvm_driver"},
    "monitor": {"uvm_monitor"},
    "object": {"uvm_object"},
    "transaction": {"uvm_sequence_item", "uvm_transaction"},
}


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------


def _preceding_comment(text: str, match_start: int) -> str:
    """Extract the last // comment line immediately preceding a match."""
    prefix = text[:match_start].rstrip()
    lines = prefix.split("\n")
    for i in range(len(lines) - 1, max(len(lines) - 6, -1), -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            return stripped[2:].strip()
        break
    return ""


def extract_classes(sv_text: str, file: str = "") -> list[SVClassInfo]:
    """Extract class declarations with UVM macros and methods."""
    classes: list[SVClassInfo] = []
    matches = list(RE_CLASS.finditer(sv_text))

    for idx, m in enumerate(matches):
        name = m.group(1)
        extends = m.group(2)
        class_start = m.start()
        class_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(sv_text)
        body = sv_text[class_start:class_end]

        # UVM utils macro
        utils_macro: str | None = None
        comp_m = RE_UVM_COMPONENT_UTILS.search(body)
        obj_m = RE_UVM_OBJECT_UTILS.search(body)
        if comp_m and comp_m.group(1) == name:
            utils_macro = "uvm_component_utils"
        elif obj_m and obj_m.group(1) == name:
            utils_macro = "uvm_object_utils"

        # Methods
        methods = _extract_methods_from_body(body)

        # Feature tags
        method_names = [mth.name for mth in methods]
        feature_tags = infer_feature_tags(name, file, " ".join(method_names))

        classes.append(
            SVClassInfo(
                name=name,
                file=file,
                extends=extends,
                utils_macro=utils_macro,
                methods=methods,
                feature_tags=feature_tags,
            )
        )

    return classes


def _extract_methods_from_body(body: str) -> list[SVMethodInfo]:
    """Extract methods from a class body region."""
    methods: list[SVMethodInfo] = []
    seen: set[str] = set()

    for m in RE_TASK.finditer(body):
        name = m.group(2)
        if name in seen:
            continue
        seen.add(name)
        desc = _preceding_comment(body, m.start())
        methods.append(
            SVMethodInfo(
                name=name,
                signature=m.group(3).strip(),
                return_type=None,
                is_virtual=bool(m.group(1)),
                is_task=True,
                description=desc,
            )
        )

    for m in RE_FUNCTION.finditer(body):
        name = m.group(3)
        if name in ("endfunction", "endtask", "endclass", "endmodule"):
            continue
        if name in seen:
            continue
        seen.add(name)
        ret_type = (m.group(2) or "").strip() or None
        desc = _preceding_comment(body, m.start())
        methods.append(
            SVMethodInfo(
                name=name,
                signature=m.group(4).strip(),
                return_type=ret_type,
                is_virtual=bool(m.group(1)),
                is_task=False,
                description=desc,
            )
        )

    return methods


def extract_modules(sv_text: str, file: str = "") -> list[SVModuleInfo]:
    """Extract module declarations with ports/parameters."""
    modules: list[SVModuleInfo] = []

    for m in RE_MODULE.finditer(sv_text):
        name = m.group(1)
        params_raw = m.group(2) or ""
        ports_raw = m.group(3) or ""

        # Parse ports
        ports: list[str] = []
        for pm in RE_PORT.finditer(ports_raw):
            ports.append(f"{pm.group(1)} {pm.group(3)}")

        # Parse parameters
        parameters: list[dict] = []
        if params_raw:
            for param_m in re.finditer(
                r"(?:parameter\s+)?(\w+)\s+(\w+)\s*=\s*([^,;]+)", params_raw
            ):
                parameters.append(
                    {
                        "type": param_m.group(1),
                        "name": param_m.group(2),
                        "default": param_m.group(3).strip(),
                    }
                )

        # Line range
        start_line = sv_text[: m.start()].count("\n") + 1
        end_m = re.search(r"\bendmodule\b", sv_text[m.end() :])
        if end_m:
            end_line = sv_text[: m.end() + end_m.end()].count("\n") + 1
        else:
            end_line = start_line

        # FSM states
        fsm_states: list[str] = []
        mod_end = m.end() + (end_m.end() if end_m else 0)
        mod_body = sv_text[m.start() : mod_end]
        for em in RE_ENUM.finditer(mod_body):
            members_str = em.group(1)
            members = [s.strip().split("=")[0].strip() for s in members_str.split(",")]
            fsm_states.extend(m for m in members if m)

        modules.append(
            SVModuleInfo(
                name=name,
                file=file,
                line_range=(start_line, end_line),
                ports=ports,
                parameters=parameters,
                fsm_states=fsm_states,
            )
        )

    return modules


def extract_methods(sv_text: str) -> list[SVMethodInfo]:
    """Extract task/function signatures from SV text."""
    methods: list[SVMethodInfo] = []
    seen: set[str] = set()

    for m in RE_TASK.finditer(sv_text):
        name = m.group(2)
        if name in seen:
            continue
        seen.add(name)
        desc = _preceding_comment(sv_text, m.start())
        methods.append(
            SVMethodInfo(
                name=name,
                signature=m.group(3).strip(),
                return_type=None,
                is_virtual=bool(m.group(1)),
                is_task=True,
                description=desc,
            )
        )

    for m in RE_FUNCTION.finditer(sv_text):
        name = m.group(3)
        if name in ("endfunction", "endtask", "endclass", "endmodule"):
            continue
        if name in seen:
            continue
        seen.add(name)
        ret_type = (m.group(2) or "").strip() or None
        desc = _preceding_comment(sv_text, m.start())
        methods.append(
            SVMethodInfo(
                name=name,
                signature=m.group(4).strip(),
                return_type=ret_type,
                is_virtual=bool(m.group(1)),
                is_task=False,
                description=desc,
            )
        )

    return methods


def extract_config_db_usage(sv_text: str) -> list[dict]:
    """Extract uvm_config_db set/get patterns."""
    results: list[dict] = []
    for m in RE_CONFIG_DB.finditer(sv_text):
        results.append(
            {
                "type_param": m.group(1).strip(),
                "kind": m.group(2),
                "args": m.group(3).strip(),
            }
        )
    return results


def extract_plusargs(sv_text: str) -> list[dict]:
    """Extract +plusarg=%d patterns."""
    results: list[dict] = []
    for m in RE_PLUSARG.finditer(sv_text):
        results.append({"name": m.group(1)})
    return results


# ---------------------------------------------------------------------------
# Feature tag inference
# ---------------------------------------------------------------------------

_TAG_KEYWORDS: dict[str, list[str]] = {
    "write": ["write"],
    "read": ["read"],
    "burst": ["burst"],
    "error": ["error", "exception"],
    "fifo": ["fifo"],
    "reset": ["reset", "recovery"],
    "wrap": ["wrap"],
    "incr": ["incr"],
    "fixed": ["fixed"],
    "random": ["random"],
    "traffic": ["traffic"],
    "stress": ["stress"],
    "single": ["single"],
    "mixed": ["mixed"],
    "backend": ["backend"],
    "frontend": ["frontend"],
}


def infer_feature_tags(name: str, file: str = "", body: str = "") -> list[str]:
    """Heuristic feature tag inference from naming and content.

    Applies keyword rules to the lowercased name and file basename.
    Returns deduplicated sorted list of tag strings.
    """
    text = (name + " " + Path(file).stem).lower()
    if body:
        text += " " + body.lower()
    tags: set[str] = set()
    for tag, keywords in _TAG_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                tags.add(tag)
                break
    return sorted(tags)


# ---------------------------------------------------------------------------
# Extends chain resolution and UVM role classification
# ---------------------------------------------------------------------------


def resolve_extends_chain(classes: list[SVClassInfo]) -> dict[str, list[str]]:
    """Build extends ancestry chains for all parsed classes.

    Returns dict mapping class name -> [parent, grandparent, ...].
    """
    parent_map: dict[str, str] = {}
    for cls in classes:
        if cls.extends:
            parent_map[cls.name] = cls.extends

    result: dict[str, list[str]] = {}
    for cls in classes:
        chain: list[str] = []
        current = cls.extends
        visited: set[str] = set()
        while current and current not in visited:
            chain.append(current)
            visited.add(current)
            current = parent_map.get(current)
        result[cls.name] = chain
    return result


def classify_uvm_role(
    cls: SVClassInfo, ancestry: dict[str, list[str]]
) -> str:
    """Determine the UVM role of a class based on its ancestry."""
    chain = ancestry.get(cls.name, [])
    all_ancestors = set(chain)
    if cls.extends:
        all_ancestors.add(cls.extends)

    for role in (
        "test", "sequence", "env", "agent", "scoreboard", "subscriber",
        "sequencer", "driver", "monitor", "transaction", "object",
    ):
        if all_ancestors & _UVM_ROLES[role]:
            return role

    if cls.utils_macro == "uvm_component_utils":
        return "unknown"
    if cls.utils_macro == "uvm_object_utils":
        return "object"

    return "unknown"


# ---------------------------------------------------------------------------
# Test-to-sequence linking
# ---------------------------------------------------------------------------


def link_tests_to_sequences(
    test_classes: list[SVClassInfo],
    seq_classes: list[SVClassInfo],
    raw_texts: dict[str, str],
) -> dict[str, list[str]]:
    """Find which sequences each test starts."""
    seq_names = {cls.name for cls in seq_classes}
    result: dict[str, list[str]] = {}

    for test_cls in test_classes:
        test_text = raw_texts.get(test_cls.file, "")
        linked: set[str] = set()

        # Phase 1: .start() variable -> type resolution
        for start_m in RE_SEQ_START.finditer(test_text):
            var_name = start_m.group(1)
            type_m = re.search(
                rf"(\w+)\s+{re.escape(var_name)}\s*[;=]", test_text
            )
            if type_m and type_m.group(1) in seq_names:
                linked.add(type_m.group(1))

        # Phase 2: Direct type name references
        for seq_name in seq_names:
            if re.search(rf"\b{re.escape(seq_name)}\b", test_text):
                linked.add(seq_name)

        result[test_cls.name] = sorted(linked)

    return result


# ---------------------------------------------------------------------------
# Config knob extraction
# ---------------------------------------------------------------------------


def extract_config_knobs(
    config_classes: list[SVClassInfo],
    raw_texts: dict[str, str],
) -> list[dict]:
    """Extract config knob definitions from config classes."""
    all_plusargs: dict[str, str] = {}
    for text in raw_texts.values():
        for pm in RE_PLUSARG.finditer(text):
            all_plusargs[pm.group(1).lower()] = f"+{pm.group(1)}="

    knobs: list[dict] = []
    seen_names: set[str] = set()

    for cls in config_classes:
        cls_text = raw_texts.get(cls.file, "")
        for m in RE_MEMBER_VAR.finditer(cls_text):
            type_name = m.group(1).strip()
            if type_name.startswith("virtual"):
                continue
            var_name = m.group(3)
            if var_name in seen_names:
                continue
            seen_names.add(var_name)
            default = m.group(4) or ""
            default = default.strip().strip('"')

            plusarg = all_plusargs.get(var_name.lower(), "")

            knobs.append(
                {
                    "name": var_name,
                    "type": type_name,
                    "default": default,
                    "plusarg": plusarg,
                }
            )

    return knobs


# ---------------------------------------------------------------------------
# File parsing
# ---------------------------------------------------------------------------


def parse_sv_file(path: Path, *, project_root: Path) -> ParsedFile:
    """Parse a single .sv/.svh file and return all extracted items."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ParsedFile(file=str(path))

    try:
        rel = str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        rel = str(path)

    classes = extract_classes(text, file=rel)
    modules = extract_modules(text, file=rel)

    return ParsedFile(
        file=rel,
        classes=classes,
        modules=modules,
        raw_text=text,
    )


def parse_directory(
    dirpath: Path,
    *,
    project_root: Path,
    extensions: tuple[str, ...] = (".sv", ".svh"),
    recursive: bool = True,
) -> list[ParsedFile]:
    """Parse all SV files in a directory tree."""
    if not dirpath.is_dir():
        return []

    results: list[ParsedFile] = []
    if recursive:
        files = sorted(
            p for p in dirpath.rglob("*") if p.is_file() and p.suffix in extensions
        )
    else:
        files = sorted(
            p for p in dirpath.iterdir() if p.is_file() and p.suffix in extensions
        )

    for f in files:
        parsed = parse_sv_file(f, project_root=project_root)
        results.append(parsed)

    return results
