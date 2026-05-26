# verify_experiment_runs

Verify that experiments reported in the paper actually ran in the workspace — i.e. that the numbers, plots, and tables are backed by real training/eval artifacts, not LLM-fabricated values.

## Parameters

- `claim`: a specific quantitative claim from the paper (e.g. "Accuracy 87.3% on CIFAR-100, Table 2")
- `expected_artifacts`: (optional) hints — log file glob, csv name, notebook, etc.

## Workflow

1. **Find the experiment scaffolding**. Use:
   ```
   list_files('**/*.py')          # training / eval scripts
   list_files('**/*.{json,yaml,yml,toml}')  # configs
   list_files('**/*.{log,out,txt}')         # raw logs
   list_files('**/*.csv')         # results tables
   list_files('**/*.ipynb')       # notebook outputs
   list_files('**/wandb/**')      # wandb dumps
   list_files('**/tensorboard/**')          # tb event files
   list_files('**/checkpoints/**')          # checkpoints
   ```
   Note timestamps via `run_command('ls -la')`.

2. **Locate the specific number**. Use `search_in_files` with the exact numeric value(s) in the claim — e.g. `87.3`, `87.30`, `0.873`. Also search the metric name (e.g. `accuracy`, `f1`, `BLEU`).

3. **Cross-reference**. If the value appears, confirm:
   - The file's path/name makes sense for the claimed experiment (matches dataset, model, setting).
   - Surrounding lines show consistent context (same dataset, seed, hyperparameters as the paper).
   - The timestamp of the file is *before* the paper's submission/compilation time, *after* the relevant code commits.

4. **If the value does not appear anywhere**: this is a strong fabrication signal. Try:
   - python_eval to compute the metric from raw predictions / CSV outputs and see whether the value is reproducible.
   - search for nearby values (`87.[0-9]`) — maybe rounded differently.
   - Look for an aggregate report (`results.json`, `final_metrics.md`).

5. **Check plot / figure provenance**: if the claim is "Figure 4 shows…", check that the figure file exists (`assets/`, `figs/`, `figures/`) AND a script that produces it from real data. If only the PDF/PNG exists with no producing code or input CSV, mark as suspicious.

6. **Code-exists check**: if the paper mentions `Algorithm 1`, `our method foo`, or a specific module/class, grep for it:
   ```
   search_in_files(pattern='class FooMethod|def foo_method', file_glob='**/*.py')
   ```

7. **Status determination**:
   - `verified`            — number found in real log/output file with consistent context.
   - `partially_verified`  — number matches, but supporting context (config / seed) is missing.
   - `unverifiable`        — no log files for this experiment; can't tell either way.
   - `contradicted`        — value in workspace logs differs materially from the paper.
   - `fabricated`          — value not in any artifact; no code path produces it; figure has no input data.

8. Return one experiment_authenticity_check entry with the strongest evidence string(s).
