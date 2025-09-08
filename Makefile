.PHONY: api ui test fmt typecheck docker-build docker-up docker-down docker-dev-up docker-dev-down docker-prod-build docker-prod-up docker-prod-down docker-prod-deploy

api:
	uv run uvicorn api.main:app --reload --host $${APP_HOST:-0.0.0.0} --port $${APP_PORT:-8000}
ui:
	uv run streamlit run ui/main.py
test:
	uv run pytest -q

fmt:
	uv run python -m pip install ruff black >/dev/null 2>&1 || true
	ruff check --fix .
	black .

typecheck:
	uv run python -m pip install pyright >/dev/null 2>&1 || true
	pyright

# Docker 명령어들
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-dev-up:
	docker-compose -f docker-compose.dev.yml up -d

docker-dev-down:
	docker-compose -f docker-compose.dev.yml down

docker-logs:
	docker-compose logs -f

docker-dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# 운영 환경 Docker 명령어들
docker-prod-build:
	docker-compose -f docker-compose.prod.yml build

docker-prod-up:
	docker-compose -f docker-compose.prod.yml up -d

docker-prod-down:
	docker-compose -f docker-compose.prod.yml down

docker-prod-deploy:
	./scripts/deploy.sh deploy

docker-prod-stop:
	./scripts/deploy.sh stop

docker-prod-restart:
	./scripts/deploy.sh restart

docker-prod-logs:
	./scripts/deploy.sh logs

docker-prod-status:
	./scripts/deploy.sh status

docker-prod-clean:
	./scripts/deploy.sh clean
