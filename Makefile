.PHONY: install test lint format clean

VENV = .venv
PYTHON = $(VENV)/bin/python
UV = uv

install:
	$(UV) venv $(VENV)
	$(UV) pip install -e ../djust --python $(PYTHON)
	$(UV) pip install -e ".[dev,redis,postgres]" --python $(PYTHON)

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
