.PHONY: dev backend frontend install test lint

# Run everything
dev:
	@echo "Starting backend and frontend..."
	@make backend &
	@make frontend

# Backend
backend:
	cd . && uvicorn app.main:app --reload --port 8000

# Frontend
frontend:
	cd frontend && npm run dev

# Install all dependencies
install:
	pip install -r requirements.txt
	cd frontend && npm install

# Run tests
test:
	pytest tests/ -v

# Lint
lint:
	ruff check app/ --fix
	ruff format app/

# Docker
up:
	docker-compose up --build

down:
	docker-compose down

# Database migrations
migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"
