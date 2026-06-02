"""URG HTML coverage report parser library.

This package provides parsers for Synopsys VCS URG (Unified Report Generator)
HTML coverage reports. It supports:

- session.xml parsing for metadata and metrics
- modlist.html parsing for module structure
- groups.html parsing for functional coverage groups
- grp*.html parsing for functional coverage gaps (coverpoints, crosses)
- mod*.html parsing for code coverage gaps (line, branch, condition, toggle, fsm, assert)

Usage:
    from lib.urg_parser import (
        parse_session_xml,
        parse_module_list,
        parse_group_list,
        parse_functional_coverage,
        parse_code_coverage,
        assemble_gaps,
        build_coverage_index,
        build_coverage_gaps,
        write_index_files,
    )
"""

from lib.urg_parser.code_coverage import parse_code_coverage
from lib.urg_parser.functional import parse_functional_coverage
from lib.urg_parser.gap_assembler import assemble_gaps
from lib.urg_parser.index_builder import (
    build_coverage_gaps,
    build_coverage_index,
    write_index_files,
)
from lib.urg_parser.session import parse_session_xml
from lib.urg_parser.structure import parse_group_list, parse_module_list

__all__ = [
    "parse_session_xml",
    "parse_module_list",
    "parse_group_list",
    "parse_functional_coverage",
    "parse_code_coverage",
    "assemble_gaps",
    "build_coverage_index",
    "build_coverage_gaps",
    "write_index_files",
]
