.PHONY: help build up down logs clean install-backend install-frontend dev-backend dev-frontend

help:
	@echo "Calibre Web Clone - Makefile commands"
	@echo ""
	@echo "Docker commands:"
	@echo "  make build         - Build Docker images"
	@echo "  make up            - Start all services"
	@echo "  make down          - Stop all services"
	@echo "  make logs          - View logs from all services"
	@echo "  make clean         - Remove all containers and volumes"
	@echo ""
	@echo "Development commands:"
	@echo "  make install-backend   - Install backend dependencies"
	@echo "  make install-frontend  - Install frontend dependencies"
	@echo "  make dev-backend       - Run backend in development mode"
	@echo "  make dev-frontend      - Run frontend in development mode"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d
	@echo ""
	@echo "Services started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f

# Development commands
install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev
