"""Data models shared across the research-eval package."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ExperimentStatus(str, Enum):
    VERIFIED            = "verified"
    PARTIALLY_VERIFIED  = "partially_verified"
    UNVERIFIABLE        = "unverifiable"
    CONTRADICTED        = "contradicted"
    FABRICATED          = "fabricated"


class CitationStatus(str, Enum):
    VERIFIED          = "verified"
    METADATA_MISMATCH = "metadata_mismatch"
    UNVERIFIABLE      = "unverifiable"
    FABRICATED        = "fabricated"


@dataclass(frozen=True)
class ExperimentCheck:
    claim: str
    status: ExperimentStatus
    evidence: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class CitationCheck:
    reference: str
    status: CitationStatus
    evidence: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class ReviewInput:
    work_dir: Path
    paper_path: Path
    template_path: Path
    extra_context: str = ""        # optional free-form context the user passes in


@dataclass
class ReviewResult:
    review_input: ReviewInput
    filled_review_markdown: str = ""
    desk_rejection_pass: bool = False
    overall_score: int = 0
    experiment_checks: list[ExperimentCheck] = field(default_factory=list)
    citation_checks:  list[CitationCheck]   = field(default_factory=list)
    raw_tool_log: list[dict] = field(default_factory=list)

    @property
    def experiment_summary(self) -> dict[str, int]:
        out: dict[str, int] = {s.value: 0 for s in ExperimentStatus}
        for c in self.experiment_checks:
            out[c.status.value] = out.get(c.status.value, 0) + 1
        return out

    @property
    def citation_summary(self) -> dict[str, int]:
        out: dict[str, int] = {s.value: 0 for s in CitationStatus}
        for c in self.citation_checks:
            out[c.status.value] = out.get(c.status.value, 0) + 1
        return out

    @property
    def has_fabricated_citations(self) -> bool:
        return any(c.status == CitationStatus.FABRICATED for c in self.citation_checks)

    @property
    def has_fabricated_experiments(self) -> bool:
        return any(c.status == ExperimentStatus.FABRICATED for c in self.experiment_checks)
