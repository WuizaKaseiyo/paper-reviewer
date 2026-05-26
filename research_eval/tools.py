"""Tools available to the research-review LLM judge.

Workspace inspection tools
──────────────────────────
  read_file              — read a text file from the workspace
  read_file_lines        — read a specific line range (large files)
  list_files             — list files matching a glob pattern (with sizes)
  search_in_files        — regex search across workspace files
  run_command            — execute a shell command in the workspace
  write_file             — write text content to a file
  python_eval            — execute a Python snippet, capture stdout/stderr
  http_request           — make an HTTP request (testing services / fetching artifacts)

Paper-specific shortcut
───────────────────────
  read_paper             — read / search / page the paper file (wraps large_doc_reader
                           on a path outside the workspace tree). Use for the PDF.

Web / vision / large-doc (see extra_tools.py)
─────────────────────────────────────────────
  web_search             — Tavily web search → ranked markdown (verify citations)
  web_fetch              — fetch URL → main content as clean markdown
  render_html_screenshot — Playwright render of HTML/URL → PNG
  vision_inspect         — Gemini vision: image + question → text
  video_understand       — Gemini video frames → text
  large_doc_reader       — chunked + searchable reader for HTML/PDF/text

Skill invocation
────────────────
  invoke_skill           — load a skill workflow (.md) and follow its steps

Final submission
────────────────
  submit_review          — emit the filled review report and authenticity findings.
                           Call exactly once at the end.
"""
from __future__ import annotations

import json
import re
import subprocess
import textwrap
import urllib.request
import urllib.error
from urllib.parse import urlparse
from pathlib import Path

from .extra_tools import EXTRA_TOOL_SPECS, ExtraTools, _extract_text, _chunkify


_MAX_READ_BYTES = 256_000

_BINARY_HINT: dict[str, str] = {
    ".xlsx":    "Use python_eval with openpyxl/pandas.",
    ".xls":     "Use python_eval with pandas.",
    ".db":      "Use python_eval with sqlite3.",
    ".sqlite":  "Use python_eval with sqlite3.",
    ".parquet": "Use python_eval with pandas.read_parquet().",
    ".pdf":     "Use read_paper(...) for the main paper, or large_doc_reader for any other PDF.",
}

_SEARCH_MAX_FILE_BYTES = 5_000_000
_SEARCH_MAX_LINE_CHARS = 500
_SEARCH_MAX_RESULTS    = 80

_HTTP_ALLOWED_SCHEMES = {"http", "https"}
_HTTP_BLOCKED_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata",
    "100.100.100.200",
}

_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_BUILTIN_SKILLS_DIR = Path(__file__).parent / "skills"


