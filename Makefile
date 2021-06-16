CKAN_VERSION ?= 2.8
COMPOSE_FILE ?= docker-compose.yml

build: ## Build the docker containers
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) build

lint: ## Lint the code
	@# our linting only runs with python3
	@# TODO use CKAN_VERSION make variable once 2.8 is deprecated
	CKAN_VERSION=2.9 docker-compose -f docker-compose.new.yml run --rm app flake8 . --count --show-source --statistics --exclude ckan

clean: ## Clean workspace and containers
	find . -name *.pyc -delete
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) down -v --remove-orphan

test: ## Run tests in a new container
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) run --rm ckan /bin/bash -c "nosetests --ckan --with-pylons=src/ckan/test-catalog-next.ini src_extensions/geodatagov/"

test-legacy: ## Run legacy nose tests in an existing container
	@# TODO wait for CKAN to be up; use docker-compose run instead
	docker-compose exec ckan /bin/bash -c "nosetests --ckan --with-pylons=src/ckan/test-catalog-next.ini src_extensions/datajson/ckanext/datajson/tests/nose"

lint-all:
	docker-compose exec -T ckan \
		bash -c "cd $(CKAN_HOME)/src && \
		 		 pip install pip==20.3.3  && \
				 pip install flake8 && \
				 flake8 . --count --select=E9 --show-source --statistics"

up: ## Start the containers
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) up


.DEFAULT_GOAL := help
.PHONY: build clean help lint test test-legacy up

# Output documentation for top-level targets
# Thanks to https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
