# MacBook Smart Organizer

This repository contains a Python-based file and folder organizer designed for macOS (it also works on Linux and Windows). With a single command it analyses the files in a target directory, designs a clean folder structure based on the content it discovers, and then safely rearranges everything for you.

## Features

* **Automatic structure design** – Detects file types, creation dates, and text content to infer the best destination folder for each file.
* **Multi-layer heuristics** – Combines extension analysis, MIME detection, and content keyword scanning to achieve smart placements.
* **Duplicate detection** – Hash-based duplicate detection prevents storing the same file twice.
* **Dry-run mode** – Preview the plan before moving a single file.
* **Undo-friendly** – Moves files using the built-in `shutil.move`, so `Cmd + Z` in Finder or `mv` in the shell can revert changes if needed.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 organizer.py --help
```

If you prefer module-style invocation while inside the repository (or an editable install), you can run:

```bash
python3 -m mac_organizer --help
```

Or install the tool as a package and use the bundled command from anywhere on your Mac:

```bash
python3 -m pip install -e .
mac-organizer --help
```

To organize your downloads folder in-place:

```bash
python3 organizer.py ~/Downloads --apply
```

With the console script installed you can also run:

```bash
mac-organizer ~/Downloads --apply
```

Or, if you keep a virtual environment active and want to rely on the module runner instead of the console script:

```bash
python3 -m mac_organizer ~/Downloads --apply
```

To preview what would happen without actually moving files:

```bash
python3 organizer.py ~/Downloads --dry-run
```

## How it works

1. **Data collection** – Builds a profile for every file using metadata, MIME type, file name patterns, and (for readable text files) a keyword frequency analysis.
2. **Category inference** – Scores each file against a set of predefined categories (Work, Personal, Finance, Media, Archives, Source Code, etc.).
3. **Structure planner** – Generates an `Organized` folder tree rooted in the target directory and maps every file to an optimal destination.
4. **Execution engine** – Applies the plan by moving files. Duplicate hashes are logged and skipped by default.

## Disclaimer

Run the tool on a copy or with `--dry-run` the first time to ensure it matches your expectations.

## Troubleshooting

* **"can't open file 'organizer.py'"** – Make sure you are inside the project directory before invoking Python:
  ```bash
  pwd            # Should print the path to the cloned repository
  ls organizer.py
  ```
  If the file is not listed, `cd` into the repository folder or provide the absolute path when running `python3`.
  Alternatively install the project with `python3 -m pip install -e .` and run it via `mac-organizer ...` from any folder.
* **"Target directory does not exist"** – Supply a folder path that already exists and that you can read/write.
* **Unexpected character/encoding issues** – Theme detection reads text files as UTF-8. Convert files with other encodings if keywords are not being detected.
