#!/usr/bin/env bash
# Pack the integration directory for HACS zip_release (Slice 3/4).
# Archive root = integration files (manifest.json at top level, not nested domain dir).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INTEGRATION_DIR="${ROOT}/custom_components/high_school_sports_scores"
OUTPUT="${OUTPUT:-${ROOT}/dist/high_school_sports_scores.zip}"

if [[ ! -d "${INTEGRATION_DIR}" ]]; then
  echo "Integration directory not found: ${INTEGRATION_DIR}" >&2
  exit 1
fi

mkdir -p "$(dirname "${OUTPUT}")"
rm -f "${OUTPUT}"

(
  cd "${INTEGRATION_DIR}"
  zip -qr "${OUTPUT}" . \
    -x "*__pycache__*" \
    -x "*.pyc" \
    -x "*.pyo" \
    -x ".DS_Store"
)

echo "Created ${OUTPUT}"
