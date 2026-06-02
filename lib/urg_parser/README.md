# URG HTML Coverage Report Parser

Parses Synopsys VCS URG (Unified Report Generator) HTML coverage reports into
structured JSON indexes compatible with the DV AI Coverage Closure Skill Pack.

## Supported URG Report Version

- **VCS Version**: Synopsys VCS O-2018.09-SP2
- **URG command**: `urg -dir <simv_dir> -report <output_dir>`

Other VCS versions may produce different HTML structures and are **not
currently supported**. If you need support for a different version, please
file an issue with sample report files.

## Supported File Types

| File | Parser | Description |
|------|--------|-------------|
| `session.xml` | `session.py` | Report metadata, per-type coverage metrics |
| `modlist.html` | `structure.py` | Module hierarchy and design structure |
| `groups.html` | `structure.py` | Functional coverage group listing |
| `grp*.html` | `functional.py` | Functional coverage details (covergroup/coverpoint/bin) |
| `mod*.html` | `code_coverage.py` | Code coverage details (line/branch/condition/toggle/fsm/assert) |

## Supported Coverage Types

| Type | Gap ID Prefix | Source File |
|------|---------------|-------------|
| functional | `GAP_XXXX` | `grp*.html` |
| line | `GAP_LNNN` | `mod*.html` |
| branch | `GAP_BNNN` | `mod*.html` |
| condition | `GAP_CNNN` | `mod*.html` |
| toggle | `GAP_TNNN` | `mod*.html` |
| fsm | `GAP_MNNN` | `mod*.html` |
| assert | `GAP_ANNN` | `mod*.html` |

## Synopsys Library File Filtering

The parser automatically filters out Synopsys VCS library files during gap
extraction. Any source file with a path containing `/opt/synopsys/` is excluded.
These are UVM library files from the VCS installation and not part of the
user design.

## Unsupported Situations

The following are **not supported** and may cause parser warnings or errors:

- **Other VCS versions** (e.g., VCS 2020.x, VCS 2021.x, VCS 2022.x) — HTML
  structure may differ
- **Other EDA vendor reports** (Cadence IMC, Mentor Questa) — completely
  different formats
- **Custom URG options** — non-standard report layouts may not parse correctly
- **Encrypted/obfuscated reports** — parser requires readable HTML content
- **Very large reports** (>10,000 modules) — parser may be slow but should
  still produce output

## Parser Failure Behavior

| Situation | Behavior |
|-----------|----------|
| Missing required file (e.g., `session.xml`) | **Error**: parser exits with descriptive message |
| Malformed HTML in optional file | **Warning**: skips affected module/group, continues |
| Unsupported file format | **Warning**: logs unsupported format, skips file |
| Empty coverage data | **Warning**: produces 0 gaps, no error |
| Path traversal attempt | **Blocked**: paths validated against project root allowlist |

## CLI Usage

```bash
# Build coverage index from URG report
python scripts/build_coverage_index.py --manifest mock_data/axi2ahb/project_manifest.yaml

# Or via Makefile
make build-real-index
```

## Output

The parser produces two JSON files in the project's `.dv_ai_index/` directory:

- **`coverage_index.json`** — Full coverage metrics and gap listing
- **`coverage_gaps.json`** — Schema-compliant gap details for MCP tools

Both files are compatible with the DV Context MCP Server and all downstream tools.

## Extending Parser Support

To add support for new URG report versions or file types:

1. Identify the HTML structure differences
2. Add new parsing logic in the appropriate module
3. Update this README with the new supported version/format
4. Add test cases for the new parsing logic
