---
name: peer_reviewer
description: Pipeline matching key for AutoResearch Stage 9. Aliases to paper-review-workflow.
autoload: false
---

# peer_reviewer (alias skill)

This skill exists primarily as a **pipeline matching key** for AutoResearch's
`pipeline_engine.py`, which looks up `Stage 9` (Self-Review) producer via the
exact string `"peer_reviewer"`:

```python
STAGES[8] = {"id": 9, "skill": "peer_reviewer", "name": "Self-Review"}
```

The actual methodology lives in **`paper-review-workflow`** (which is autoloaded
into the system prompt). This file exists so the `skills/` folder structure
matches `profile.yaml.skills[0]` per Talent Market template convention
("skills list corresponding to folder names").

## When this skill activates

Whenever OMC's pipeline engine dispatches a Stage 9 task with skill key
`peer_reviewer`. No additional behavior beyond what `paper-review-workflow`
already specifies.

## See also

- `skills/paper-review-workflow/SKILL.md` — the full 5-phase workflow (autoloaded)
