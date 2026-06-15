"""Stub VCS adapter — returns stub data, never calls real VCS.

This adapter is for architecture scaffolding only. A real VCS adapter
(Phase 5+) would integrate with VCS to compile designs, run simulations,
and generate coverage reports.
"""

from __future__ import annotations

from typing import Any

from lib.eda_adapters.base import EDAAdapter


class StubVCSAdapter(EDAAdapter):
    """Stub VCS adapter — returns stub data, never calls real VCS."""

    @property
    def name(self) -> str:
        return "vcs_stub"

    @property
    def capabilities(self) -> list[str]:
        return ["compile", "simulate", "coverage_report"]

    def check_availability(self) -> dict[str, Any]:
        return {
            "available": True,
            "mode": "stub",
            "version": None,
            "note": "Stub VCS adapter — no real VCS connection.",
        }

    def open_waveform(self, path: str) -> dict[str, Any]:
        return {
            "status": "stub",
            "mode": "stub",
            "path": path,
            "signals": [],
            "note": "VCS adapter does not open waveforms directly.",
        }

    def query_signal(
        self, signal_path: str, time_range: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "stub",
            "mode": "stub",
            "signal_path": signal_path,
            "time_range": time_range,
            "values": [],
            "note": "VCS adapter does not query signals directly.",
        }

    def compile_design(self, filelist: str) -> dict[str, Any]:
        """Stub compile — returns stub result."""
        return {
            "status": "stub",
            "mode": "stub",
            "filelist": filelist,
            "errors": 0,
            "warnings": 0,
            "note": "Stub compile result — no real VCS compilation.",
        }

    def run_simulation(self, test: str, seed: int) -> dict[str, Any]:
        """Stub simulation run — returns stub result."""
        return {
            "status": "stub",
            "mode": "stub",
            "test": test,
            "seed": seed,
            "pass_count": 1,
            "fail_count": 0,
            "note": "Stub simulation result — no real VCS execution.",
        }
