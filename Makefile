PYTHON = python3
VENV   = .venv
BINARY_NAME = nexxtporter
DIST_DIR = dist
JOBS = $(shell nproc)

# Cross-platform venv binary paths
ifeq ($(OS),Windows_NT)
	VENV_PYTHON = $(VENV)/Scripts/python
	VENV_PIP    = $(VENV)/Scripts/pip
	BINARY_EXT  = .exe
	STRIP_CMD   = @echo "Skipping strip on Windows"
else
	VENV_PYTHON = $(VENV)/bin/python
	VENV_PIP    = $(VENV)/bin/pip
	BINARY_EXT  =
	STRIP_CMD   = strip --strip-all
endif

.PHONY: all install test coverage run clean dist

all: install

## Create virtual environment and install dependencies
install: $(VENV_PYTHON)

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt

## Run all unit tests
test: install
	$(VENV_PYTHON) -m pytest tests/ -v

## Run tests with coverage report
coverage: install
	$(VENV_PYTHON) -m pytest tests/ -v --cov=nexxtporter --cov-report=term-missing

## Run nexxtporter with config.json
run: install
	$(VENV_PYTHON) main.py config.json

## Build optimized distribution binary (production-ready)
dist: install
	@echo "Building optimized distribution binary..."
	@mkdir -p $(DIST_DIR)
	$(VENV_PYTHON) -m nuitka \
		--standalone \
		--onefile \
		--assume-yes-for-downloads \
		--output-dir=$(DIST_DIR) \
		--output-filename=$(BINARY_NAME)$(BINARY_EXT) \
		--remove-output \
		--warn-implicit-exceptions \
		--warn-unusual-code \
		--prefer-source-code \
		--python-flag=no_docstrings \
		--python-flag=no_asserts \
		--python-flag=-OO \
		--lto=yes \
		--jobs=$(JOBS) \
		--deployment \
		main.py
	@echo "Stripping debug symbols..."
	$(STRIP_CMD) $(DIST_DIR)/$(BINARY_NAME)$(BINARY_EXT)
	@echo ""
	@echo "Distribution binary ready: $(DIST_DIR)/$(BINARY_NAME)$(BINARY_EXT)"
	@ls -lh $(DIST_DIR)/$(BINARY_NAME)$(BINARY_EXT)
	@echo ""
	@echo "You can now distribute this as a standalone CLI tool"

## Remove build artifacts and virtual environment
clean:
	rm -rf $(VENV) .pytest_cache .coverage $(DIST_DIR)
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*.build' -exec rm -rf {} +
	find . -type d -name '*.dist' -exec rm -rf {} +
	find . -type d -name '*.onefile-build' -exec rm -rf {} +
