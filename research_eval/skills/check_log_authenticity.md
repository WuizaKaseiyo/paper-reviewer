# check_log_authenticity

Inspect training / evaluation logs to confirm they were produced by real runs (not handcrafted by an LLM after the fact).

## Parameters

- `log_glob`: glob for log files (default: `**/*.{log,out,txt}`)

## Workflow

1. **Find the logs**
   ```
   list_files(log_glob)
   run_command('ls -la <dir>')          # timestamps + file sizes
   ```

2. **Real-log fingerprints** — for each candidate file, check for these markers using `read_file_lines` or `search_in_files`:
   - Library banner strings: `torch.__version__`, `transformers/4.`, `cuda`, `nvidia-smi`, `GPU 0`.
   - Timestamps with high resolution: lines like `[2025-04-12 13:24:07,331]` or epoch + ms.
   - Stochastic, irregular content: warning lines, deprecation notices, OOM retries, `tqdm` progress bars (carriage returns), per-batch losses with realistic noise.
   - Output file paths that match the OS / cluster (e.g. `/home/USER/`, `/scratch/`, `slurm_job_<id>`).

3. **Anti-fingerprints (fabrication signals)**
   - Suspiciously clean monotone training curves with no noise or fluctuation.
   - All timestamps identical or stepping by exactly N minutes.
   - No traceback / warning / deprecation lines anywhere.
   - Numbers in the log perfectly match the paper to 4+ decimals across many seeds (real seeds rarely produce identical leading digits).
   - Log file mtime is *after* the paper PDF mtime.

4. **Timeline cross-check**
   - `run_command('git log --pretty=format:"%h %ai %s" --all')` to get commit timestamps.
   - Compare: results files must be newer than the relevant code commit, older than the paper compilation.

5. **Output**
   For each major log file, classify:
   - real         — multiple positive fingerprints + plausible noise
   - synthetic    — multiple anti-fingerprints
   - inconclusive — neither a strong signal
   Provide the strongest 2–3 evidence lines per file.
