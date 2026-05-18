.PHONY: install run migrate test superuser lint format seed clean

# Prefer project venv (Windows: Scripts\python.exe, Unix: bin/python)
ifeq ($(OS),Windows_NT)
    VENV_PY := venv/Scripts/python.exe
    VENV_PIP := venv/Scripts/pip.exe
else
    VENV_PY := venv/bin/python
    VENV_PIP := venv/bin/pip
endif

ifneq ($(wildcard $(VENV_PY)),)
    PYTHON := $(VENV_PY)
    PIP := $(VENV_PIP)
else
    PYTHON := python3
    PIP := pip3
endif

install:
	python -m venv venv
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) manage.py runserver

migrate:
	$(PYTHON) manage.py makemigrations
	$(PYTHON) manage.py migrate

test:
	$(PYTHON) manage.py test

superuser:
	$(PYTHON) manage.py createsuperuser

lint:
	ruff check .

format:
	ruff format .

seed:
	$(PYTHON) manage.py seed_data

clean:
	find . -type d -name __pycache__ -not -path "./venv/*" -exec rm -rf {} +
	find . -type f -name "*.pyc" -not -path "./venv/*" -delete
