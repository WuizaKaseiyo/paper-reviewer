# research-eval — API key config template
#
# 1. Copy this file:  cp api-key.example.md api-key.md
# 2. Fill in your credentials below
# 3. api-key.md is listed in .gitignore — it will never be committed
#
# Lines starting with # are comments.
# Keys are case-insensitive; spaces/hyphens in key names are ignored.

api key  = YOUR_API_KEY_HERE
model    = YOUR_MODEL_NAME_HERE

# base url is required for third-party proxies and custom endpoints.
# It is auto-detected for DeepSeek and Qwen (official endpoints).
# For everything else, set it explicitly:
#
# base url = https://app.ppapi.ai/v1

# provider is auto-detected from the model name in most cases.
# Set it explicitly only if auto-detection is wrong:
#
# provider = openai     # or: anthropic


# ── Common setups ──────────────────────────────────────────────────────────

# Anthropic Claude  (official) — best default for paper review
#   api key  = sk-ant-...
#   model    = claude-opus-4-7
#   provider = anthropic

# OpenAI  (official)
#   api key  = sk-...
#   model    = gpt-4o
#   (base url not needed)

# OpenRouter  (pay-per-token, many models)
#   api key  = sk-or-v1-...
#   model    = google/gemini-2.5-pro
#   base url = https://openrouter.ai/api/v1

# DeepSeek  (official)
#   api key  = sk-...
#   model    = deepseek-chat

# Qwen / DashScope  (official)
#   api key  = sk-...
#   model    = qwen-plus


# ── Tool-specific env vars (set in your shell, not here) ───────────────────
#
# TAVILY_API_KEY      — web_search (Tavily); built-in fallback key exists.
# OPENROUTER_API_KEY  — vision_inspect / video_understand (Gemini via OpenRouter).
# GEMINI_MODEL        — override Gemini model slug (default: google/gemini-3-pro-preview)
