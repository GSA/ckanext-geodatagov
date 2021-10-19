CKAN_VERSION ?= 2.8
COMPOSE_FILE ?= docker-compose.yml
COMPOSE_LEGACY_FILE ?= docker-compose.legacy.yml

build: ## Build the docker containers
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) build

lint: ## Lint the code
	@# our linting only runs with python3
	@# TODO use CKAN_VERSION make variable once 2.8 is deprecated
	CKAN_VERSION=2.9 docker-compose -f docker-compose.yml run --rm app flake8 . --count --show-source --statistics --exclude ckan,nose

clean: ## Clean workspace and containers
	find . -name *.pyc -delete
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) down -v --remove-orphan

test: ## Run tests in a new container
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) run --rm app ./test.sh

java: ## Test java transformation command (java + saxon installed)
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) run --rm app bash -c "java net.sf.saxon.Transform -s:/app/ckanext/geodatagov/tests/data-samples/waf-fgdc/fgdc-csdgm_sample.xml -xsl:/app/ckanext/geodatagov/harvesters/fgdcrse2iso19115-2.xslt"

test-legacy: ## Run legacy nose tests in an existing container
	@# TODO wait for CKAN to be up; use docker-compose run instead
	docker-compose -f docker-compose.legacy.yml exec ckan /bin/bash -c "nosetests --ckan --with-pylons=src/ckan/test-catalog-next.ini src_extensions/geodatagov/ckanext/geodatagov/tests/nose"

up: ## Start the containers
ifeq ($(CKAN_VERSION), 2.8)
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_LEGACY_FILE) up
else
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) up
endif


.DEFAULT_GOAL := help
.PHONY: build clean help lint test test-legacy up

# Output documentation for top-level targets
# Thanks to https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
