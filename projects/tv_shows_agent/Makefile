.PHONY: help build up down fmt

COMPOSE_CMD := podman compose

build:
	$(COMPOSE_CMD) build --no-cache

up:
	$(COMPOSE_CMD) up

down:
	$(COMPOSE_CMD) down

fmt:
	ruff format src
