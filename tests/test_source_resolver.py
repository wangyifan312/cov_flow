"""Tests for lib.source_resolver — bounded source snippet resolver."""

from pathlib import Path

import pytest

from lib.source_resolver import SourceResolver, SourceSnippet


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a sample source file with 30 lines."""
    lines = [f"// Line {i + 1} of sample source\n" for i in range(30)]
    p = tmp_path / "sample.sv"
    p.write_text("".join(lines), encoding="utf-8")
    return p


@pytest.fixture
def large_file(tmp_path: Path) -> Path:
    """Create a file with long lines to test max_bytes truncation."""
    # Each line is ~200 bytes, 50 lines = ~10000 bytes total
    padding = "x" * 190
    lines = [f"// {padding} line {i + 1}\n" for i in range(50)]
    p = tmp_path / "large.sv"
    p.write_text("".join(lines), encoding="utf-8")
    return p


class TestSourceResolverNormalRead:
    def test_reads_snippet_around_target_line(self, sample_file: Path) -> None:
        resolver = SourceResolver(allowed_roots=[sample_file.parent])
        snippet = resolver.resolve(str(sample_file), source_line=15, context_lines=3)
        assert snippet.status == "ok"
        assert snippet.start_line == 12
        assert snippet.end_line == 18
        assert "Line 15" in snippet.content
        assert not snippet.truncated

    def test_reads_relative_path(self, tmp_path: Path, sample_file: Path) -> None:
        resolver = SourceResolver(allowed_roots=[tmp_path])
        snippet = resolver.resolve("sample.sv", source_line=5, context_lines=2)
        assert snippet.status == "ok"
        assert "Line 5" in snippet.content
        assert snippet.file == "sample.sv"

    def test_context_clamped_to_file_start(self, sample_file: Path) -> None:
        resolver = SourceResolver(allowed_roots=[sample_file.parent])
        snippet = resolver.resolve(str(sample_file), source_line=1, context_lines=5)
        assert snippet.status == "ok"
        assert snippet.start_line == 1

    def test_context_clamped_to_file_end(self, sample_file: Path) -> None:
        resolver = SourceResolver(allowed_roots=[sample_file.parent])
        snippet = resolver.resolve(str(sample_file), source_line=30, context_lines=5)
        assert snippet.status == "ok"
        assert snippet.end_line == 30


class TestSourceResolverPathTraversal:
    def test_double_dot_rejected(self, tmp_path: Path) -> None:
        resolver = SourceResolver(allowed_roots=[tmp_path])
        snippet = resolver.resolve("../../etc/passwd", source_line=1)
        assert snippet.status == "access_denied"
        assert "traversal" in snippet.message.lower()

    def test_absolute_path_outside_root_rejected(self, tmp_path: Path) -> None:
        resolver = SourceResolver(allowed_roots=[tmp_path])
        snippet = resolver.resolve("/etc/hostname", source_line=1)
        assert snippet.status == "access_denied"

    def test_symlink_escape_rejected(self, tmp_path: Path) -> None:
        # Create a target file outside allowed root
        outside = tmp_path / "outside"
        outside.mkdir()
        target = outside / "secret.sv"
        target.write_text("// secret content\n", encoding="utf-8")

        # Create allowed root with symlink pointing outside
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        link = allowed / "link.sv"
        link.symlink_to(target)

        resolver = SourceResolver(allowed_roots=[allowed])
        snippet = resolver.resolve(str(link), source_line=1)
        assert snippet.status == "access_denied"
        assert "symlink" in snippet.message.lower()


class TestSourceResolverFileNotFound:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        resolver = SourceResolver(allowed_roots=[tmp_path])
        snippet = resolver.resolve("nonexistent.sv", source_line=1)
        assert snippet.status == "file_not_found"

    def test_nonexistent_absolute_file(self, tmp_path: Path) -> None:
        resolver = SourceResolver(allowed_roots=[tmp_path])
        snippet = resolver.resolve(str(tmp_path / "missing.sv"), source_line=1)
        assert snippet.status == "file_not_found"


class TestSourceResolverMaxLines:
    def test_max_lines_bounds_snippet(self, sample_file: Path) -> None:
        resolver = SourceResolver(allowed_roots=[sample_file.parent], max_lines=5)
        snippet = resolver.resolve(str(sample_file), source_line=15, context_lines=10)
        assert snippet.status == "ok"
        line_count = snippet.end_line - snippet.start_line + 1
        assert line_count <= 5

    def test_max_lines_clamped_to_100(self, sample_file: Path) -> None:
        resolver = SourceResolver(allowed_roots=[sample_file.parent], max_lines=200)
        assert resolver.max_lines == 100


class TestSourceResolverMaxBytes:
    def test_max_bytes_truncation(self, tmp_path: Path, large_file: Path) -> None:
        resolver = SourceResolver(
            allowed_roots=[tmp_path], max_lines=100, max_bytes=500
        )
        snippet = resolver.resolve(str(large_file), source_line=25, context_lines=20)
        assert snippet.status == "ok"
        assert snippet.truncated is True
        assert "[truncated]" in snippet.content
        assert len(snippet.content.encode("utf-8")) <= 600  # 500 + truncation marker

    def test_no_truncation_for_small_snippet(self, sample_file: Path) -> None:
        resolver = SourceResolver(allowed_roots=[sample_file.parent], max_bytes=4096)
        snippet = resolver.resolve(str(sample_file), source_line=15, context_lines=3)
        assert snippet.status == "ok"
        assert snippet.truncated is False


class TestSourceResolverMultipleRoots:
    def test_resolves_from_second_root(self, tmp_path: Path) -> None:
        root_a = tmp_path / "root_a"
        root_b = tmp_path / "root_b"
        root_a.mkdir()
        root_b.mkdir()
        (root_b / "file.sv").write_text("// from root_b\n", encoding="utf-8")

        resolver = SourceResolver(allowed_roots=[root_a, root_b])
        snippet = resolver.resolve("file.sv", source_line=1)
        assert snippet.status == "ok"
        assert "root_b" in snippet.content

    def test_file_not_in_any_root(self, tmp_path: Path) -> None:
        root_a = tmp_path / "root_a"
        root_a.mkdir()
        resolver = SourceResolver(allowed_roots=[root_a])
        snippet = resolver.resolve("unknown.sv", source_line=1)
        # Relative path resolves under root_a but file doesn't exist
        assert snippet.status == "file_not_found"


class TestSourceSnippetDataclass:
    def test_default_values(self) -> None:
        s = SourceSnippet(file="test.sv", start_line=1, end_line=10, content="hello")
        assert s.truncated is False
        assert s.status == "ok"
        assert s.message == ""

    def test_custom_values(self) -> None:
        s = SourceSnippet(
            file="test.sv", start_line=5, end_line=15, content="data",
            truncated=True, status="ok", message="Read 11 lines",
        )
        assert s.truncated is True
        assert s.message == "Read 11 lines"
