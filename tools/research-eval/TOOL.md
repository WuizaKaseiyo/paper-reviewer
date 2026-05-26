---
name: research-eval
description: Agentic paper reviewer + authenticity auditor — reviews a paper against its workspace, verifying every experimental number and citation, then fills the review template.
---

# Research Eval

The engine that backs this talent. Given a paper (PDF / markdown) and the
workspace that produced it, it runs an agentic review loop that:

1. Desk-rejection screen (length / topic / required sections / prompt injection).
2. Audits each load-bearing experimental number against the workspace's real
   logs / results / code.
3. Verifies each citation against the public literature (web search).
4. Fills the review template (Parts I–VI) and emits authenticity appendices.

## Usage

```
bash tools/research-eval/run.sh review \
    --paper <paper.pdf|paper.md> \
    --workspace <dir the paper claims to be based on> \
    --config api-key.md \
    --output review.md \
    --output-format markdown|json
```

`run.sh` wraps `cli.py` in this folder. Exit code is `1` on desk-rejection
failure or any fabricated experiment/citation, else `0`.

## Internal tools (driven by the engine's LLM judge)

Implemented in this folder's `review_tools.py` / `extra_tools.py`:

| Group | Tools |
|---|---|
| Paper / workspace | `read_paper`, `read_file`, `read_file_lines`, `list_files`, `search_in_files`, `run_command`, `write_file`, `python_eval`, `http_request` |
| Web / vision      | `web_search`, `web_fetch`, `large_doc_reader`, `render_html_screenshot`, `vision_inspect`, `video_understand` |
| Composite         | `invoke_skill` (loads a `skills/<name>/SKILL.md` workflow) |
| Final             | `submit_review` |

## Setup

`pip install -e tools/research-eval` from the repo root (Python ≥ 3.10).
Credentials via `api-key.md` (copy `api-key.example.md` in this folder) or env
vars. See the root README.
