#!/usr/bin/env bash
# Coverage of a turath-catalog release in the open sources it links to (OpenITI 2025.1.9 metadata,
# Wikidata identifier crosswalks, Shamela links carried by the release). Reproducible: the sources are
# downloaded once into ./cache (OpenITI TSV ~12 MB from GitHub, three small Wikidata SPARQL results).
#   bench/compare.sh releases/turath-catalog-0.2.0
set -euo pipefail
REL=${1:?usage: bench/compare.sh RELEASE_DIR}
CACHE=${CACHE:-cache}
TC=${TC:-turath-catalog}
mkdir -p "$CACHE"
"${PYTHON:-python3}" - "$CACHE" <<'PY'
import sys
from pathlib import Path
from turath_catalog import link
cache = Path(sys.argv[1])
print("OpenITI versions:", len(link.openiti_metadata(cache)))
for name in link.QUERIES:
    print(f"Wikidata {name}:", len(link.wikidata(cache, name)))
PY
"$TC" compare "$REL" --cache "$CACHE" --out bench/results.json
