"""research_eval — agentic LLM reviewer for research papers + workspaces.

Given a paper (PDF / markdown) and the workspace that produced it, the agent
verifies experimental claims against actual workspace artifacts, checks for
fabricated citations, and emits a filled paper-review template.
"""
from __future__ import annotations

__version__ = "0.1.0"
