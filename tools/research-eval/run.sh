#!/usr/bin/env bash
# Wrapper around the research-eval engine CLI. The engine modules live in this
# same directory; cd here (regardless of invocation cwd) and run cli.py.
#
# Example:
#   bash tools/research-eval/run.sh review \
#       --paper paper.pdf --workspace ./code \
#       --config api-key.md --output review.md
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TOOL_DIR"

exec python cli.py "$@"
