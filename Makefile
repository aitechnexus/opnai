VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
ORGANIZER := organizer.py

.DEFAULT_GOAL := help

.PHONY: help venv install run gui test clean

help:
@echo "Available targets:"
@echo "  make venv       - create a virtual environment in $(VENV)"
@echo "  make install    - install the project in editable mode"
@echo "  make run        - run the organizer with TARGET and ARGS variables"
@echo "                   (example: make run TARGET=~/Downloads ARGS=--dry-run)"
@echo "  make gui        - launch the Tkinter GUI"
@echo "  make test       - execute pytest using the virtual environment"
@echo "  make clean      - remove the virtual environment"

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
