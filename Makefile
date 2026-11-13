VERSION   := $(shell python3 -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
RELEASE   := releases/turath-catalog-$(VERSION)
WORKSPACE ?= ../library
PY        := .venv/bin/python
TC        := .venv/bin/turath-catalog

.PHONY: help venv check release charts sample bench zip clean

help:          ## this list
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

venv:          ## create .venv with the dev extras
	uv venv && uv pip install -e ".[dev]"

check:         ## lint + tests with coverage
	$(PY) -m ruff check src tests && $(PY) -m ruff format --check src tests
	$(PY) -m pytest --cov=turath_catalog --cov-report=term-missing

release:       ## build the release from WORKSPACE (a Warraq library workspace)
	rm -rf $(RELEASE)
	$(TC) build --warraq $(WORKSPACE) --out $(RELEASE) \
	  --include hf/README.md:README.md --include LICENSE-DATA:LICENSE --include CITATION.cff:CITATION.cff
	$(TC) validate $(RELEASE)

charts:        ## README charts and the landing card from the release
	$(TC) charts $(RELEASE) --out docs/media

sample:        ## the 150-work sample shipped in the package
	$(TC) sample $(RELEASE) --works 150

bench:         ## coverage against OpenITI, Wikidata and Shamela -> bench/results.json
	PYTHON=$(PY) TC=$(TC) bench/compare.sh $(RELEASE)

zip:           ## one archive per release for the GitHub release page
	cd releases && ../$(PY) -m zipfile -c turath-catalog-$(VERSION).zip turath-catalog-$(VERSION)

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist
