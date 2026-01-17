SHELL := /bin/bash
PYTHONPATH := $(PWD)/shared/src:$(PWD)/backend/src:$(PWD)/client/src
export PYTHONPATH

.PHONY: help setup setup-backend setup-client backend client test lint clean

help:
	@echo "KeyMuse Development Commands"
	@echo ""
	@echo "  make setup          - Set up both backend and client virtualenvs"
	@echo "  make setup-backend  - Set up backend virtualenv only"
	@echo "  make setup-client   - Set up client virtualenv only"
	@echo "  make backend        - Run the backend server"
	@echo "  make client         - Run the client app"
	@echo "  make test           - Run all tests"
	@echo "  make clean          - Remove __pycache__ directories"

setup: setup-backend setup-client

setup-backend:
	@echo "Setting up backend virtualenv..."
	-pyenv virtualenv 3.12.3 keymuse-backend 2>/dev/null || true
	cd backend && pyenv local keymuse-backend
	bash -c "source $$(pyenv root)/versions/keymuse-backend/bin/activate && pip install -r backend/requirements.txt"
	@echo "Backend setup complete."

setup-client:
	@echo "Setting up client virtualenv..."
	-pyenv virtualenv 3.12.3 keymuse-client 2>/dev/null || true
	cd client && pyenv local keymuse-client
	bash -c "source $$(pyenv root)/versions/keymuse-client/bin/activate && pip install -r client/requirements.txt"
	@echo "Client setup complete."

backend:
	@echo "Starting backend server..."
	@bash -c "source $$(pyenv root)/versions/keymuse-backend/bin/activate && python -m keymuse_backend.server"

client:
	@echo "Starting client app..."
	@bash -c "source $$(pyenv root)/versions/keymuse-client/bin/activate && python -m keymuse_client.app"

test:
	pytest backend/tests client/tests -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned."
