"""Load research-eval credentials and model settings from a local config file.

The config file is kept OUTSIDE the repo (it is listed in .gitignore) so
credentials are never accidentally committed.

File format  (any plain text or markdown file, e.g. api-key.md):
────────────────────────────────────────────────────────
  api key  = sk-...
  model    = gemini-3-flash-preview
  base url = https://app.ppapi.ai/v1    # required for proxies
  provider = openai                     # optional; auto-detected from model
────────────────────────────────────────────────────────

Parsing rules:
  - Lines starting with # are comments.
  - Key names are case-insensitive; spaces/hyphens are normalised.
  - Markdown formatting characters (**bold**, `code`) are stripped from values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_MODEL_ROUTES: list[tuple[str, str, str | None]] = [
    ("deepseek",   "openai",  "https://api.deepseek.com"),
    ("qwen",       "openai",  "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    ("gpt-",       "openai",  None),
    ("o1-",        "openai",  None),
    ("o3-",        "openai",  None),
    ("claude",     "anthropic", None),
    ("gemini",     "openai",  None),
    ("llama",      "openai",  None),
    ("mistral",    "openai",  None),
    ("mixtral",    "openai",  None),
]


def _detect_provider(model: str) -> tuple[str, str | None]:
    lower = model.lower()
    for fragment, provider, base_url in _MODEL_ROUTES:
        if fragment in lower:
            return provider, base_url
    return "openai", None


@dataclass
class EvalConfig:
    api_key: str = ""
    model: str = ""
    provider: str = ""
    base_url: str = ""

    def resolve(self) -> "EvalConfig":
        if self.model and (not self.provider or not self.base_url):
            detected_provider, detected_url = _detect_provider(self.model)
            if not self.provider:
                self.provider = detected_provider
            if not self.base_url and detected_url:
                self.base_url = detected_url
        if not self.provider:
            self.provider = "anthropic"
        return self

    def __repr__(self) -> str:
        masked = self.api_key[:8] + "…" if self.api_key else "(not set)"
        return (
            f"EvalConfig(model={self.model!r}, provider={self.provider!r}, "
            f"base_url={self.base_url!r}, api_key={masked})"
        )


_STRIP_MD  = re.compile(r"[`*_]")
_KV_RE     = re.compile(r"^(.+?)\s*[=:]\s*(.*)$")
_KEY_NORM  = re.compile(r"[\s\-_]+")

_KEY_ALIASES: dict[str, str] = {
    "api key":  "api_key",
    "apikey":   "api_key",
    "key":      "api_key",
    "model":    "model",
    "provider": "provider",
    "base url": "base_url",
    "baseurl":  "base_url",
    "base":     "base_url",
    "endpoint": "base_url",
}


def _norm_key(raw: str) -> str:
    return _KEY_NORM.sub(" ", _STRIP_MD.sub("", raw).strip().lower())


def _norm_value(raw: str) -> str:
    return _STRIP_MD.sub("", raw).strip()


def parse_config(text: str) -> EvalConfig:
    cfg = EvalConfig()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _KV_RE.match(line)
        if not m:
            continue
        field = _KEY_ALIASES.get(_norm_key(m.group(1)))
        value = _norm_value(m.group(2))
        if field and value:
            setattr(cfg, field, value)
    return cfg.resolve()


def load_config(path: Path) -> EvalConfig:
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Copy the template and fill in your credentials:\n"
            "  cp api-key.example.md api-key.md"
        )
    return parse_config(path.read_text(encoding="utf-8"))
