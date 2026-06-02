"""Mock Verdi adapter — returns stub data, never calls real Verdi.

This adapter is for architecture scaffolding only. A real Verdi adapter
(Phase 5+) would integrate with the Verdi API to open waveforms, query
signals, and view schematics.
"""

from __future__ import annotations

from typing import Any

from lib.eda_adapters.base import EDAAdapter


class MockVerdiAdapter(EDAAdapter):
    """Mock Verdi adapter — returns stub data, never calls real Verdi."""

    @property
    def name(self) -> str:
        return "verdi_mock"

    @property
    def capabilities(self) -> list[str]:
        return ["waveform_view", "signal_query", "schematic_view"]

    def check_availability(self) -> dict[str, Any]:
        return {
            "available": True,
            "mode": "mock",
            "version": None,
            "note": "Mock Verdi adapter — no real Verdi connection.",
        }

    def open_waveform(self, path: str) -> dict[str, Any]:
        return {
            "status": "mock",
            "mode": "mock",
            "path": path,
            "signals": [
                {"name": "clk", "type": "wire", "width": 1},
                {"name": "rst_n", "type": "wire", "width": 1},
                {"name": "data_bus", "type": "wire", "width": 32},
            ],
            "note": "Stub waveform data — no real FSDB/VCD loaded.",
        }

    def query_signal(
        self, signal_path: str, time_range: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "mock",
            "mode": "mock",
            "signal_path": signal_path,
            "time_range": time_range,
            "values": [
                {"time_ns": 0, "value": "0"},
                {"time_ns": 100, "value": "1"},
                {"time_ns": 200, "value": "0"},
            ],
            "note": "Stub signal data — no real waveform queried.",
        }
