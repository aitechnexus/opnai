import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import mac_organizer.gui as gui


def test_ensure_tk_missing_module(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: SimpleNamespace())

    def fake_import(name, package=None):
        raise ModuleNotFoundError("No module named '_tkinter'", name="_tkinter")

    monkeypatch.setattr(importlib, "import_module", fake_import)

    monkeypatch.setattr(gui, "tk", None)
    monkeypatch.setattr(gui, "ttk", None)
    monkeypatch.setattr(gui, "filedialog", None)
    monkeypatch.setattr(gui, "messagebox", None)

    with pytest.raises(RuntimeError) as excinfo:
        gui._ensure_tk()

    assert "Tkinter is not available" in str(excinfo.value)


def test_launch_returns_error_when_tk_missing(monkeypatch, capsys):
    def raise_runtime_error():
        raise RuntimeError("no tk")

    monkeypatch.setattr(gui, "_ensure_tk", raise_runtime_error)
    result = gui.launch()
    captured = capsys.readouterr()
    assert result == 1
    assert "no tk" in captured.err
