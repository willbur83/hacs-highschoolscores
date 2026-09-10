#!/usr/bin/env bash
# Assert release ZIP layout matches hacs.json zip_release expectations.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ZIP="${ZIP:-${ROOT}/dist/high_school_sports_scores.zip}"
HACS_JSON="${ROOT}/hacs.json"

if [[ ! -f "${ZIP}" ]]; then
  echo "Release zip not found: ${ZIP}" >&2
  exit 1
fi

expected_filename="$(python3 -c "import json; print(json.load(open('${HACS_JSON}'))['filename'])")"
zip_basename="$(basename "${ZIP}")"
if [[ "${zip_basename}" != "${expected_filename}" ]]; then
  echo "Expected zip filename ${expected_filename}, got ${zip_basename}" >&2
  exit 1
fi

for required in manifest.json brand/icon.png www/high-school-sports-scores-card.js; do
  if ! unzip -l "${ZIP}" | awk '{print $4}' | grep -qx "${required}"; then
    echo "Missing required zip root entry: ${required}" >&2
    exit 1
  fi
done

if unzip -l "${ZIP}" | awk '{print $4}' | grep -q '^high_school_sports_scores/'; then
  echo "Zip must not contain nested high_school_sports_scores/ directory" >&2
  exit 1
fi

echo "Release zip assertions passed: ${ZIP}"
