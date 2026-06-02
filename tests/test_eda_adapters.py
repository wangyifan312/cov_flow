"""Tests for EDA adapter interface and mock implementations."""

import pytest

from lib.eda_adapters import (
    EDAAdapter,
    MockVCSAdapter,
    MockVerdiAdapter,
    get_adapter,
    list_adapters,
)


class TestEDAAdapterInterface:
    """Verify all adapters implement the EDAAdapter interface."""

    def test_mock_verdi_is_adapter(self) -> None:
        adapter = MockVerdiAdapter()
        assert isinstance(adapter, EDAAdapter)

    def test_mock_vcs_is_adapter(self) -> None:
        adapter = MockVCSAdapter()
        assert isinstance(adapter, EDAAdapter)

    def test_mock_verdi_has_name(self) -> None:
        adapter = MockVerdiAdapter()
        assert isinstance(adapter.name, str)
        assert adapter.name == "verdi_mock"

    def test_mock_vcs_has_name(self) -> None:
        adapter = MockVCSAdapter()
        assert isinstance(adapter.name, str)
        assert adapter.name == "vcs_mock"

    def test_mock_verdi_has_capabilities(self) -> None:
        adapter = MockVerdiAdapter()
        assert isinstance(adapter.capabilities, list)
        assert len(adapter.capabilities) > 0

    def test_mock_vcs_has_capabilities(self) -> None:
        adapter = MockVCSAdapter()
        assert isinstance(adapter.capabilities, list)
        assert len(adapter.capabilities) > 0


class TestMockVerdiAdapter:
    """Test MockVerdiAdapter behavior."""

    def test_check_availability_returns_mock_mode(self) -> None:
        adapter = MockVerdiAdapter()
        result = adapter.check_availability()
        assert isinstance(result, dict)
        assert result["mode"] == "mock"
        assert "available" in result
        assert result["available"] is True

    def test_open_waveform_returns_mock(self) -> None:
        adapter = MockVerdiAdapter()
        result = adapter.open_waveform("/path/to/test.fsdb")
        assert isinstance(result, dict)
        assert result["mode"] == "mock"
        assert result["status"] == "mock"
        assert result["path"] == "/path/to/test.fsdb"
        assert isinstance(result["signals"], list)

    def test_query_signal_returns_mock(self) -> None:
        adapter = MockVerdiAdapter()
        result = adapter.query_signal("top.dut.signal", (0, 1000))
        assert isinstance(result, dict)
        assert result["mode"] == "mock"
        assert result["status"] == "mock"
        assert result["signal_path"] == "top.dut.signal"
        assert result["time_range"] == (0, 1000)
        assert isinstance(result["values"], list)

    def test_capabilities_include_waveform(self) -> None:
        adapter = MockVerdiAdapter()
        assert "waveform_view" in adapter.capabilities
        assert "signal_query" in adapter.capabilities


class TestMockVCSAdapter:
    """Test MockVCSAdapter behavior."""

    def test_check_availability_returns_mock_mode(self) -> None:
        adapter = MockVCSAdapter()
        result = adapter.check_availability()
        assert isinstance(result, dict)
        assert result["mode"] == "mock"
        assert result["available"] is True

    def test_open_waveform_returns_mock(self) -> None:
        adapter = MockVCSAdapter()
        result = adapter.open_waveform("/path/to/test.fsdb")
        assert isinstance(result, dict)
        assert result["mode"] == "mock"

    def test_query_signal_returns_mock(self) -> None:
        adapter = MockVCSAdapter()
        result = adapter.query_signal("top.dut.signal")
        assert isinstance(result, dict)
        assert result["mode"] == "mock"

    def test_compile_design_returns_mock(self) -> None:
        adapter = MockVCSAdapter()
        result = adapter.compile_design("/path/to/filelist.f")
        assert isinstance(result, dict)
        assert result["mode"] == "mock"
        assert result["status"] == "mock"
        assert "errors" in result
        assert "warnings" in result

    def test_run_simulation_returns_mock(self) -> None:
        adapter = MockVCSAdapter()
        result = adapter.run_simulation("test_name", 12345)
        assert isinstance(result, dict)
        assert result["mode"] == "mock"
        assert result["test"] == "test_name"
        assert result["seed"] == 12345

    def test_capabilities_include_compile(self) -> None:
        adapter = MockVCSAdapter()
        assert "compile" in adapter.capabilities
        assert "simulate" in adapter.capabilities


class TestAdapterRegistry:
    """Test the adapter registry and factory."""

    def test_get_adapter_verdi(self) -> None:
        adapter = get_adapter("verdi_mock")
        assert isinstance(adapter, MockVerdiAdapter)
        assert adapter.name == "verdi_mock"

    def test_get_adapter_vcs(self) -> None:
        adapter = get_adapter("vcs_mock")
        assert isinstance(adapter, MockVCSAdapter)
        assert adapter.name == "vcs_mock"

    def test_get_adapter_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown adapter"):
            get_adapter("nonexistent_adapter")

    def test_list_adapters_returns_both(self) -> None:
        adapters = list_adapters()
        assert isinstance(adapters, list)
        assert len(adapters) >= 2
        names = [a["name"] for a in adapters]
        assert "verdi_mock" in names
        assert "vcs_mock" in names

    def test_list_adapters_has_capabilities(self) -> None:
        adapters = list_adapters()
        for adapter in adapters:
            assert "name" in adapter
            assert "capabilities" in adapter
            assert isinstance(adapter["capabilities"], list)
