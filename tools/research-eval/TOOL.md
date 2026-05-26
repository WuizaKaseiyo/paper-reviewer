---
name: research-eval
description: Review a paper and audit it against its workspace — verifying every experimental number and citation — via MCP.
---

# Research Eval Tool

MCP server (declared in `tools/.mcp.json`) that exposes one tool, `review_paper`.
It runs a full agentic review of a research paper against the workspace that
produced it: a desk-rejection screen, an experiment-authenticity audit that
cross-checks the paper's load-bearing numbers against the workspace's real
logs/results/code, citation verification against the public literature, and
rubric scoring — flagging fabricated experiments and hallucinated citations with
evidence, then filling the review template (Parts I–VI).

## Tool: `review_paper`

| Argument | Required | Description |
|---|---|---|
| `paper` | ✅ | Path to the paper file (`.pdf` or `.md`). |
| `workspace` | ✅ | Directory the paper claims to be based on (code/configs/logs/results). An empty dir → citation-only screen. |
| `extra_context` | — | Notes for the reviewer (target venue, focus areas, budget caps). |
| `output_format` | — | `markdown` (default) or `json`. |

Returns the filled review template plus per-experiment and per-citation
authenticity findings (each verdict carries evidence: a workspace `file:line` or
a source URL).

## When to use

- Stress-test a paper before submission, with its code/data workspace available.
- AutoResearch Stage 9 (Self-Review): adversarially audit a pipeline's own paper.
- Catch fabricated results (numbers in no log/result file) or hallucinated citations.
- Citation-only screens (point `workspace` at an empty directory).

## Configuration (env / secrets)

Set via the empty `env` values in `tools/.mcp.json` after hiring:

- `ANTHROPIC_API_KEY` — use Claude (default if present), or `OPENAI_API_KEY` for
  an OpenAI-compatible endpoint.
- `TAVILY_API_KEY` — web search for citation verification.
- `RESEARCH_EVAL_MODEL` — override the model id (optional).

The same engine is also runnable as a standalone CLI (`cli.py`); see the root README.
