"""research-eval MCP server.

Exposes the agentic paper-review engine as a single MCP tool, `review_paper`.
A host (e.g. an OMC employee / Claude) calls it with a paper file and the
workspace that produced the paper; the engine then runs its full agentic review
internally — desk-rejection screen, experiment-authenticity audit against the
workspace, citation verification against the public literature — and returns the
filled review template plus per-claim / per-citation authenticity findings.

Run as an MCP server (declared in ../.mcp.json):
    python tools/research-eval/server.py

Credentials are read from the environment (set as secrets after hiring):
    ANTHROPIC_API_KEY     — use Claude (default if present)
    OPENAI_API_KEY        — use an OpenAI-compatible endpoint
    RESEARCH_EVAL_MODEL   — override the model id (optional)
    RESEARCH_EVAL_PROVIDER— "anthropic" | "openai" (optional; auto-detected)
    OPENAI_BASE_URL / ANTHROPIC_BASE_URL — proxy base URLs (optional)
    TAVILY_API_KEY        — web_search (citation verification)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# This file lives in the tool folder alongside the engine modules; make sure
# they are importable regardless of the host's working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from evaluator import run_review  # noqa: E402
from models import ReviewInput  # noqa: E402
from report import to_json, to_markdown  # noqa: E402

_TOOL_DIR = Path(__file__).resolve().parent
_DEFAULT_TEMPLATE = _TOOL_DIR / "review_template_en.md"

mcp = FastMCP("research-eval")


def _resolve_provider() -> tuple[str, str | None]:
    """Pick provider + model from the environment."""
    provider = os.environ.get("RESEARCH_EVAL_PROVIDER", "").strip().lower()
    if not provider:
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            provider = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        else:
            provider = "anthropic"
    model = os.environ.get("RESEARCH_EVAL_MODEL") or None
    return provider, model


@mcp.tool()
def review_paper(
    paper: str,
    workspace: str,
    extra_context: str = "",
    output_format: str = "markdown",
) -> str:
    """Review a research paper AND audit it against the workspace that produced it.

    Runs the full agentic review: desk-rejection screen, experiment-authenticity
    audit (cross-checks the paper's load-bearing numbers against the workspace's
    real logs/results/code), citation verification against the public literature,
    rubric scoring, and the filled review template — flagging fabricated
    experiments and hallucinated citations with evidence.

    Args:
        paper:         Path to the paper file (.pdf or .md).
        workspace:     Path to the directory the paper claims to be based on
                       (code/configs/logs/results). Use an empty dir for a
                       citation-only screen.
        extra_context: Optional notes for the reviewer (target venue, focus
                       areas, budget caps).
        output_format: "markdown" (default) or "json".

    Returns:
        The review report as markdown or JSON.
    """
    paper_path = Path(paper).expanduser().resolve()
    work_dir = Path(workspace).expanduser().resolve()

    if not paper_path.exists():
        return f"ERROR: paper not found: {paper_path}"
    if not work_dir.is_dir():
        return f"ERROR: workspace is not a directory: {work_dir}"
    if not _DEFAULT_TEMPLATE.exists():
        return f"ERROR: bundled review template missing: {_DEFAULT_TEMPLATE}"

    provider, model = _resolve_provider()

    def _on_event(type_: str, message: str, detail: str | None = None) -> None:
        # MCP uses stdout for protocol — log progress to stderr only.
        suffix = f"  {detail}" if detail else ""
        print(f"[{type_.replace('review.', '')}] {message}{suffix}", file=sys.stderr)

    result = run_review(
        ReviewInput(
            work_dir=work_dir,
            paper_path=paper_path,
            template_path=_DEFAULT_TEMPLATE,
            extra_context=extra_context or "",
        ),
        provider=provider,
        model=model,
        base_url=None,
        api_key=None,
        on_event=_on_event,
    )

    return to_json(result) if output_format == "json" else to_markdown(result)


if __name__ == "__main__":
    mcp.run()
