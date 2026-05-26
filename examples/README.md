# Examples

## Reviewing a paper

```bash
# 1) Put the paper PDF somewhere you can reference:
cp ~/Downloads/some_paper.pdf ./paper.pdf

# 2) Point --workspace at the directory the paper claims to be backed by
#    (code, configs, training logs, result CSVs, notebook outputs, etc.):

research-eval review \
    --paper      ./paper.pdf \
    --workspace  ./my_research_project \
    --output     review.md \
    --config     ../api-key.md
```

The agent will:

1. Read the paper with `read_paper(mode='overview')`, then page through sections.
2. Map `./my_research_project` and find logs, configs, results.
3. For each table number and key claim — search the workspace for that value.
4. For each citation — search the web and confirm it exists.
5. Submit the filled review template + authenticity audit.

The output `review.md` contains:

- The filled review template (Parts I–VI of `review_template_en.md`)
- **Appendix A** — per-experiment authenticity verdicts with evidence file paths
- **Appendix B** — per-citation authenticity verdicts with URLs
- **Appendix C** — collapsible tool-call log

## What "workspace" means

It should be the directory containing whatever a reproducer would need.
Typical contents the reviewer looks for:

- `*.py` — source code
- `requirements.txt` / `pyproject.toml` / `environment.yml`
- `configs/` or `*.yaml` / `*.json` — experimental configurations
- `logs/`, `runs/`, `wandb/`, `tb_logs/` — training/evaluation logs
- `results/`, `outputs/`, `*.csv`, `*.json` — final metrics
- `notebooks/*.ipynb` — analyses with cached outputs
- `figs/`, `figures/`, `assets/` — figure source files

Empty / mostly-empty workspaces will produce many `unverifiable` audit
entries — that's the signal that the paper isn't reproducibly backed.

## Inspecting just the citations

If you only care about citation authenticity (e.g. quick screen of a paper
without the supporting workspace), point `--workspace` at an empty directory
and pass extra context telling the reviewer to focus on Part III + citations:

```bash
mkdir -p /tmp/empty
research-eval review \
    --paper ./paper.pdf --workspace /tmp/empty \
    --extra-context "Focus on the bibliography. Mark every experimental claim as 'unverifiable' (we don't have the workspace). Spend turn budget on citation verification." \
    --output citation_check.md --config ../api-key.md
```
