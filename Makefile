.PHONY: help install dev test lint format clean run-main run-api run-fastapi deploy-setup health-check

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Development setup
install: ## Install dependencies
	pip install -r requirements.txt
	pip install black flake8 isort pre-commit

dev-install: install ## Install development dependencies
	@echo "Installing development tools..."
	pip install black flake8 isort pre-commit pytest
	pre-commit install || echo "pre-commit not configured yet"

# Code quality
lint: ## Run linting checks
	@echo "Running flake8..."
	flake8 --max-line-length=100 --extend-ignore=E203,W503 *.py
	@echo "Running import sorting check..."
	isort --check-only --diff *.py

format: ## Format code
	@echo "Formatting code with black..."
	black --line-length=100 *.py
	@echo "Sorting imports..."
	isort *.py

# Testing
test: ## Run tests
	@echo "Running basic import tests..."
	python -c "import main; print('✓ main.py')"
	python -c "import api; print('✓ api.py')"
	python -c "import at; print('✓ at.py')"
	python -c "import bot; print('✓ bot.py')"
	python -c "import test; print('✓ test.py')"
	@echo "All modules imported successfully!"

health-check: ## Run health checks on all services
	@echo "Checking service health..."
	python scripts/health_check.py

# Running services
run-main: ## Run main Flask app
	@echo "Starting main Flask app on port 5000..."
	python main.py

run-api: ## Run API Flask app
	@echo "Starting API Flask app on port 5001..."
	FLASK_APP=api.py flask run --port=5001

run-fastapi: ## Run FastAPI app
	@echo "Starting FastAPI app on port 8000..."
	uvicorn at:app --reload --host 0.0.0.0 --port 8000

run-bot: ## Run bot Flask app
	@echo "Starting bot Flask app on port 5002..."
	FLASK_APP=bot.py flask run --port=5002

# Deployment
deploy-heroku: ## Deploy to Heroku
	@echo "Deploying to Heroku..."
	git push heroku main

deploy-render: ## Show Render deployment info
	@echo "Render deployment configured in render.yaml"
	@echo "Connect your GitHub repo to Render dashboard"

deploy-vercel: ## Deploy to Vercel
	@echo "Deploying to Vercel..."
	vercel --prod

# Utilities
clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete
	find . -name "*.cache" -delete
	rm -f attendance_cache.json

setup: ## Complete project setup
	@echo "Setting up LNCT Attendance System..."
	make clean
	make dev-install
	make format
	make test
	@echo "✓ Setup complete! Use 'make help' to see available commands."

# CI/CD helpers
ci-test: ## Run CI tests
	make lint
	make test

quick-start: ## Quick start development server
	@echo "Choose a service to run:"
	@echo "1. Main Flask App (port 5000)"
	@echo "2. API Flask App (port 5001)" 
	@echo "3. FastAPI App (port 8000)"
	@echo "4. Bot Flask App (port 5002)"
	@read -p "Enter choice (1-4): " choice; \
	case $$choice in \
		1) make run-main ;; \
		2) make run-api ;; \
		3) make run-fastapi ;; \
		4) make run-bot ;; \
		*) echo "Invalid choice" ;; \
	esac