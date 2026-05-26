# check_code_executes

Confirm that the workspace code at least imports and that key entry-points referenced in the paper are real, callable, and produce the claimed outputs when reasonable.

## Parameters

- `entry_point`: (optional) script the paper calls out (e.g. `train.py`, `eval.py`)
- `dry_run_args`: (optional) command-line args that should exit early without launching a full run

## Workflow

1. **Inventory**
   ```
   list_files('**/*.py')
   list_files('**/requirements*.txt')
   list_files('**/pyproject.toml')
   list_files('**/setup.py')
   ```

2. **Import smoke test** — for each non-trivial top-level package, run:
   ```
   python_eval('
   import importlib, sys
   for mod in ["my_pkg", "my_pkg.train", "my_pkg.model"]:
       try:
           importlib.import_module(mod)
           print(f"OK: {mod}")
       except Exception as e:
           print(f"FAIL: {mod} -> {type(e).__name__}: {e}")
   ')
   ```

3. **Help / --help / argparse check** for entry-point scripts:
   ```
   run_command('python -m <entry_point> --help')
   ```
   If the script exits 0 with a useful usage block, it's almost certainly a real entry point.

4. **AST inspection** to confirm the algorithms / classes the paper names actually exist:
   ```
   search_in_files(pattern='class .*<paper-method-name>|def .*<paper-method-name>', file_glob='**/*.py')
   ```
   If the paper introduces "FooNet" but no class FooNet exists anywhere, that's a major red flag.

5. **Smoke test** (only if `dry_run_args` provided and clearly safe — no GPU launch, no API call):
   ```
   run_command('timeout 30 python <entry_point> <dry_run_args>')
   ```

6. **Status**
   - real      — imports work + entry point exists + named classes exist
   - shell     — files exist but imports fail / entry points are missing
   - hollow    — top-level code is a thin stub with no implementation
