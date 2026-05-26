#!/usr/bin/env bash
# Thin wrapper around the research-eval CLI (the talent's engine entry point).
# Resolves the repo root regardless of where this script is invoked from, then
# delegates all arguments to `python -m research_eval`.
#
# Example:
#   tools/research-eval/run.sh review \
#       --paper paper.pdf --workspace ./code \
#       --config api-key.md --output review.md
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

exec python -m research_eval "$@"