class SkillLoader:
    """Loads skill workflow markdown files from one or more directories."""

    def __init__(self, extra_dirs: list[Path] | None = None) -> None:
        dirs: list[Path] = list(extra_dirs or [])
        dirs.append(_BUILTIN_SKILLS_DIR)
        self._dirs = dirs

    def names(self) -> list[str]:
        seen: set[str] = set()
        names: list[str] = []
        for d in self._dirs:
            if d.is_dir():
                for f in sorted(d.glob("*.md")):
                    name = f.stem
                    if name not in seen:
                        seen.add(name)
                        names.append(name)
        return sorted(names)

    def load(self, name: str) -> str | None:
        if not _SKILL_NAME_RE.match(name):
            return None
        for d in self._dirs:
            candidate = d / f"{name}.md"
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        return None

    def descriptions(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in self.names():
            content = self.load(name) or ""
            lines = content.splitlines()
            desc = ""
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    desc = stripped
                    break
            result[name] = desc
        return result


_BASE_TOOL_SPECS: list[dict] = [
    {
        "name": "read_file",
        "description": (
            "Read the full text content of a text file inside the workspace. "
            "256 KB cap. Binary files (.xlsx, .db, .pdf, .parquet, .xls, .sqlite) are rejected "
            "with a hint to use the appropriate alternative."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to the workspace root."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file_lines",
        "description": (
            "Read a line range from a text file (streams line-by-line, no size cap). "
            "Use for large logs, training outputs, or CSVs when you only need a portion."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path":       {"type": "string"},
                "start_line": {"type": "integer", "description": "1-based start (default 1)."},
                "end_line":   {"type": "integer", "description": "1-based end inclusive (default start+99)."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": (
            "List workspace files matching a glob pattern. Returns paths with sizes. "
            "Use to map what the agent actually produced (training logs, configs, checkpoints, results)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern relative to workspace root."},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "search_in_files",
        "description": (
            "Search for a regex pattern across workspace files. Returns up to 80 matching lines. "
            "Use to verify that specific numbers reported in the paper actually appear in logs/output files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern":   {"type": "string"},
                "file_glob": {"type": "string"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "run_command",
        "description": (
            "Run a shell command inside the workspace (timeout 60 s). "
            "Use for: wc -l, head/tail, find, grep, git log, sqlite3 queries, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write text content to a file inside the workspace (e.g. an audit script to run via run_command)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "python_eval",
        "description": (
            "Execute Python in the workspace and capture stdout/stderr (timeout 60 s). "
            "Common libraries: pandas, numpy, openpyxl, bs4, json, csv, re, os, pathlib, sqlite3."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    },
    {
        "name": "http_request",
        "description": "HTTP GET/POST request — fetch arXiv abstracts, DOI metadata, project URLs, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url":     {"type": "string"},
                "method":  {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                "body":    {"type": "string"},
                "headers": {"type": "object"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "read_paper",
        "description": (
            "Read / search / page the paper file (PDF or markdown). Wraps large_doc_reader for the paper path. "
            "Modes:\n"
            "  overview            — total chars, num chunks, headings, first chunk preview\n"
            "  search (+ query)    — top matching chunks for a keyword/regex\n"
            "  page   (+ chunk_index) — full content of one chunk + N neighbours\n"
            "Always start with mode='overview' to understand the paper structure."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode":        {"type": "string", "enum": ["overview", "search", "page"]},
                "query":       {"type": "string"},
                "chunk_index": {"type": "integer"},
                "chunk_size":  {"type": "integer"},
                "max_hits":    {"type": "integer"},
                "context":     {"type": "integer"},
            },
            "required": ["mode"],
        },
    },
    {
        "name": "submit_review",
        "description": (
            "Submit the final review. Call this exactly once after gathering sufficient evidence. "
            "Provide:\n"
            "  - filled_review_markdown:  the fully filled review template (Parts I–VI of review_template_en.md)\n"
            "  - desk_rejection_pass:     boolean — did the paper pass all desk-rejection checks\n"
            "  - overall_score:           1–6 integer matching Part IV\n"
            "  - experiment_authenticity_checks: list of audits — claim vs. workspace evidence\n"
            "  - citation_authenticity_checks:   list of audits — each citation's verified/unverified/fabricated status\n"
            "All structured findings should ALSO be reflected in filled_review_markdown so the markdown is self-contained."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filled_review_markdown": {
                    "type": "string",
                    "description": "Full markdown filling the review template — every section.",
                },
                "desk_rejection_pass": {
                    "type": "boolean",
                    "description": "True iff Part I (length, topic, components, prompt-injection) all pass.",
                },
                "overall_score": {
                    "type": "integer",
                    "description": "1 = Strong Reject … 6 = Strong Accept (Part IV).",
                },
                "experiment_authenticity_checks": {
                    "type": "array",
                    "description": "One entry per important experimental claim audited against workspace evidence.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {
                                "type": "string",
                                "description": "Quoted or paraphrased claim from the paper (cite Section / Table / Figure).",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["verified", "partially_verified", "unverifiable", "contradicted", "fabricated"],
                            },
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Workspace file paths, log lines, or numbers backing the verdict.",
                            },
                            "notes": {"type": "string"},
                        },
                        "required": ["claim", "status", "evidence"],
                    },
                },
                "citation_authenticity_checks": {
                    "type": "array",
                    "description": "One entry per citation that was audited (focus on the load-bearing ones).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "reference": {
                                "type": "string",
                                "description": "Citation as it appears in the paper (authors, title, year, venue).",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["verified", "metadata_mismatch", "unverifiable", "fabricated"],
                            },
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Web search URLs, fetched venue pages, DOIs, etc.",
                            },
                            "notes": {"type": "string"},
                        },
                        "required": ["reference", "status", "evidence"],
                    },
                },
            },
            "required": [
                "filled_review_markdown",
                "desk_rejection_pass",
                "overall_score",
                "experiment_authenticity_checks",
                "citation_authenticity_checks",
            ],
        },
    },
]


