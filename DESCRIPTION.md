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

It is **engine-backed**: an agentic loop drives ~16 internal tools (`read_paper`,
`search_in_files`, `run_command`, `python_eval`, `web_search`, `web_fetch`,
`invoke_skill`, `submit_review`, …) across Anthropic and OpenAI-compatible
backends, then fills a structured review template (Parts I–VI) plus per-claim /
per-citation authenticity appendices — every verdict carrying evidence
(workspace `file:line` or a source URL).

## Use Cases

- **Pre-submission audit** — Catch fabricated-looking results and bad citations
  before a real reviewer (or a venue's integrity check) does.
- **AutoResearch Stage 9** — Plug in as the `peer_reviewer` producer for an
  adversarial self-review pipeline.
- **CI gating** — Exit code is non-zero on desk-rejection failure or any fabricated
  experiment/citation, so `research-eval review ... && deploy` works as a gate.
- **Citation-only screen** — Point the workspace at an empty dir to audit just the
  bibliography.

## Demo

<!-- Add screenshots, GIFs, or video links showcasing the agent in action -->
<!-- Example: ![Demo Screenshot](./assets/demo.png) -->

## Success Stories

<!-- Share real-world results or testimonials -->
<!-- Example: "Caught 3 hallucinated citations and 2 unbacked table numbers in a draft before submission." -->

## Methodology & Rules

The reviewer follows a 7-step workflow (see `skills/research-eval-review/SKILL.md`):
map the paper → desk-rejection screen → map the workspace → audit experimental
claims → audit citations → score the rubric → submit.

Hard rules it holds itself to:

- **Evidence only.** Never fabricate evidence — cite only what tool outputs
  actually returned (workspace `file:line`, log lines, numbers, source URLs).
- **Missing ≠ confirmed.** When a citation can't be found after ≥3 differently
  phrased searches, it is `fabricated`; when merely hard to confirm, `unverifiable`
  (never silently `verified`). Experiment numbers absent from the workspace lean
  `fabricated`, but only after checking for aliases / other locations.
- **Audit every citation**, not just the load-bearing ones — hallucinations hide
  in routine references.
- **Consistent severity.** Two similar issues get the same tier.
- **Self-contained output.** Every structured finding is also reflected in the
  filled review markdown.

Status taxonomies — experiments: `verified` / `partially_verified` / `unverifiable`
/ `contradicted` / `fabricated`; citations: `verified` / `metadata_mismatch` /
`unverifiable` / `fabricated`. Overall score is 1 (Strong Reject) … 6 (Strong Accept).

---

> **Content Policy**: This description is publicly visible on the Talent Market platform.
> Do not include illegal content, political propaganda, child exploitation material,
> pornography, or graphic violence. Violations will result in talent removal and
> repeated offenses will lead to permanent account suspension.
> All external links must point to legitimate, safe resources.
