# check_directory_tree

Verify that a workspace directory has the expected structure for the kind of research described in the paper — code, configs, data, results, logs.

## Parameters

- `root`: directory to inspect (default `.`)
- `required_dirs`: (optional) list of subdirectories expected
- `required_files`: (optional) list of files expected

## Workflow

1. Map the tree:
   ```
   run_command('find {root} -maxdepth 4 -not -path "*/.git/*" | sort | head -120')
   ```

2. For each `required_dirs`:
   ```
   run_command('[ -d "{root}/{dir}" ] && echo "EXISTS: {dir}" || echo "MISSING: {dir}"')
   ```

3. For each `required_files`:
   ```
   run_command('[ -f "{root}/{file}" ] && echo "EXISTS: {file}" || echo "MISSING: {file}"')
   ```

4. Categorise by extension:
   ```python
   from pathlib import Path
   root = Path("{root}")
   by_ext = {}
   for f in root.rglob("*"):
       if f.is_file() and "/.git/" not in str(f):
           by_ext[f.suffix] = by_ext.get(f.suffix, 0) + 1
   print(by_ext)
   ```

5. Report: tree, found/missing required paths, count by extension. Flag presence/absence of:
   - source code (.py / .cpp / .rs / .ts)
   - configs (.yaml/.json/.toml)
   - logs (.log/.out/.txt)
   - data (.csv/.parquet/.npz)
   - notebooks (.ipynb)
   - README / docs
