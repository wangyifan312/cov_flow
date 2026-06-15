"""Abstract base class for EDA tool adapters.

Defines the interface that all EDA tool adapters (Verdi, VCS, etc.) must
implement. Stub adapters return representative data; real adapters (Phase 5+)
will provide actual tool integration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EDAAdapter(ABC):
    """Abstract base class for EDA tool adapters.

    All methods return structured dicts for compatibility with the MCP
    envelope format. Stub implementations must include mode='stub' in
    their return values.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the adapter name (e.g. 'verdi_stub', 'vcs_stub')."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """Return the list of capabilities this adapter supports."""
        ...

    @abstractmethod
    def check_availability(self) -> dict[str, Any]:
        """Check if the EDA tool is available (license, path, etc.).

        Returns:
            Dict with keys: available (bool), mode ('stub' or 'real'),
            version (str or None), note (str).
        """
        ...

    @abstractmethod
    def open_waveform(self, path: str) -> dict[str, Any]:
        """Open a waveform file (FSDB/VCD).

        Args:
            path: Path to the waveform file.

        Returns:
            Dict with keys: status ('stub' or 'ok'), path (str),
            signals (list), mode (str).
        """
        ...

    @abstractmethod
    def query_signal(
        self, signal_path: str, time_range: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        """Query signal values from a waveform.

        Args:
            signal_path: Hierarchical signal path (e.g. 'tb_top.dut.signal').
            time_range: Optional (start_ns, end_ns) time window.

        Returns:
            Dict with keys: status, signal_path, values (list), mode (str).
        """
        ...
