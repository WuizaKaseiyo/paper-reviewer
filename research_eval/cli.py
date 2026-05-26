"""Command-line interface for research-eval.

Usage
-----
  research-eval review \\
      --paper      paper.pdf \\
      --workspace  ./experiments \\
      --output     review.md \\
      --config     api-key.md

Optional:
  --template     path to review template (default: bundled review_template_en.md)
  --extra-context  free-form notes the user wants the reviewer to consider
  --skills-dir   extra directory of skill .md files (repeatable)
  --output-format markdown (default) | json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _default_template() -> Path:
    """Look for review_template_en.md inside the package first (works for
    pip-installed builds), then fall back to the repo root (editable install)."""
    pkg_copy = Path(__file__).resolve().parent / "review_template_en.md"
    if pkg_copy.exists():
        return pkg_copy
    return Path(__file__).resolve().parent.parent / "review_template_en.md"


_DEFAULT_TEMPLATE = _default_template()


def _add_credential_args(p: argparse.ArgumentParser) -> None:
    cred = p.add_argument_group("credentials — config file (recommended)")
    cred.add_argument(
        "--config", metavar="FILE", default=None,
        help="Path to api-key.md with 'api key', 'model', 'base url', 'provider'.",
    )
    flags = p.add_argument_group("credentials — explicit flags (override config file)")
    flags.add_argument("--provider", choices=["anthropic", "openai"], default=None)
    flags.add_argument("--model",    metavar="MODEL", default=None)
    flags.add_argument("--base-url", metavar="URL",   default=None)
    flags.add_argument("--api-key",  metavar="KEY",   default=None)


def _resolve_config(args: argparse.Namespace):
    from research_eval.config import EvalConfig, load_config
    cfg = load_config(Path(args.config)) if args.config else EvalConfig()
    if args.api_key:   cfg.api_key  = args.api_key
    if args.model:     cfg.model    = args.model
    if args.provider:  cfg.provider = args.provider
    if args.base_url:  cfg.base_url = args.base_url
    return cfg.resolve()


def _build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog        = "research-eval",
        description = "Agentic LLM peer-reviewer with experiment + citation authenticity audits.",
        formatter_class = argparse.RawDescriptionHelpFormatter,
    )
    sub = root.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p = sub.add_parser(
        "review",
        help="Review a paper against its workspace, fill the review template, and audit authenticity.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Read a paper (PDF / markdown) and the workspace that produced it, then:\n"
            "  1. Run desk-rejection checks (length, components, prompt-injection).\n"
            "  2. Audit experimental claims against workspace artifacts.\n"
            "  3. Verify each load-bearing citation against the public literature.\n"
            "  4. Fill out the review template (Parts I–VI).\n\n"
            "Example:\n"
            "  research-eval review \\\n"
            "      --paper paper.pdf --workspace ./code \\\n"
            "      --output review.md --config api-key.md"
        ),
    )
    req = p.add_argument_group("inputs (required)")
    req.add_argument("--paper",     required=True, metavar="FILE",
                     help="Path to the paper file (PDF or markdown).")
    req.add_argument("--workspace", required=True, metavar="DIR",
                     help="Path to the workspace directory the paper claims to be based on.")

    opt = p.add_argument_group("inputs (optional)")
    opt.add_argument("--template",     metavar="FILE", default=None,
                     help=f"Override review template (default: {_DEFAULT_TEMPLATE}).")
    opt.add_argument("--extra-context", metavar="TEXT", default="",
                     help="Free-form context to pass to the reviewer (e.g. venue, focus areas).")
    opt.add_argument("--skills-dir", action="append", metavar="DIR", default=[],
                     help="Extra directory of skill .md files (repeatable).")

    out = p.add_argument_group("output")
    out.add_argument("--output-format", choices=["markdown", "json"], default="markdown")
    out.add_argument("--output", "--output-file", dest="output_file",
                     metavar="FILE", default=None,
                     help="Write report to file (default: stdout).")

    _add_credential_args(p)
    return root


def _run_review(args: argparse.Namespace) -> int:
    from research_eval.evaluator import run_review
    from research_eval.models import ReviewInput
    from research_eval.report import to_json, to_markdown

    paper_path   = Path(args.paper).resolve()
    work_dir     = Path(args.workspace).resolve()
    template     = Path(args.template).resolve() if args.template else _DEFAULT_TEMPLATE.resolve()

    for path, label in [
        (paper_path, "paper"),
        (work_dir,   "workspace"),
        (template,   "template"),
    ]:
        if not path.exists():
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            return 1
    if not work_dir.is_dir():
        print(f"ERROR: workspace is not a directory: {work_dir}", file=sys.stderr)
        return 1

    try:
        cfg = _resolve_config(args)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(
        f"research-eval review\n"
        f"  paper      : {paper_path}\n"
        f"  workspace  : {work_dir}\n"
        f"  template   : {template}\n"
        f"  provider   : {cfg.provider}\n"
        f"  model      : {cfg.model or '(provider default)'}\n"
        f"  base_url   : {cfg.base_url or '(provider default)'}",
        file=sys.stderr,
    )

    skills_dirs = [Path(d).resolve() for d in (args.skills_dir or [])]

    # Stream tool-call events to stderr so the user can watch progress
    def _on_event(type_: str, message: str, detail: str | None = None) -> None:
        tag = type_.replace("review.", "")
        suffix = f"  {detail}" if detail else ""
        print(f"[{tag}] {message}{suffix}", file=sys.stderr)

    result = run_review(
        ReviewInput(
            work_dir      = work_dir,
            paper_path    = paper_path,
            template_path = template,
            extra_context = args.extra_context or "",
        ),
        provider    = cfg.provider,
        model       = cfg.model    or None,
        base_url    = cfg.base_url or None,
        api_key     = cfg.api_key  or None,
        skills_dirs = skills_dirs or None,
        on_event    = _on_event,
    )

    report = to_json(result) if args.output_format == "json" else to_markdown(result)

    if args.output_file:
        out = Path(args.output_file)
        out.write_text(report, encoding="utf-8")
        print(f"\nReport written to: {out}", file=sys.stderr)
    else:
        print(report)

    # Non-zero exit if desk-rejection failed OR any fabrication found
    if not result.desk_rejection_pass:
        return 1
    if result.has_fabricated_citations or result.has_fabricated_experiments:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args   = parser.parse_args(argv)

    if args.command == "review":
        return _run_review(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
