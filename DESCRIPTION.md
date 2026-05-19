# Paper Reviewer Pro

> Reviewer-2 grade peer review specialist — skeptical but fair, evidence-grounded, file:line precise.

## Overview

Designed as **AutoResearch Stage 9 (Peer Review)** — the adversarial self-review that the AutoResearch pipeline runs on its own generated paper before claiming completion. Equally usable standalone as a pre-submission stress test for human-authored papers.

Built around the question every accepted CS paper had to survive: *"What's the strongest reason a smart, skeptical, time-pressed Reviewer 2 would reject this?"*

## Use Cases

- **Pre-submission review** — Stress-test a paper draft before submitting to OSDI / NSDI / SOSP / NeurIPS / ICML / etc. Surface every weakness a real reviewer would raise, so you can fix or rebut in advance.
- **AutoResearch Stage 9** — Plug into OMC pipeline as the peer_reviewer producer for AutoResearch's adversarial pipeline. Replaces the default stock employee with a richer toolchain.
- **Rebuttal preparation** — Given reviewer comments, identifies the load-bearing issues and ranks them by accept-flip importance.
- **Citation hallucination audit** — Standalone: run `verify_references` on any paper's .bib to catch fake / withdrawn / mis-cited entries before the reviewer does.

## What Sets It Apart

| Vanilla LLM peer review | This talent |
|---|---|
| "Looks good, here are some thoughts" | Severity-tiered: Major (rejection-grade) / Minor / Nitpick |
| Hallucinated "missing citations" | `verify_references` only flags real .bib entries that fail real API lookup |
| Forgets line numbers | Every weakness carries `file.tex:line` |
| Generic praise | Concrete fix paired with every weakness |
| Random scoring | 5-criterion rubric with per-score justification |
| Unstructured prose | Pydantic-schema JSON + canonical reviewer report markdown |

## Demo

(Add screenshots after first real run.)

## Tools Provided

13 LangChain `@tool` functions covering:
- LaTeX project loading + section parsing + .bib extraction
- Issue scanning (TODO / placeholders / undefined acronyms / passive density)
- Reference verification against arxiv / Crossref / Semantic Scholar
- Cited-PDF fetching for fact-checking
- Pydantic schema validation + canonical markdown rendering
- Per-run provenance (review_run.json)

---

> **Content Policy** — This description is publicly visible on Talent Market. No illegal / political / explicit content. All external links must point to legitimate, safe resources.
