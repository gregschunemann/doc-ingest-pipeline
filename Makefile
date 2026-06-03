# doc-ingest-pipeline Makefile
# All targets shell out to Poetry so they work identically on macOS, Linux,
# and Windows (PowerShell / WSL / Git Bash). On Windows native PowerShell
# without `make` installed, run the body of each target directly.

.PHONY: help install precommit lint format test test-cov host-start bicep-build bicep-lint bicep-whatif clean

help:                ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:             ## Install runtime + dev deps and pre-commit hooks
	poetry install
	poetry run pre-commit install

precommit:           ## Run pre-commit hooks across the whole repo
	poetry run pre-commit run --all-files

lint:                ## Lint (black --check + flake8); fails CI on any diff
	poetry run black --check src tests
	poetry run flake8 src tests

format:              ## Apply black formatting in place
	poetry run black src tests

test:                ## Run the pytest suite
	poetry run pytest -q

test-cov:            ## Run pytest with coverage report
	poetry run pytest -q --cov=src --cov-report=term-missing --cov-report=html

host-start:          ## Start Azure Functions runtime locally
	cd src/functions && func host start

bicep-build:         ## Compile infra/main.bicep to ARM JSON
	az bicep build --file infra/main.bicep

bicep-lint:          ## Lint infra/main.bicep with strict ruleset
	az bicep lint --file infra/main.bicep

bicep-whatif:        ## Preview deployment changes (requires Azure login)
	az deployment sub what-if --location swedencentral \
	  --template-file infra/main.bicep \
	  --parameters infra/main.parameters.json \
	  --parameters environmentName=doc-ingest-dev \
	  principalId=$$(az ad signed-in-user show --query id -o tsv)

clean:               ## Remove build / cache artifacts
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
