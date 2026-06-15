"""EDA tool adapter registry and factory.

Provides a registry for EDA tool adapters and a factory method to
retrieve adapters by name. All adapters implement the EDAAdapter interface.

Usage:
    from lib.eda_adapters import get_adapter, list_adapters

    adapter = get_adapter("verdi_stub")
    adapter.check_availability()
"""

from __future__ import annotations

from typing import Any

from lib.eda_adapters.base import EDAAdapter
from lib.eda_adapters.stub_vcs import StubVCSAdapter
from lib.eda_adapters.stub_verdi import StubVerdiAdapter

__all__ = [
    "EDAAdapter",
    "StubVerdiAdapter",
    "StubVCSAdapter",
    "get_adapter",
    "list_adapters",
]

# Built-in adapter registry
_ADAPTERS: dict[str, type[EDAAdapter]] = {
    "verdi_stub": StubVerdiAdapter,
    "vcs_stub": StubVCSAdapter,
}


def get_adapter(name: str) -> EDAAdapter:
    """Get an adapter instance by name.

    Args:
        name: Adapter name (e.g. 'verdi_stub', 'vcs_stub').

    Returns:
        An instance of the requested adapter.

    Raises:
        KeyError: If the adapter name is not registered.
    """
    cls = _ADAPTERS.get(name)
    if cls is None:
        available = ", ".join(sorted(_ADAPTERS.keys()))
        raise KeyError(
            f"Unknown adapter: '{name}'. Available adapters: {available}"
        )
    return cls()


def list_adapters() -> list[dict[str, Any]]:
    """List all registered adapters with their capabilities."""
    result = []
    for name, cls in sorted(_ADAPTERS.items()):
        instance = cls()
        result.append({
            "name": instance.name,
            "capabilities": instance.capabilities,
        })
    return result
