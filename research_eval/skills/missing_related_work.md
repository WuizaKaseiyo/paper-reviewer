# missing_related_work

Identify works that should have been cited but aren't, to populate Part III of the review template.

## Parameters

- `topic_query`: one-line description of the paper's main contribution
- `years`: (optional) year range to search, default last 5

## Workflow

1. From the paper overview, list 2–3 key topics:
   - core method (e.g. "in-context learning for code generation")
   - dataset / benchmark used
   - claimed prior SOTA

2. For each topic, `web_search(query='<topic> survey OR <topic> NeurIPS|ICML|ACL 2023 2024 2025', max_results=8)`.

3. Read the citation list already in the paper (use `extract_references` skill if not already done).

4. For each promising hit from web_search, check whether the cited paper / author appears in the existing reference list. If absent, candidate for "potentially missing related work".

5. For each candidate, capture:
   - Authors, title, year, venue
   - Why it's relevant (one sentence)
   - Suggested placement (which section of the paper)
   - How to use (background citation / baseline / future-work extension)

6. Return 0–6 entries. Quality > quantity — only list works that genuinely fill a gap. Avoid suggesting works the paper would have no reason to cite.
