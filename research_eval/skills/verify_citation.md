# verify_citation

Independently verify that a citation exists in the literature and that the title / authors / venue / year match. Detect fabricated (hallucinated) references.

## Parameters

- `reference`: the citation as it appears in the paper, e.g. `Smith et al., "Foo bar baz," NeurIPS 2023`
- `expected_year`: (optional) the year the paper claims
- `expected_venue`: (optional) the venue the paper claims (e.g. "NeurIPS", "arXiv:2301.xxxxx")

## Workflow

1. Build search queries (most discriminative first):
   - `"<full title>"`  — exact phrase
   - `<first author surname> <few title keywords> <expected_year>`
   - `<first author surname> <expected_venue>`

2. `web_search(query=Q, max_results=8)` for the top 2–3 queries.

3. Inspect the returned hits:
   - **verified**: ≥1 hit has a clearly matching title and author and (if provided) year/venue. Save the canonical URL.
   - **metadata_mismatch**: paper exists but year/venue/title differs from `reference` in non-trivial ways (e.g. claims NeurIPS 2023 but it was published at ICML 2024). Note the discrepancy.
   - **unverifiable**: searches return no relevant hits but the title sounds plausible and might just be hard to index. Try one more query (e.g. arXiv search) before settling on this.
   - **fabricated**: title looks like a plausible-but-invented composition (typical LLM hallucination patterns: generic title, claimed first author who works in a different field, fabricated arXiv ID). No matches across ≥3 differently-phrased queries.

4. For 'verified' entries, optionally `web_fetch(url)` on the arXiv / OpenReview / ACL Anthology page to confirm authors and abstract match.

5. **Red flags for fabrication**:
   - The arXiv ID format is invalid (wrong year prefix, wrong number-of-digits).
   - First-author web search returns no publications anywhere near the claimed topic.
   - The exact title returns zero results on Google Scholar / Semantic Scholar.
   - Two LLM-generated refs in the same paper share suspiciously similar formulaic titles.

6. Return one citation_authenticity_check entry:
   ```
   {
     "reference": "<as in paper>",
     "status":    "verified" | "metadata_mismatch" | "unverifiable" | "fabricated",
     "evidence":  ["<URL or snippet>", ...],
     "notes":     "<one-sentence explanation>"
   }
   ```
