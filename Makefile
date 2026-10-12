.PHONY: build up down restart logs test test-backend test-frontend seed eval clean

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d

logs:
	docker compose logs -f

test: test-backend test-frontend

test-backend:
	pytest backend/tests/ -v

test-frontend:
	cd frontend && npm test

seed:
	python seed/seed_data.py

eval:
	python eval/evaluate.py

e2e:
	python tests/e2e_scenario.py

clean:
	docker compose down -v
	rm -rf .pytest_cache frontend/dist
