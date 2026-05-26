# Research Eval

> Agentic peer reviewer that doesn't just score a paper — it audits whether the paper is **real**.

## Overview

Most LLM "paper reviewers" read the PDF and opine. Research Eval also takes the
**workspace that produced the paper** (code, configs, training logs, result files)
and independently verifies the paper against it. It is designed as **AutoResearch
Stage 9 (Self-Review)** — the adversarial audit a research pipeline runs on its own
output before claiming completion — and works equally well as a pre-submission
stress test for human-authored papers.

It answers two questions a normal review skips:

1. **Are the experiments real?** Every load-bearing number (each table cell, key
   figure, headline metric) is cross-checked against the workspace's actual
   logs/results/code. A number that appears nowhere in the workspace gets flagged.
2. **Are the citations real?** Every reference is verified against the public
   literature via web search. Hallucinated / mis-attributed references get flagged.

## Use Cases

- **Pre-submission audit** — catch fabricated-looking results and bad citations
  before a real reviewer (or a venue's integrity check) does.
- **AutoResearch Stage 9** — plug in as the `peer_reviewer` producer for an
  adversarial self-review pipeline.
- **CI gating** — exit code is non-zero on desk-rejection failure or any fabricated
  experiment/citation, so `research-eval review ... && deploy` works as a gate.
- **Citation-only screen** — point the workspace at an empty dir to audit just the
  bibliography.

## What Sets It Apart

| Vanilla LLM peer review | Research Eval |
|---|---|
| Reads the PDF only | Reads the PDF **and** the workspace that produced it |
| "Looks plausible" | Each number cross-checked against real logs/results — `verified` … `fabricated` |
| Trusts the bibliography | Every citation web-verified — `verified` … `fabricated` |
| Prose opinion | Filled review template (Parts I–VI) + per-claim / per-citation audit appendices |
| No evidence trail | Every verdict carries evidence: workspace `file:line` or a source URL |
| Single model only | Anthropic **and** OpenAI-compatible backends (Claude / GPT / OpenRouter / DeepSeek / Qwen) |

## Tools Provided

The bundled `research_eval/` engine exposes ~16 tools to the LLM judge:

- Paper / workspace: `read_paper`, `read_file`, `read_file_lines`, `list_files`,
  `search_in_files`, `run_command`, `write_file`, `python_eval`, `http_request`
- Web / vision: `web_search`, `web_fetch`, `large_doc_reader`,
  `render_html_screenshot`, `vision_inspect`, `video_understand`
- Composite: `invoke_skill` (9 built-in review workflows)
- Final: `submit_review`

---

> **Content Policy** — This description is publicly visible on Talent Market. No
> illegal / political / explicit content. All external links point to legitimate,
> safe resources.
