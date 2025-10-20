VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
ORGANIZER := organizer.py

REMOTE ?= origin
MAIN ?= main
BRANCH ?=
TITLE ?=
BODY ?=
MSG ?=
FILES ?=
GH := $(shell command -v gh)

.DEFAULT_GOAL := help

.PHONY: help venv install run gui test clean git-prepare git-sync git-commit git-pr

help:
@echo "Available targets:"
@echo "  make venv       - create a virtual environment in $(VENV)"
@echo "  make install    - install the project in editable mode"
@echo "  make run        - run the organizer with TARGET and ARGS variables"
@echo "                   (example: make run TARGET=~/Downloads ARGS=--dry-run)"
@echo "  make gui        - launch the Tkinter GUI"
@echo "  make test       - execute pytest using the virtual environment"
@echo "  make clean      - remove the virtual environment"
@echo "  make git-prepare BRANCH=name - update $(MAIN) and create/reset BRANCH from it"
@echo "  make git-sync BRANCH=name    - rebase BRANCH onto $(REMOTE)/$(MAIN)"
@echo "  make git-commit MSG='...'    - stage FILES (defaults to all) and commit"
@echo "  make git-pr BRANCH=name      - push BRANCH and create a PR via gh if available"

$(PYTHON):
python3 -m venv $(VENV)

venv: $(PYTHON)

install: venv
$(PIP) install -e .

run: install
ifndef TARGET
$(error TARGET is required. Example: make run TARGET=~/Downloads ARGS=--dry-run)
endif
$(PYTHON) $(ORGANIZER) $(TARGET) $(ARGS)

gui: install
$(VENV)/bin/mac-organizer-gui $(ARGS)

test: install
$(PYTHON) -m pytest $(ARGS)

clean:
rm -rf $(VENV)

git-prepare:
ifndef BRANCH
$(error BRANCH is required. Example: make git-prepare BRANCH=feature/my-change)
endif
git fetch $(REMOTE)
git checkout $(MAIN)
git pull --ff-only $(REMOTE) $(MAIN)
git checkout -B $(BRANCH)

git-sync:
ifndef BRANCH
$(error BRANCH is required. Example: make git-sync BRANCH=feature/my-change)
endif
git fetch $(REMOTE)
git checkout $(BRANCH)
git rebase $(REMOTE)/$(MAIN)

git-commit:
ifndef MSG
$(error MSG is required. Example: make git-commit MSG="Add feature" [FILES="path1 path2"])
endif
ifeq ($(strip $(FILES)),)
git add -A
else
git add $(FILES)
endif
git commit -m "$(MSG)"

git-pr:
ifndef BRANCH
$(error BRANCH is required. Example: make git-pr BRANCH=feature/my-change TITLE="My change")
endif
git push --set-upstream $(REMOTE) $(BRANCH)
ifdef GH
gh pr create --base $(MAIN) --head $(BRANCH) $(if $(strip $(TITLE)),--title "$(TITLE)") $(if $(strip $(BODY)),--body "$(BODY)") || echo "Git push succeeded but gh pr create failed."
else
@echo "Git push succeeded. Install GitHub CLI (gh) to auto-create pull requests."
endif
