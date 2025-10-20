import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import organizer


def test_module_package_exposes_main():
    from mac_organizer import main as package_main

    assert package_main is organizer.main


def test_module_runner_reuses_main_function():
    import mac_organizer.__main__ as module_main

    assert module_main.main is organizer.main


def test_wrapper_script_runs_core_main(monkeypatch):
    result = object()

    def fake_main(argv=None):
        return result

    monkeypatch.setattr(organizer, "_core", types.SimpleNamespace(main=fake_main))

    assert organizer._run() is result


def test_tokenize_basic():
    tokens = list(organizer._tokenize("Hello, World! 2024"))
    assert tokens == ["Hello", "World", "2024"]


def test_select_theme_prefers_high_score():
    profile = organizer.Counter({"invoice": 2, "tax": 1, "travel": 3})
    assert organizer.select_theme(profile) == "Finance"


def test_guess_category_uses_extension(tmp_path: Path):
    file_path = tmp_path / "photo.JPG"
    file_path.write_bytes(b"fake")
    category, theme = organizer.guess_category(file_path, None)
    assert category == "Images"
    assert theme is None


def test_text_profile_and_theme(tmp_path: Path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("Project proposal meeting minutes", encoding="utf-8")
    profile = organizer.text_profile(file_path, "text/plain")
    category, theme = organizer.guess_category(file_path, profile)
    assert category == "Documents/Work"
    assert theme == "Work"


def test_plan_report_json(tmp_path: Path):
    plan = organizer.PlanReport(
        root=tmp_path,
        files=[
            organizer.FilePlan(
                source=tmp_path / "a.txt",
                destination=tmp_path / "Organized/Documents/a.txt",
                category="Documents",
                theme=None,
                duplicate_of=None,
            )
        ],
    )
    payload = json.loads(plan.to_json())
    assert payload["root"] == str(tmp_path)
    assert payload["files"][0]["source"].endswith("a.txt")
    assert payload["files"][0]["duplicate_of"] is None


def test_home_directory_protection(tmp_path: Path, monkeypatch):
    target = tmp_path
    (target / "Library").mkdir()
    (target / "Library" / "prefs.plist").write_text("prefs", encoding="utf-8")
    (target / ".ssh").mkdir()
    (target / ".ssh" / "id_rsa").write_text("key", encoding="utf-8")
    docs = target / "Documents"
    docs.mkdir()
    safe_file = docs / "notes.txt"
    safe_file.write_text("meeting minutes", encoding="utf-8")

    monkeypatch.setattr(organizer.Path, "home", classmethod(lambda cls: target))
    org = organizer.Organizer(target, apply_changes=False, dry_run=True)
    plans = list(org._build_plan())
    sources = {plan.source for plan in plans}
    assert safe_file in sources
    assert target / "Library" / "prefs.plist" not in sources
    assert target / ".ssh" / "id_rsa" not in sources


def test_refuses_system_target(tmp_path: Path):
    org = organizer.Organizer(Path("/System"), apply_changes=False, dry_run=True)
    with pytest.raises(ValueError):
        org.run()


def test_refuses_nested_system_target():
    org = organizer.Organizer(Path("/System/Library"), apply_changes=False, dry_run=True)
    with pytest.raises(ValueError):
        org.run()


def test_allows_regular_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    sample = tmp_path / "note.txt"
    sample.write_text("hello", encoding="utf-8")

    org = organizer.Organizer(tmp_path, apply_changes=False, dry_run=True)
    org.run()

    captured = capsys.readouterr()
    assert "Scanning" in captured.out
    assert "Dry run only" in captured.out


def test_duplicate_removal_moves_to_duplicates(tmp_path: Path):
    original = tmp_path / "report.pdf"
    duplicate = tmp_path / "copy.pdf"
    original.write_bytes(b"sample")
    duplicate.write_bytes(b"sample")

    org = organizer.Organizer(
        tmp_path,
        apply_changes=True,
        dry_run=False,
        remove_duplicates=True,
    )

    plan = list(org._build_plan())
    duplicates = [item for item in plan if item.is_duplicate]
    assert len(duplicates) == 1
    assert duplicates[0].category == "Duplicates"
    assert duplicates[0].duplicate_of is not None

    org._apply(plan)

    duplicates_dir = tmp_path / "Organized" / "Duplicates"
    moved = list(duplicates_dir.glob("*.pdf"))
    assert moved, "Duplicate file should be moved into Organized/Duplicates"
    assert moved[0].read_bytes() == b"sample"
    organized_docs = tmp_path / "Organized" / "Documents"
    assert list(organized_docs.glob("*.pdf")), "One copy should remain in Organized/Documents"
