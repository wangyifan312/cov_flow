"""Tests for audit logging service."""

from datetime import datetime

from dv_mcp.dv_context_server.services.audit import audit_record


class TestAuditRecord:
    def test_audit_record_structure(self) -> None:
        record = audit_record("test_tool", "test_project", {"arg1": "val1"})
        assert "user" in record
        assert "project" in record
        assert "tool" in record
        assert "arg_hash" in record
        assert "timestamp" in record
        assert "result_size" in record
        assert record["user"] == "mock_user"
        assert record["project"] == "test_project"
        assert record["tool"] == "test_tool"

    def test_arg_hash_deterministic(self) -> None:
        args = {"key": "value", "num": 42}
        r1 = audit_record("tool", "proj", args)
        r2 = audit_record("tool", "proj", args)
        assert r1["arg_hash"] == r2["arg_hash"]
        assert len(r1["arg_hash"]) == 16

    def test_arg_hash_differs_for_different_args(self) -> None:
        r1 = audit_record("tool", "proj", {"a": 1})
        r2 = audit_record("tool", "proj", {"a": 2})
        assert r1["arg_hash"] != r2["arg_hash"]

    def test_timestamp_iso_format(self) -> None:
        record = audit_record("tool", "proj", {})
        # Should be a valid ISO 8601 timestamp
        ts = datetime.fromisoformat(record["timestamp"])
        assert ts.year >= 2024

    def test_result_size_default_zero(self) -> None:
        record = audit_record("tool", "proj", {})
        assert record["result_size"] == 0

    def test_result_size_custom(self) -> None:
        record = audit_record("tool", "proj", {}, result_size=1024)
        assert record["result_size"] == 1024
