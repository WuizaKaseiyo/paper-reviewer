# Paper Reviewer

[![CI](https://github.com/WuizaKaseiyo/paper-reviewer/actions/workflows/ci.yml/badge.svg)](https://github.com/WuizaKaseiyo/paper-reviewer/actions/workflows/ci.yml)

A skeptical-but-fair "Reviewer 2" talent for top-tier CS venue paper review. Designed to plug into **AutoResearch / OneManCompany pipeline Stage 9 (Peer Review)** — autonomously reads a paper's `.tex` / `.bib` source, runs a 5-phase structured review (skim → deep read → killer questions → writing sweep → scoring), and emits a peer review report with `file:line` references, severity-tiered weaknesses, scores, and rebuttal priorities.

> **Talent Market compliant** — packaged per [1mancompany/talent-template](https://github.com/1mancompany/talent-template) v1.
>
> **Pure-skill talent**: no custom `@tool` files. Everything is achieved through one autoloaded `SKILL.md` + OMC's stock base tools (`read`, `grep_search`, `glob_files`, `write`, `bash`). Onboarding is essentially zero-cost — no dependencies to install, no tool registry refresh required.

---

## What it does

- **LaTeX project loading** — uses `read` + `glob_files` to gather `main.tex`, all `\input`-ed `.tex` files, and `.bib`
- **Issue scanning** — uses `grep_search` for `TODO` / `FIXME` / `\todo{}` / empty `\cite{}` / `[?]` / undefined acronyms / overused passive voice
- **Section-by-section deep read** — Abstract / Intro / Related / Method / Experiments / Results / Conclusion, each with a checklist tied to common reviewer failure modes
- **Killer Questions** — the 4-category battery (Novelty / Significance / Soundness / Clarity) that decides accept-vs-reject in real review meetings
- **Writing-quality sweep** — voice / tense / acronyms / terminology / LaTeX integrity (systemic issues only, no nit-picking)
- **5-criterion scoring** — Novelty / Significance / Soundness / Clarity / Reproducibility, each 1-5 with justification; final recommendation in 5 buckets
- **Structured output** — canonical reviewer report markdown with file:line references

## Why use this instead of asking GPT directly

| Symptom of vanilla LLM | What this talent does |
|---|---|
| Generic "great paper, here are some thoughts" | 5-criterion rubric + severity-tiered weaknesses |
| No concrete fixes | Every weakness paired with a fix |
| Forgets file:line references | Every issue carries `file.tex:line` for direct navigation |
| Inflated praise | Calibrated to top-tier acceptance thresholds, not perfection |
| Wanders off task | Strict 5-phase workflow + canonical output template |

---

## Quick install

In your OMC instance frontend, **Talent Market → Add Talent** and paste:

```
https://github.com/WuizaKaseiyo/paper-reviewer
```

OMC's onboarding flow will:

1. `git clone` this repo into `.onemancompany/talents/paper-reviewer/`
2. `execute_hire()` creates a new employee directory (e.g. `00016`)
3. Copies the autoloaded SKILL.md into the employee's prompt context
4. Registers a LangChain agent with **only stock base tools** (no custom tool registration needed)

Compared to typical talents this onboarding is **trivial** — no `assets/tools/` writes, no `tool_registry` refresh, no restart-required state.

### Or, programmatic install

```bash
curl -X POST http://localhost:8000/api/candidates/hire-from-cv \
  -H 'Content-Type: application/json' \
  -d '{
    "cv": {
      "name": "Paper Reviewer Pro",
      "role": "QA",
      "talent_id": "paper-reviewer",
      "source_repo": "https://github.com/WuizaKaseiyo/paper-reviewer",
      "skills": ["peer_reviewer", "paper-review-workflow"],
      "llm_model": "anthropic/claude-opus-4.6",
      "temperature": 0.2,
      "hosting": "company",
      "auth_method": "api_key",
      "api_provider": "openrouter"
    }
  }'
```

---

## ⚠️ Required setup

### Only one thing: `OPENROUTER_API_KEY` in OMC's `.env`

| Key | Required? | Where to get it |
|-----|-----------|-----------------|
| `OPENROUTER_API_KEY` | **REQUIRED** | https://openrouter.ai/keys (~$5 covers 3-5 full reviews with Opus) |

That's it. No `S2_API_KEY`, no `pip install`, no other setup. Pure skill = pure simplicity.

### Stage 9 dispatch

Once hired, route Stage 9 (Peer Review) work to the new employee:

```bash
# Option A: explicit assignment per task
curl -X POST http://localhost:8000/api/ceo/task \
  -F 'task=Review the submitted paper draft for OSDI 2027' \
  -F 'stage_assignments={"9": "<new_employee_id>"}'

# Option B: ensure no other employee has skill 'peer_reviewer' set —
# pipeline_engine._find_employee_by_skill('peer_reviewer') will auto-pick this one
```

---

## Skills loaded (2)

```
skills/
├── paper-review-workflow/    (autoload: true)  ← injected into every system prompt
│                                                  Contains the full 5-phase workflow
└── peer_reviewer/            (autoload: false) ← pipeline match-key alias
```

### Pipeline match key

`profile.yaml.skills` **MUST contain `peer_reviewer`** (exact string, underscore). OMC's `src/onemancompany/core/pipeline_engine.py` STAGES table hard-codes:

```python
STAGES[8] = {"id": 9, "skill": "peer_reviewer", "name": "Self-Review"}
```

`_find_employee_by_skill("peer_reviewer")` does a literal string match — rename and Stage 9 won't auto-route.

The `skills/peer_reviewer/SKILL.md` file is a thin alias pointing to `paper-review-workflow` (where the actual methodology lives). It exists because the Talent Market scanner requires every `profile.yaml.skills` entry to have a matching `skills/<name>/SKILL.md` folder.

---

## How the talent works (zero custom tools)

The whole talent is **one autoloaded SKILL.md** that instructs the LLM to use OMC's stock base tools:

| What the SKILL.md says | OMC base tool used |
|------------------------|---------------------|
| "Use **Read** to load main.tex" | `read` |
| "Use **Grep** to scan" | `grep_search` |
| "Walk \input / \include" | `glob_files` + `read` |
| "Save your review to `stage9_peer_reviewer.md`" | `write` |
| (Optional) "Run pdflatex / git blame for context" | `bash` |

There is no `tools/` directory in this repo. The talent's value is **the carefully-tuned SKILL.md prompt + the persona + a calibrated mental model of a top-tier CS reviewer**, not custom code.

This is intentional and architecturally different from talents like `literature-surveyor` (which needs arxiv/Semantic Scholar/OpenAlex API access and a structured corpus store). Peer review needs `read` + `grep_search` + thinking — both of which OMC employees already have for free.

---

## LLM configuration

Default `llm_model: anthropic/claude-opus-4.6`. Peer review demands deep critical reading + counterfactual reasoning over long context (a full paper is often 30-50 pages), so Opus is the recommended default. To experiment cheaper:

```yaml
# profile.yaml
llm_model: anthropic/claude-sonnet-4-5    # ~1/5 cost, near-identical reasoning
# or
llm_model: openai/gpt-4o                  # different reviewer flavor
```

OMC hot-reloads `profile.yaml` within seconds — no restart needed.

---

## Cost estimate

| Component | Tokens (est.) | Cost (Opus 4.6) |
|-----------|---------------|-----------------|
| Full paper deep read (Phase 2) | 100K in / 8K out | $1.50 |
| Killer Questions (Phase 3) | 15K in / 5K out | $0.60 |
| Writing sweep (Phase 4) | 20K in / 3K out | $0.50 |
| Scoring + output rendering (Phase 5) | 8K in / 4K out | $0.40 |
| **Total per review** | | **$3-5** |

Sonnet 4.5 reduces this ~5× (~$0.60-1.00 per review).

---

## Repo layout

```
paper-reviewer/
├── profile.yaml                    # Talent identity (skills include 'peer_reviewer' — pipeline match key)
├── manifest.json                   # Frontend settings UI schema
├── DESCRIPTION.md                  # Public talent marketplace blurb
├── prompts/talent_persona.md       # Role boundaries + behavioral contract
├── vessel/vessel.yaml              # Per-talent timeout (2400s) + iterations (80)
├── skills/
│   ├── peer_reviewer/SKILL.md      # Pipeline match-key alias
│   └── paper-review-workflow/SKILL.md  # The actual 5-phase workflow (autoload)
├── avatar.jpg                      # Talent card avatar
├── README.md
└── LICENSE                         # TMAL v1.0
```

No `tools/`, no `schemas/`, no `tests/`. The whole talent is **9 files**.

---

## License

[Talent Market Attribution License (TMAL) v1.0](./LICENSE).

---

## Citation

> **DO NOT REMOVE** — required by the [Talent Market Attribution License](./LICENSE).

This talent was built using the [Talent Market](https://one-man-company.com) template by [Zhengxu Yu](mailto:yuzxfred@gmail.com) / [1mancompany](https://github.com/1mancompany).

```bibtex
@software{talentmarket,
  title  = {Talent Market - AI Agent Marketplace},
  author = {Zhengxu Yu},
  email  = {yuzxfred@gmail.com},
  url    = {https://one-man-company.com},
  year   = {2026}
}
```

If you publish or deploy a talent based on this template, please keep this section intact in your README or equivalent documentation.
