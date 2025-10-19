"""Smart file organizer for macOS and other Unix-like systems.

The tool analyses every file in a target directory, designs a content-aware
folder structure, and optionally rearranges the files into the new layout.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import mimetypes
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Tuple

TEXT_MIME_PREFIXES = {"text/", "application/json", "application/xml"}
DEFAULT_ROOT_NAME = "Organized"

KEYWORD_THEMES: Mapping[str, Tuple[str, ...]] = {
    "Finance": (
        "invoice",
        "receipt",
        "tax",
        "bank",
        "statement",
        "payment",
        "budget",
    ),
    "Work": (
        "meeting",
        "project",
        "sprint",
        "presentation",
        "minutes",
        "proposal",
        "brief",
    ),
    "Personal": (
        "travel",
        "family",
        "recipe",
        "health",
        "fitness",
        "shopping",
        "wishlist",
    ),
    "Education": (
        "assignment",
        "lecture",
        "course",
        "university",
        "study",
        "notes",
    ),
    "Legal": (
        "contract",
        "nda",
        "agreement",
        "license",
        "policy",
    ),
}

EXTENSION_MAP: Mapping[str, str] = {
    # Documents
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".ppt": "Documents",
    ".pptx": "Documents",
    ".xls": "Documents",
    ".xlsx": "Documents",
    ".txt": "Documents",
    ".md": "Documents",
    ".rtf": "Documents",
    # Media
    ".jpg": "Images",
    ".jpeg": "Images",
    ".png": "Images",
    ".gif": "Images",
    ".heic": "Images",
    ".mov": "Videos",
    ".mp4": "Videos",
    ".m4v": "Videos",
    ".mp3": "Audio",
    ".aac": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    # Archives
    ".zip": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".bz2": "Archives",
    ".7z": "Archives",
    # Code
    ".py": "Code",
    ".js": "Code",
    ".ts": "Code",
    ".java": "Code",
    ".swift": "Code",
    ".c": "Code",
    ".cpp": "Code",
    ".rb": "Code",
    ".go": "Code",
    ".rs": "Code",
}

DEFAULT_CATEGORY = "Others"


PROTECTED_DIR_NAMES = {
    "Applications",
    "Library",
    "System",
    "bin",
    "sbin",
    "usr",
    "etc",
    "var",
    "opt",
    "Volumes",
}


def walk_files(
    root: Path,
    *,
    protected_dir_names: Iterable[str] = (),
    skip_hidden: bool = False,
    exclude: Optional[Path] = None,
) -> Iterator[Path]:
    protected = {name for name in protected_dir_names}
    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        if exclude and (current_dir == exclude or exclude in current_dir.parents):
            dirnames[:] = []
            continue
        filtered_dirs = []
        for dirname in dirnames:
            if skip_hidden and dirname.startswith("."):
                continue
            if dirname in protected:
                continue
            filtered_dirs.append(dirname)
        dirnames[:] = filtered_dirs
        for name in filenames:
            if skip_hidden and name.startswith("."):
                continue
            yield current_dir / name


def guess_category(path: Path, text_profile: Optional[Counter[str]]) -> Tuple[str, Optional[str]]:
    ext = path.suffix.lower()
    category = EXTENSION_MAP.get(ext)

    if not category:
        mime, _ = mimetypes.guess_type(str(path))
        if mime:
            if mime.startswith("image/"):
                category = "Images"
            elif mime.startswith("video/"):
                category = "Videos"
            elif mime.startswith("audio/"):
                category = "Audio"
            elif mime in {"application/zip", "application/x-tar"}:
                category = "Archives"
            elif mime.startswith("text/"):
                category = "Documents"

    if not category:
        category = DEFAULT_CATEGORY

    theme = None
    if text_profile:
        theme = select_theme(text_profile)
        if theme:
            category = f"Documents/{theme}"

    if category == "Documents" and theme:
        category = f"Documents/{theme}"

    return category, theme


def select_theme(profile: Counter[str]) -> Optional[str]:
    best_theme = None
    best_score = 0
    for theme, keywords in KEYWORD_THEMES.items():
        score = sum(profile.get(keyword, 0) for keyword in keywords)
        if score > best_score:
            best_score = score
            best_theme = theme
    if best_score == 0:
        return None
    return best_theme


def text_profile(path: Path, mime: Optional[str]) -> Optional[Counter[str]]:
    if not mime:
        return None
    if not any(mime.startswith(prefix.rstrip("/")) for prefix in TEXT_MIME_PREFIXES):
        return None
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            content = handle.read(20_000)
    except (OSError, UnicodeError):
        return None
    tokens = [token.lower() for token in _tokenize(content)]
    return Counter(tokens)


def _tokenize(text: str) -> Iterable[str]:
    current = []
    for char in text:
        if char.isalnum():
            current.append(char)
        else:
            if current:
                yield "".join(current)
                current.clear()
    if current:
        yield "".join(current)


@dataclasses.dataclass
class FilePlan:
    source: Path
    destination: Path
    category: str
    theme: Optional[str]
    is_duplicate: bool = False


@dataclasses.dataclass
class PlanReport:
    root: Path
    files: List[FilePlan]

    def summary(self) -> Mapping[str, int]:
        counts: MutableMapping[str, int] = defaultdict(int)
        for plan in self.files:
            counts[plan.category] += 1
        return dict(sorted(counts.items(), key=lambda item: item[0]))

    def to_json(self) -> str:
        serializable = {
            "root": str(self.root),
            "files": [
                {
                    "source": str(plan.source),
                    "destination": str(plan.destination),
                    "category": plan.category,
                    "theme": plan.theme,
                    "duplicate": plan.is_duplicate,
                }
                for plan in self.files
            ],
        }
        return json.dumps(serializable, indent=2)


CRITICAL_TARGETS = {
    Path("/"),
    Path("/System"),
    Path("/Applications"),
    Path("/Library"),
    Path("/bin"),
    Path("/usr"),
    Path("/sbin"),
    Path("/etc"),
    Path("/var"),
}


class Organizer:
    def __init__(self, target: Path, apply_changes: bool, dry_run: bool, root_name: str = DEFAULT_ROOT_NAME) -> None:
        self.target = target.expanduser().resolve()
        self.apply_changes = apply_changes
        self.dry_run = dry_run
        self.organized_root = self.target / root_name
        self._protected_dirs = set(PROTECTED_DIR_NAMES)
        home = Path.home()
        if self.target == home:
            self._protected_dirs.update({"Applications", "Library", ".ssh", ".config"})
        self._skip_hidden = True

    def run(self) -> PlanReport:
        if not self.target.exists() or not self.target.is_dir():
            raise ValueError(f"Target {self.target} does not exist or is not a directory")
        if self._is_critical_target():
            raise ValueError(f"Refusing to organize critical system directory: {self.target}")

        print(f"Scanning {self.target} ...")
        plan = list(self._build_plan())
        report = PlanReport(self.organized_root, plan)
        self._print_summary(report)
        if self.apply_changes and not self.dry_run:
            self._apply(plan)
        else:
            print("Dry run only. Use --apply to move files.")
        return report

    def _build_plan(self) -> Iterator[FilePlan]:
        hash_index: Dict[str, Path] = {}
        for path in walk_files(
            self.target,
            protected_dir_names=self._protected_dirs,
            skip_hidden=self._skip_hidden,
            exclude=self.organized_root,
        ):
            if self.organized_root in path.parents:
                continue
            mime, _ = mimetypes.guess_type(str(path))
            profile = text_profile(path, mime)
            category, theme = guess_category(path, profile)
            destination = self._destination_for(path, category)
            file_hash = self._hash_file(path)
            is_duplicate = False
            if file_hash in hash_index:
                destination = hash_index[file_hash]
                is_duplicate = True
            else:
                hash_index[file_hash] = destination
            yield FilePlan(source=path, destination=destination, category=category, theme=theme, is_duplicate=is_duplicate)

    def _is_critical_target(self) -> bool:
        return any(self.target == path or path in self.target.parents for path in CRITICAL_TARGETS)

    def _destination_for(self, path: Path, category: str) -> Path:
        if category.startswith("Images"):
            return self._dated_destination(path, category)
        if category.startswith("Videos"):
            return self._dated_destination(path, category)
        if category.startswith("Audio"):
            return self._dated_destination(path, category)
        return self.organized_root / category / path.name

    def _dated_destination(self, path: Path, category: str) -> Path:
        try:
            stats = path.stat()
            created = datetime.fromtimestamp(stats.st_mtime)
        except OSError:
            created = datetime.now()
        year = created.strftime("%Y")
        month = created.strftime("%m")
        return self.organized_root / category / year / month / path.name

    def _apply(self, plan: Iterable[FilePlan]) -> None:
        print("Applying plan ...")
        for item in plan:
            if item.is_duplicate:
                print(f"Skipping duplicate: {item.source} -> {item.destination}")
                continue
            destination_dir = item.destination.parent
            destination_dir.mkdir(parents=True, exist_ok=True)
            print(f"Moving {item.source} -> {item.destination}")
            shutil.move(str(item.source), str(item.destination))
        print("Done.")

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError:
            return f"error:{path}"
        return digest.hexdigest()

    def _print_summary(self, report: PlanReport) -> None:
        print("\nSummary:")
        for category, count in report.summary().items():
            print(f"  {category}: {count}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Content-aware MacBook file organizer")
    parser.add_argument("target", type=Path, help="Target directory to organize")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the plan (move files). Without this flag the tool performs a dry run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force a dry run even if --apply is supplied.",
    )
    parser.add_argument(
        "--root-name",
        default=DEFAULT_ROOT_NAME,
        help="Name of the folder that will contain the reorganized structure.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the plan as JSON after the summary.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    organizer = Organizer(args.target, apply_changes=args.apply, dry_run=args.dry_run, root_name=args.root_name)
    try:
        report = organizer.run()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print("\nPlan (JSON):")
        print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
