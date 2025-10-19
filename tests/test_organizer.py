import json
import sys
from pathlib import Path

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
            )
        ],
    )
    payload = json.loads(plan.to_json())
    assert payload["root"] == str(tmp_path)
    assert payload["files"][0]["source"].endswith("a.txt")
