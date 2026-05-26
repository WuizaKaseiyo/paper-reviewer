# cross_check_numbers

Pull every quantitative result from the paper (Tables + headline numbers) and grep the workspace to confirm each appears in real artifacts. Drives the most important fabrication detector.

## Parameters

- `table_query`: (optional) regex passed to `read_paper(mode='search')` to locate tables (default: `Table\\s+\\d|\\|.*\\|`)
- `tolerance`: (optional) relative tolerance for "is this number present?" (default: 0.001)

## Workflow

1. **Extract numbers from the paper**
   - `read_paper(mode='search', query=table_query, max_hits=20)` to locate table-bearing chunks.
   - For each hit chunk, `read_paper(mode='page', chunk_index=N)` and pull out:
     - decimal numbers ≥ 1 digit (`\d+\.\d+`)
     - percentages (`\d+(\.\d+)?\s*%`)
     - integers > 100 (counts: dataset sizes, parameter counts)
   - Also pull headline numbers from the abstract & intro.
   - Deduplicate and keep ~20–40 of the most distinctive (unique-looking) values.

2. **Search the workspace for each**
   For each value v, run:
   ```
   search_in_files(pattern=v, file_glob='**/*.{log,csv,json,txt,out,md,ipynb}')
   ```
   Try both `v` and `v` rounded to one fewer decimal place. For percentages, also try the fractional form (e.g. 87.3 ↔ 0.873).

3. **Tally**
   - matched: value appears verbatim in ≥1 log/output file.
   - rounded_match: value appears at slightly different precision.
   - missing: value is nowhere in any artifact.

4. **Sanity check the missing values**
   If a value is "missing" but the workspace has obvious metric files:
   - `python_eval` to load those files and look for the value within tolerance.
   - Look in `wandb/`, `tb_logs/`, `runs/`, `output/`, `results/`.

5. **Status**
   - Aggregate match rate `r = matched / total`.
   - `r ≥ 0.8`           → claim infrastructure is real (verified)
   - `0.3 ≤ r < 0.8`     → mixed (partially_verified) — flag missing values
   - `r < 0.3`           → strong fabrication signal (contradicted / fabricated)

6. Report the full match-list as evidence. Use this skill's output to populate multiple `experiment_authenticity_checks` entries, one per important value.