def _invoke_skill_spec(loader: SkillLoader) -> dict:
    descs = loader.descriptions()
    names = loader.names()

    catalogue_lines = ["Available skills:"]
    for name in names:
        desc = descs.get(name, "")
        catalogue_lines.append(f"  {name}: {desc}")
    catalogue = "\n".join(catalogue_lines)

    return {
        "name": "invoke_skill",
        "description": (
            "Load a skill workflow and follow its step-by-step instructions using "
            "the other available tools. When you call this tool, you receive the full "
            "workflow markdown — read it carefully and execute each step.\n\n"
            f"{catalogue}"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "skill": {"type": "string", "enum": names},
                "args":  {"type": "object"},
            },
            "required": ["skill"],
        },
    }


def get_tool_specs(loader: SkillLoader) -> list[dict]:
    return _BASE_TOOL_SPECS + [_invoke_skill_spec(loader)] + EXTRA_TOOL_SPECS


class WorkspaceTools:
    """Executes tool calls against a specific workspace + paper file."""

    def __init__(self, work_dir: Path, paper_path: Path, loader: SkillLoader) -> None:
        self._root   = work_dir.resolve()
        self._paper  = paper_path.resolve()
        self._loader = loader
        self._extra  = ExtraTools(self._root)
        self._paper_cache: tuple[list[str], list[str]] | None = None

    def dispatch(self, name: str, args: dict) -> str:
        if ExtraTools.supports(name):
            return self._extra.dispatch(name, args)
        if name == "read_file":
            return self._read_file(args["path"])
        if name == "read_file_lines":
            return self._read_file_lines(
                args["path"],
                args.get("start_line", 1),
                args.get("end_line"),
            )
        if name == "list_files":
            return self._list_files(args["pattern"])
        if name == "search_in_files":
            return self._search(args["pattern"], args.get("file_glob", "**/*"))
        if name == "run_command":
            return self._run(args["command"])
        if name == "write_file":
            return self._write_file(args["path"], args["content"])
        if name == "python_eval":
            return self._python_eval(args["code"])
        if name == "http_request":
            return self._http_request(
                args["url"],
                method=args.get("method", "GET"),
                body=args.get("body"),
                headers=args.get("headers") or {},
            )
        if name == "read_paper":
            return self._read_paper(
                mode=args.get("mode", "overview"),
                query=args.get("query"),
                chunk_index=args.get("chunk_index"),
                chunk_size=int(args.get("chunk_size", 4000)),
                max_hits=int(args.get("max_hits", 5)),
                context=int(args.get("context", 0)),
            )
        if name == "invoke_skill":
            return self._invoke_skill(args["skill"], args.get("args") or {})
        if name == "submit_review":
            return json.dumps({
                "status": "recorded",
                "experiment_checks": len(args.get("experiment_authenticity_checks", [])),
                "citation_checks":   len(args.get("citation_authenticity_checks", [])),
            })
        return f"Unknown tool: {name}"

    def _safe_path(self, rel: str) -> Path | None:
        target = (self._root / rel).resolve()
        try:
            target.relative_to(self._root)
        except ValueError:
            return None
        return target

    def _read_file(self, rel: str) -> str:
        target = self._safe_path(rel)
        if target is None:
            return "ERROR: path escapes workspace boundary"
        if not target.exists():
            return f"ERROR: file not found: {rel}"

        ext = target.suffix.lower()
        if ext in _BINARY_HINT:
            return f"ERROR: '{rel}' is binary ({ext}). {_BINARY_HINT[ext]}"

        size = target.stat().st_size
        if size > _MAX_READ_BYTES:
            return (
                f"ERROR: '{rel}' is {size:,} B (> {_MAX_READ_BYTES:,} B cap). "
                f"Use read_file_lines for a range, or python_eval for large data."
            )

        try:
            data = target.read_bytes()
        except Exception as e:
            return f"ERROR: {e}"

        if b"\x00" in data:
            return f"ERROR: '{rel}' looks binary (NUL bytes). Use python_eval with the right library."

        return data.decode("utf-8", errors="replace")

    def _read_file_lines(self, rel: str, start: int, end: int | None) -> str:
        target = self._safe_path(rel)
        if target is None:
            return "ERROR: path escapes workspace boundary"
        if not target.exists():
            return f"ERROR: file not found: {rel}"

        ext = target.suffix.lower()
        if ext in _BINARY_HINT:
            return f"ERROR: '{rel}' is binary ({ext}). {_BINARY_HINT[ext]}"

        s = max(1, start)
        e = end if end is not None else start + 99
        if e < s:
            return f"ERROR: end_line ({end}) < start_line ({start})"

        try:
            selected: list[str] = []
            total = 0
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if s <= i <= e:
                        selected.append(line)
                    total = i
        except Exception as ex:
            return f"ERROR: {ex}"

        actual_end = min(e, total)
        header = f"[Lines {s}–{actual_end} of {total}]\n"
        return header + "".join(selected)

    def _list_files(self, pattern: str) -> str:
        try:
            paths = sorted(p for p in self._root.glob(pattern) if p.is_file())
            if not paths:
                return "(no files matched)"
            lines = []
            for p in paths:
                try:
                    size = p.stat().st_size
                    size_str = f"{size:,} B" if size < 1024 else f"{size/1024:.1f} KB"
                except OSError:
                    size_str = "?"
                lines.append(f"{p.relative_to(self._root)}  [{size_str}]")
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: {e}"

    def _search(self, pattern: str, file_glob: str) -> str:
        try:
            rx = re.compile(pattern)
        except re.error as e:
            return f"ERROR: invalid regex: {e}"
        results: list[str] = []
        for fp in sorted(self._root.glob(file_glob or "**/*")):
            if not fp.is_file():
                continue
            if fp.suffix.lower() in _BINARY_HINT:
                continue
            try:
                if fp.stat().st_size > _SEARCH_MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    for n, line in enumerate(f, 1):
                        if rx.search(line):
                            snippet = line.rstrip()[:_SEARCH_MAX_LINE_CHARS]
                            results.append(
                                f"{fp.relative_to(self._root)}:{n}: {snippet}"
                            )
                            if len(results) >= _SEARCH_MAX_RESULTS:
                                results.append(f"... (truncated at {_SEARCH_MAX_RESULTS} results)")
                                return "\n".join(results)
            except Exception:
                continue
        return "\n".join(results) if results else "(no matches found)"

    def _run(self, command: str) -> str:
        try:
            proc = subprocess.run(
                command, shell=True, cwd=self._root,
                capture_output=True, text=True, timeout=60,
            )
            parts = []
            if proc.stdout:
                parts.append(f"STDOUT:\n{proc.stdout}")
            if proc.stderr:
                parts.append(f"STDERR:\n{proc.stderr}")
            parts.append(f"EXIT CODE: {proc.returncode}")
            return "\n".join(parts)
        except subprocess.TimeoutExpired:
            return "ERROR: command timed out after 60 seconds"
        except Exception as e:
            return f"ERROR: {e}"

    def _write_file(self, rel: str, content: str) -> str:
        target = self._safe_path(rel)
        if target is None:
            return "ERROR: path escapes workspace boundary"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"OK: wrote {len(content)} chars to {rel}"
        except Exception as e:
            return f"ERROR: {e}"

    def _python_eval(self, code: str) -> str:
        try:
            proc = subprocess.run(
                ["python3", "-"],
                input=textwrap.dedent(code),
                cwd=self._root,
                capture_output=True, text=True, timeout=60,
            )
            parts = []
            if proc.stdout:
                parts.append(f"STDOUT:\n{proc.stdout}")
            if proc.stderr:
                parts.append(f"STDERR:\n{proc.stderr}")
            parts.append(f"EXIT CODE: {proc.returncode}")
            return "\n".join(parts)
        except subprocess.TimeoutExpired:
            return "ERROR: python_eval timed out after 60 seconds"
        except Exception as e:
            return f"ERROR: {e}"

    def _http_request(
        self,
        url: str,
        method: str = "GET",
        body: str | None = None,
        headers: dict | None = None,
    ) -> str:
        parsed = urlparse(url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in _HTTP_ALLOWED_SCHEMES:
            return (
                f"ERROR: only http/https schemes allowed (got '{scheme or '<none>'}'). "
                f"To read a local file use read_file."
            )
        host = (parsed.hostname or "").lower()
        if host in _HTTP_BLOCKED_HOSTS:
            return f"ERROR: host '{host}' is blocked (cloud metadata endpoint)."

        try:
            data = body.encode() if body else None
            req = urllib.request.Request(
                url, data=data, method=method.upper(),
                headers=headers or {},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                status  = resp.status
                hdrs    = dict(resp.headers)
                content = resp.read(32_768).decode("utf-8", errors="replace")
            return (
                f"STATUS: {status}\n"
                f"HEADERS: {json.dumps(hdrs, indent=2)}\n"
                f"BODY ({len(content)} chars):\n{content}"
            )
        except urllib.error.HTTPError as e:
            body_snippet = e.read(2048).decode("utf-8", errors="replace")
            return f"HTTP ERROR {e.code}: {e.reason}\nBODY: {body_snippet}"
        except Exception as e:
            return f"ERROR: {e}"

    def _read_paper(
        self,
        mode: str,
        query: str | None,
        chunk_index: int | None,
        chunk_size: int,
        max_hits: int,
        context: int,
    ) -> str:
        if not self._paper.exists():
            return f"ERROR: paper file not found: {self._paper}"
        if self._paper_cache is None:
            try:
                text, headings = _extract_text(self._paper)
            except Exception as e:
                return f"ERROR: paper extraction failed: {e}"
            self._paper_cache = (_chunkify(text, chunk_size or 4000), headings)
        chunks, headings = self._paper_cache
        total_chars = sum(len(c) for c in chunks)

        if mode == "overview":
            preview = chunks[0] if chunks else ""
            if len(preview) > 1500:
                preview = preview[:1500] + "..."
            head_block = "\n".join(f"  - {h}" for h in headings[:50]) or "  (no headings)"
            return (
                f"PAPER OVERVIEW: {self._paper.name}\n"
                f"  total_chars: {total_chars:,}\n"
                f"  num_chunks:  {len(chunks)}\n"
                f"\nTOP HEADINGS (first 50):\n{head_block}\n"
                f"\nCHUNK 0 PREVIEW:\n{preview}"
            )

        if mode == "search":
            if not query:
                return "ERROR: mode='search' requires a 'query'."
            try:
                rx = re.compile(query, re.IGNORECASE)
            except re.error as e:
                return f"ERROR: invalid regex: {e}"
            hits: list[tuple[int, int, str]] = []
            for i, c in enumerate(chunks):
                m = rx.search(c)
                if m:
                    snippet = c[max(0, m.start() - 100): m.end() + 200]
                    hits.append((i, m.start(), snippet))
                    if len(hits) >= max_hits:
                        break
            if not hits:
                return f"(no matches for /{query}/ in paper, {len(chunks)} chunks)"
            out = [f"PAPER SEARCH '{query}' — {len(hits)} hit(s):", ""]
            for i, pos, snip in hits:
                out.append(f"--- chunk {i} (offset {pos}) ---")
                out.append(snip.strip())
                out.append("")
            out.append("Use mode='page' with chunk_index=N for the full chunk.")
            return "\n".join(out)

        if mode == "page":
            if chunk_index is None:
                return "ERROR: mode='page' requires 'chunk_index'."
            if not (0 <= chunk_index < len(chunks)):
                return f"ERROR: chunk_index out of range [0, {len(chunks) - 1}]"
            lo = max(0, chunk_index - context)
            hi = min(len(chunks) - 1, chunk_index + context)
            parts = []
            for i in range(lo, hi + 1):
                parts.append(f"--- paper chunk {i} of {len(chunks)} ---")
                parts.append(chunks[i])
            return "\n".join(parts)

        return f"ERROR: unknown mode '{mode}'. Use overview/search/page."

    def _invoke_skill(self, skill_name: str, args: dict) -> str:
        content = self._loader.load(skill_name)
        if content is None:
            available = ", ".join(self._loader.names())
            return f"ERROR: skill '{skill_name}' not found. Available: {available}"

        args_block = ""
        if args:
            args_lines = "\n".join(f"  {k}: {json.dumps(v)}" for k, v in args.items())
            args_block = f"\n## Invocation Arguments\n\n{args_lines}\n"

        return (
            f"# Skill Workflow: {skill_name}\n"
            f"{args_block}\n"
            f"---\n\n"
            f"{content}\n\n"
            f"---\n"
            f"Follow the workflow above using the available tools. "
            f"Use the invocation arguments (if any) to customise each step."
        )
