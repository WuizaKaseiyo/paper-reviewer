"""Render a ReviewResult as the final review report (markdown) or JSON.

The markdown report has two halves:
  1. The full filled review template (Parts I–VI), exactly as the judge submitted it.
  2. An appendix with the structured authenticity audit (experiment + citation tables).

The JSON form is for downstream tooling.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from models import (
    CitationStatus,
    ExperimentStatus,
    ReviewResult,
)


_EXP_ICON = {
    ExperimentStatus.VERIFIED:           "✅",
    ExperimentStatus.PARTIALLY_VERIFIED: "🟡",
    ExperimentStatus.UNVERIFIABLE:       "⚠️",
    ExperimentStatus.CONTRADICTED:       "❌",
    ExperimentStatus.FABRICATED:         "🚨",
}

_CIT_ICON = {
    CitationStatus.VERIFIED:          "✅",
    CitationStatus.METADATA_MISMATCH: "🟡",
    CitationStatus.UNVERIFIABLE:      "⚠️",
    CitationStatus.FABRICATED:        "🚨",
}


def to_markdown(result: ReviewResult) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []

    lines += [
        "# Research Review Report",
        f"\n_Generated at {now} by research-eval_",
        "",
        "## Inputs",
        "",
        f"- **Paper:** `{result.review_input.paper_path}`",
        f"- **Workspace:** `{result.review_input.work_dir}`",
        f"- **Template:** `{result.review_input.template_path}`",
        "",
        "## Headline Verdict",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Desk rejection passed | {'✅ Yes' if result.desk_rejection_pass else '❌ No'} |",
        f"| Overall score (1–6)   | **{result.overall_score}** |",
        f"| Experiment checks     | {len(result.experiment_checks)} |",
        f"| Citation checks       | {len(result.citation_checks)} |",
        f"| Fabricated experiments | {'🚨 yes' if result.has_fabricated_experiments else 'no'} |",
        f"| Fabricated citations   | {'🚨 yes' if result.has_fabricated_citations else 'no'} |",
        "",
    ]

    # Experiment authenticity summary
    if result.experiment_checks:
        es = result.experiment_summary
        lines += [
            "### Experiment authenticity breakdown",
            "",
            f"- verified:           {es.get('verified', 0)}",
            f"- partially_verified: {es.get('partially_verified', 0)}",
            f"- unverifiable:       {es.get('unverifiable', 0)}",
            f"- contradicted:       {es.get('contradicted', 0)}",
            f"- fabricated:         {es.get('fabricated', 0)}",
            "",
        ]

    if result.citation_checks:
        cs = result.citation_summary
        lines += [
            "### Citation authenticity breakdown",
            "",
            f"- verified:          {cs.get('verified', 0)}",
            f"- metadata_mismatch: {cs.get('metadata_mismatch', 0)}",
            f"- unverifiable:      {cs.get('unverifiable', 0)}",
            f"- fabricated:        {cs.get('fabricated', 0)}",
            "",
        ]

    # The filled review template — the substantive review
    lines += [
        "---",
        "",
        "# Filled Review (review_template_en.md)",
        "",
        result.filled_review_markdown or "_(empty — agent did not submit a review)_",
        "",
        "---",
        "",
        "# Appendix A — Experiment Authenticity Audit",
        "",
    ]

    if not result.experiment_checks:
        lines.append("_No experiment checks recorded._")
    else:
        for i, c in enumerate(result.experiment_checks, 1):
            icon = _EXP_ICON.get(c.status, "•")
            lines += [
                f"### {i}. {icon} {c.status.value.upper()} — {c.claim}",
                "",
            ]
            if c.notes:
                lines += [f"**Notes:** {c.notes}", ""]
            if c.evidence:
                lines.append("**Evidence:**")
                for ev in c.evidence:
                    lines.append(f"- `{ev}`")
                lines.append("")

    lines += [
        "---",
        "",
        "# Appendix B — Citation Authenticity Audit",
        "",
    ]

    if not result.citation_checks:
        lines.append("_No citation checks recorded._")
    else:
        for i, c in enumerate(result.citation_checks, 1):
            icon = _CIT_ICON.get(c.status, "•")
            lines += [
                f"### {i}. {icon} {c.status.value.upper()} — {c.reference}",
                "",
            ]
            if c.notes:
                lines += [f"**Notes:** {c.notes}", ""]
            if c.evidence:
                lines.append("**Evidence:**")
                for ev in c.evidence:
                    lines.append(f"- `{ev}`")
                lines.append("")

    if result.raw_tool_log:
        lines += [
            "---",
            "",
            "# Appendix C — Tool Call Log",
            "",
            "<details><summary>Expand</summary>",
            "",
            "```json",
            json.dumps(result.raw_tool_log, indent=2),
            "```",
            "</details>",
            "",
        ]

    return "\n".join(lines)


def to_json(result: ReviewResult) -> str:
    data = {
        "paper":     str(result.review_input.paper_path),
        "workspace": str(result.review_input.work_dir),
        "template":  str(result.review_input.template_path),
        "desk_rejection_pass": result.desk_rejection_pass,
        "overall_score":       result.overall_score,
        "filled_review_markdown": result.filled_review_markdown,
        "experiment_summary": result.experiment_summary,
        "citation_summary":   result.citation_summary,
        "has_fabricated_experiments": result.has_fabricated_experiments,
        "has_fabricated_citations":   result.has_fabricated_citations,
        "experiment_checks": [
            {
                "claim":    c.claim,
                "status":   c.status.value,
                "evidence": list(c.evidence),
                "notes":    c.notes,
            }
            for c in result.experiment_checks
        ],
        "citation_checks": [
            {
                "reference": c.reference,
                "status":    c.status.value,
                "evidence":  list(c.evidence),
                "notes":     c.notes,
            }
            for c in result.citation_checks
        ],
    }
    return json.dumps(data, indent=2)
