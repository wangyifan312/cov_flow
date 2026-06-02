# EDA Tool Adapters

Abstract adapter interface and mock implementations for EDA tool integration.

## Architecture

- __init__.py — Adapter registry and factory
- base.py — EDAAdapter abstract base class
- mock_verdi.py — Mock Verdi adapter (stub data)
- mock_vcs.py — Mock VCS adapter (stub data)

## Current Status

**Phase 4**: Mock adapters only. No real EDA tool integration.

All mock adapters:
- Return structured dict responses
- Include "mode": "mock" in every response
- Never call real EDA tool APIs (Verdi, VCS, KDB, NPI, VPI, FSDB)
- Implement the full EDAAdapter interface

## Adapter Interface

All adapters must implement:

- name (property): Adapter identifier string
- capabilities (property): List of supported feature strings
- check_availability(): Check tool availability, returns dict with mode
- open_waveform(path): Open FSDB/VCD waveform, returns dict with mode
- query_signal(path, time_range): Query signal values, returns dict with mode

## Usage

    from lib.eda_adapters import get_adapter, list_adapters

    # List available adapters
    for a in list_adapters():
        print(f"{a['name']}: {a['capabilities']}")

    # Get a specific adapter
    verdi = get_adapter("verdi_mock")
    result = verdi.check_availability()
    assert result["mode"] == "mock"

## Phase 5+ (Out of Scope)

Real adapters would:
- Connect to Verdi for waveform viewing and signal queries
- Connect to VCS for design compilation and simulation
- Read FSDB files for waveform analysis
- Use KDB/NPI/VPI for design database access

**All real EDA integration requires explicit approval before implementation.**
