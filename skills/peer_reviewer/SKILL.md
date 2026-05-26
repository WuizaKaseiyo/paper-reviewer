---
name: peer_reviewer
description: Pipeline matching key for AutoResearch Stage 9. Aliases to research-eval-review.
autoload: false
---

# peer_reviewer (alias skill)

This skill exists primarily as a **pipeline matching key** for AutoResearch's
`pipeline_engine.py`, which looks up `Stage 9` (Self-Review) producer via the
exact string `"peer_reviewer"`:

```python
STAGES[8] = {"id": 9, "skill": "peer_reviewer", "name": "Self-Review"}
```

The actual methodology lives in **`research-eval-review`** (which is autoloaded
into the system prompt) and is implemented by the `research_eval/` engine. This
file exists so the `skills/` folder structure matches `profile.yaml.skills[0]`
per Talent Market template convention ("skills list corresponding to folder names").

## When this skill activates

Whenever OMC's pipeline engine dispatches a Stage 9 task with skill key
`peer_reviewer`. No additional behavior beyond what `research-eval-review`
already specifies: run the agentic review + experiment/citation authenticity audit
and submit the filled review template.

## See also

- `skills/research-eval-review/SKILL.md` — the full 7-step review + audit workflow (autoloaded)
- `tools/research-eval/TOOL.md` — the engine that backs this talent
