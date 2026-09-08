"""Tests enforcing the hard Live/Historical data-path separation.

Static source-text checks (not just behavioral checks) so a future edit
that quietly wires one path into the other is caught even if it doesn't
happen to break another test's specific scenario.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import hedgecanvas.historical as historical_pkg
import hedgecanvas.live as live_pkg


def _module_source_files(package) -> list[Path]:
    package_dir = Path(package.__file__).parent
    return sorted(package_dir.glob("*.py"))


def test_live_package_does_not_reference_historical() -> None:
    for path in _module_source_files(live_pkg):
        text = path.read_text()
        assert "hedgecanvas.historical" not in text, f"{path} references hedgecanvas.historical"
        assert "historical" not in text.lower() or path.name == "__init__.py", (
            f"{path} appears to reference 'historical'"
        )


def test_historical_package_does_not_reference_live_client() -> None:
    for path in _module_source_files(historical_pkg):
        text = path.read_text()
        assert "hedgecanvas.live" not in text, f"{path} references hedgecanvas.live"
        assert "DeribitClient" not in text, f"{path} references DeribitClient"
        assert "httpx" not in text, f"{path} references httpx (network dependency)"


def test_historical_loader_module_has_no_deribit_import() -> None:
    loader_source = Path(importlib.import_module("hedgecanvas.historical.loader").__file__).read_text()
    assert "deribit" not in loader_source.lower()
    assert "httpx" not in loader_source


def test_live_designer_can_operate_when_historical_files_absent(tmp_path: Path) -> None:
    # The live adapter's public surface takes no historical-directory
    # dependency at all -- importing and constructing it never touches the
    # historical/ package or filesystem location.
    from hedgecanvas.live import DeribitClient

    client = DeribitClient()
    assert client is not None
    client.close()


def test_historical_evidence_offline_logic_requires_no_network(tmp_path: Path) -> None:
    from hedgecanvas.historical import load_historical_evidence

    # No client, no httpx, no network fixture of any kind is passed in or
    # constructed -- loading is pure filesystem + pandas.
    evidence = load_historical_evidence(tmp_path)
    assert evidence.directory == tmp_path
