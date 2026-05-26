"""LLM provider backends.

Both backends expose the same interface so the review loop in evaluator.py
is completely provider-agnostic:

    backend.chat(messages, system, tools) -> TurnResult
    backend.batch_tool_result_message(results) -> message(s) to append
"""
from __future__ import annotations

import json
import os


class ToolCall:
    __slots__ = ("id", "name", "input")

    def __init__(self, id: str, name: str, input: dict) -> None:
        self.id = id
        self.name = name
        self.input = input


class TurnResult:
    __slots__ = ("assistant_messages", "tool_calls", "stop_reason")

    def __init__(
        self,
        assistant_messages: list[dict],
        tool_calls: list[ToolCall],
        stop_reason: str,
    ) -> None:
        self.assistant_messages = assistant_messages
        self.tool_calls = tool_calls
        self.stop_reason = stop_reason


class AnthropicBackend:
    """Uses the Anthropic Python SDK."""

    def __init__(
        self,
        model: str,
        max_tokens: int = 8192,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        import anthropic as _sdk

        self.model = model
        self.max_tokens = max_tokens

        resolved_key   = api_key or os.environ.get("ANTHROPIC_API_KEY")
        auth_token     = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        resolved_url   = base_url or os.environ.get("ANTHROPIC_BASE_URL")

        kwargs: dict = {}
        if resolved_url:
            kwargs["base_url"] = resolved_url

        if resolved_key:
            self._client = _sdk.Anthropic(api_key=resolved_key, **kwargs)
        elif auth_token:
            self._client = _sdk.Anthropic(auth_token=auth_token, **kwargs)
        else:
            raise RuntimeError(
                "Anthropic backend: set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN."
            )

    def chat(self, messages: list[dict], system: str, tools: list[dict]) -> TurnResult:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        )

        content_blocks: list[dict] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content_blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content_blocks.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))

        stop_reason = "tool_use" if response.stop_reason == "tool_use" else "end_turn"
        return TurnResult(
            assistant_messages=[{"role": "assistant", "content": content_blocks}],
            tool_calls=tool_calls,
            stop_reason=stop_reason,
        )

    def batch_tool_result_message(self, results: list[tuple[str, str]]) -> dict:
        return {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tid, "content": content}
                for tid, content in results
            ],
        }


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


def _normalize_model_for_openrouter(model: str, base_url: str | None) -> str:
    if not base_url or "openrouter" not in base_url:
        return model
    if "/" in model:
        return model

    prefixes = {
        "gemini":  "google",
        "llama":   "meta-llama",
        "mistral": "mistralai",
        "mixtral": "mistralai",
        "qwen":    "qwen",
    }
    lower = model.lower()
    for fragment, org in prefixes.items():
        if lower.startswith(fragment):
            return f"{org}/{model}"
    return model


class OpenAIBackend:
    def __init__(
        self,
        model: str,
        max_tokens: int = 8192,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI as _SDK

        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        resolved_url = base_url or os.environ.get("OPENAI_BASE_URL")

        if not resolved_key:
            raise RuntimeError(
                "OpenAI backend: set OPENAI_API_KEY or pass --api-key."
            )

        self.model = _normalize_model_for_openrouter(model, resolved_url)
        self.max_tokens = max_tokens

        kwargs: dict = {"api_key": resolved_key}
        if resolved_url:
            kwargs["base_url"] = resolved_url
        if resolved_url and "openrouter" in resolved_url:
            kwargs["default_headers"] = {
                "HTTP-Referer": "https://github.com/research-eval",
                "X-Title": "research-eval",
            }

        self._client = _SDK(**kwargs)

    def chat(self, messages: list[dict], system: str, tools: list[dict]) -> TurnResult:
        full_messages = [{"role": "system", "content": system}] + messages

        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tools=_to_openai_tools(tools),
            tool_choice="auto",
            messages=full_messages,
        )

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        content_blocks: list[dict] = []
        tool_calls: list[ToolCall] = []

        if msg.content:
            content_blocks.append({"type": "text", "text": msg.content})

        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"raw": tc.function.arguments}
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": args,
                })
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, input=args))

        assistant_msg: dict = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]

        stop_reason = "tool_use" if finish_reason == "tool_calls" else "end_turn"
        return TurnResult(
            assistant_messages=[assistant_msg],
            tool_calls=tool_calls,
            stop_reason=stop_reason,
        )

    def batch_tool_result_message(self, results: list[tuple[str, str]]) -> list[dict]:
        return [
            {"role": "tool", "tool_call_id": tid, "content": content}
            for tid, content in results
        ]


_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai":    "gpt-4o",
}


def build_backend(
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    max_tokens: int = 8192,
) -> AnthropicBackend | OpenAIBackend:
    resolved_model = model or _DEFAULT_MODELS.get(provider, "gpt-4o")

    if provider == "anthropic":
        return AnthropicBackend(
            model=resolved_model,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=base_url,
        )
    if provider == "openai":
        return OpenAIBackend(
            model=resolved_model,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=base_url,
        )
    raise ValueError(f"Unknown provider: {provider!r}. Use 'anthropic' or 'openai'.")
