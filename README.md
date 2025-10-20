# MacBook Smart Organizer

This repository contains a Python-based file and folder organizer designed for macOS (it also works on Linux and Windows). With a single command it analyses the files in a target directory, designs a clean folder structure based on the content it discovers, and then safely rearranges everything for you.

## Features

* **Automatic structure design** – Detects file types, creation dates, and text content to infer the best destination folder for each file.
* **Multi-layer heuristics** – Combines extension analysis, MIME detection, and content keyword scanning to achieve smart placements.
* **Duplicate control** – Hash-based detection can either skip or automatically relocate duplicate files.
* **Dry-run mode** – Preview the plan before moving a single file.
* **Undo-friendly** – Moves files using the built-in `shutil.move`, so `Cmd + Z` in Finder or `mv` in the shell can revert changes if needed.
* **Safety guardrails** – Refuses to operate on macOS system directories and automatically skips hidden or critical folders (for example `Library`, `Applications`, `.ssh`) when you target your home directory.

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

Enable duplicate relocation at the same time to send redundant files into `Organized/Duplicates`:

```bash
python3 organizer.py ~/Downloads --apply --remove-duplicates
```

With the console script installed you can also run:

```bash
mac-organizer ~/Downloads --apply
```

Add `--remove-duplicates` to that command as well if you want duplicates moved automatically.

Or, if you keep a virtual environment active and want to rely on the module runner instead of the console script:

```bash
python3 -m mac_organizer ~/Downloads --apply
```

To preview what would happen without actually moving files:

```bash
python3 organizer.py ~/Downloads --dry-run
```

### Optional: Makefile shortcuts

To avoid retyping the common setup and execution commands, the repository now
ships with a simple `Makefile`. Run `make` with no arguments to see every
available shortcut. A few helpful examples:

```bash
# create .venv/ if it does not exist yet
make venv

# install the project in editable mode
make install

# organize a directory; provide the target path via the TARGET variable
make run TARGET=~/Downloads ARGS=--dry-run

# launch the GUI (accepts optional ARGS like "--plan")
make gui

# execute the test-suite
make test

# remove the virtual environment when you are done
make clean
```

## Graphical interface

Prefer point-and-click? Install the project (editable installs work great) and launch the Tkinter interface:

```bash
python3 -m pip install -e .
mac-organizer-gui
```

You can also run it directly via the module entry point while developing:

```bash
python3 -m mac_organizer.gui
```

Pick the folder you want to organize, choose whether to apply changes, and decide if duplicates should be relocated—all without leaving the GUI. The interface mirrors the CLI safety guardrails, so it will not touch critical system folders even when launched from your home directory.

## How it works

1. **Data collection** – Builds a profile for every file using metadata, MIME type, file name patterns, and (for readable text files) a keyword frequency analysis.
2. **Category inference** – Scores each file against a set of predefined categories (Work, Personal, Finance, Media, Archives, Source Code, etc.).
3. **Structure planner** – Generates an `Organized` folder tree rooted in the target directory and maps every file to an optimal destination.
4. **Execution engine** – Applies the plan by moving files. Duplicate hashes are logged and either skipped or moved into `Organized/Duplicates` when you enable duplicate relocation.

## Disclaimer

Run the tool on a copy or with `--dry-run` the first time to ensure it matches your expectations.

The organizer intentionally refuses to run against critical macOS directories such as `/`, `/System`, or `/Applications`. When you point it at your home directory it automatically excludes hidden folders and sensitive locations like `~/Library` and `~/.ssh`, so apps, system files, and other critical data remain untouched.

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
* **"Tkinter is not available"** – Install the `tk`/`tkinter` package for your Python installation (on macOS via `brew install python-tk` or the official Python installer) before launching the GUI.
