CKAN_VERSION ?= 2.9.7
COMPOSE_FILE ?= docker-compose.yml

build: ## Build the docker containers
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) build
debug:
	CKAN_VERSION=$(CKAN_VERSION) docker-compose run --service-ports app

lint: ## Lint the code
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f docker-compose.yml run --rm app flake8 /srv/app/ckanext/ --count --max-line-length=127 --show-source --statistics --exclude ckan

clean: ## Clean workspace and containers
	find . -name *.pyc -delete
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans

test: ## Run tests in a new container
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) run --rm app /srv/app/test.sh

java-test: ## Test java transformation command (java + saxon installed)
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) run --rm app bash -c "java net.sf.saxon.Transform -s:/app/ckanext/geodatagov/tests/data-samples/waf-fgdc/fgdc-csdgm_sample.xml -xsl:/app/ckanext/geodatagov/harvesters/fgdcrse2iso19115-2.xslt"

up: ## Start the containers
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) up

ci: ## Start the containers in the background
	CKAN_VERSION=$(CKAN_VERSION) docker-compose -f $(COMPOSE_FILE) up -d

.DEFAULT_GOAL := help
.PHONY: build clean help lint test up

# Output documentation for top-level targets
# Thanks to https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
