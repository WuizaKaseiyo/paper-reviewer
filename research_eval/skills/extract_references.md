# extract_references

Pull the full reference / bibliography list out of the paper, parse each entry into structured form, and produce a numbered list ready for citation verification.

## Parameters

- `min_year`: (optional) only return references from this year onward
- `focus_section`: (optional) restrict to refs cited in a specific section, e.g. "Related Work" or "Experiments"

## Workflow

1. `read_paper(mode='search', query='^References$|^Bibliography$|^\\[1\\]')` to locate the start of the bibliography. Note the chunk index.

2. `read_paper(mode='page', chunk_index=N, context=4)` to retrieve the full reference list across consecutive chunks. Keep paging until you no longer see numbered entries.

3. For each reference, extract:
   - bracketed/superscript number (e.g. `[12]` or just sequence)
   - first author surname
   - paper title (often in italics or between quotes)
   - venue / journal / arXiv ID
   - year

4. If the paper uses `\cite{key}` style instead of bracketed numbers, also `read_paper(mode='search', query='\\\\cite\\{')` and resolve keys to bib entries when possible.

5. If `focus_section` is given: `read_paper(mode='search', query=focus_section)` to find the body section, then list which `[k]` markers appear in that section.

6. Return:
   - Total reference count
   - A numbered list, one per line: `[k] FirstAuthor et al., "Title," Venue, Year.`
   - A note flagging any entry where title/authors/year could not be parsed.

7. Hand off the load-bearing entries (e.g. those cited >2 times, or backing novelty claims) to `verify_citation` next.
