# Tool: research-eval engine

This talent is **engine-backed**, not pure-skill. The implementation lives in the
`research_eval/` Python package at the repo root and exposes its own agentic tool
loop + LLM backends. This folder declares that engine to the Talent Market /
OMC per the talent-template `tools/` convention.

## Entry point

```
research-eval review \
    --paper      <paper.pdf | paper.md> \
    --workspace  <dir the paper claims to be based on> \
    --config     api-key.md \
    --output     review.md \
    --output-format markdown|json
```

`run.sh` in this folder is a thin wrapper around that CLI (`python -m research_eval`).

## Tools the engine exposes to the LLM judge

Implemented in `research_eval/tools.py` and `research_eval/extra_tools.py`:

| Tool | Purpose |
|---|---|
| `read_paper` | overview / search / page the paper file (PDF via pypdf, or markdown) |
| `read_file`, `read_file_lines` | read workspace text files (full / line range) |
| `list_files`, `search_in_files` | glob + regex-search the workspace |
| `run_command`, `python_eval` | shell / Python in the workspace (60s timeout, sandboxed to workspace) |
| `write_file` | write an audit script into the workspace |
| `http_request` | HTTP GET/POST (arXiv/DOI/etc.); cloud-metadata hosts blocked |
| `web_search` | Tavily web search → ranked markdown (citation verification) |
| `web_fetch` | fetch a URL → clean markdown |
| `large_doc_reader` | chunked reader for other big PDFs/HTML |
| `render_html_screenshot` | Playwright render HTML/URL → PNG (optional `[vision]` extra) |
| `vision_inspect`, `video_understand` | Gemini vision over PNG / video frames (optional) |
| `invoke_skill` | load one of the 9 workflow `.md` files and follow it |
| `submit_review` | final structured submission (call once) |

## Outputs

- A filled review template (Parts I–VI) rendered to markdown or JSON.
- Appendix A — per-experiment authenticity verdicts (with workspace `file:line` evidence).
- Appendix B — per-citation authenticity verdicts (with source URLs).
- Appendix C — collapsible tool-call log.
- Exit code `1` on desk-rejection failure OR any fabricated experiment/citation; else `0`.

## Setup

`pip install -e .` from the repo root (Python ≥ 3.10). Credentials via `api-key.md`
(copy `api-key.example.md`) or env vars. See the root `README.md` for full details.
