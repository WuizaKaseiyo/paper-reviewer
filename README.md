# Research Eval

一个 **agentic LLM 评审员**:既给论文打分,又**审计论文是不是真的** —— 把论文跟它对应的
workspace(代码/配置/日志/结果)摆在一起,逐条核实实验数字和引用的真实性。

> **Talent Market compliant** — 按 [1mancompany/talent-template](https://github.com/1mancompany/talent-template) v1 打包,
> 可作为 **AutoResearch / OneManCompany 流水线 Stage 9(Peer Review / Self-Review)** 的 talent 直接 hire;
> 同时保留 standalone CLI(`research-eval review ...`),不依赖 OMC 也能单独跑。
>
> **Engine-backed talent**:不同于纯技能 talent,它自带真正的 agentic 引擎(`research_eval/`)——
> 有自己的工具循环和 LLM 后端(Anthropic / OpenAI-compatible)。

给定 **一篇论文**(PDF 或 markdown)+ **该论文对应的 workspace**,research-eval 会自动:

1. **桌面拒稿筛查(Desk Rejection)**:篇幅、主题、必备章节、prompt injection / 隐藏指令。
2. **实验真实性审计**:论文里每一个关键数字(Table、Figure、headline),到 workspace 里 grep / read / python_eval,看能否在真实日志/结果文件里找到。找不到 → 标 `fabricated`。
3. **引用真实性审计**:抽出参考文献列表,逐条 web search + web fetch,确认文献真实存在、作者/年份/会议匹配。找不到 → 标 `fabricated`。
4. **填写评审模板**:把 `review_template_en.md` 的 Part I–VI 全部按结构填好。

---

## 作为 OMC talent 使用(hire)

在 OMC 前端 **Talent Market → Add Talent**,粘贴本仓库地址即可。OMC 会 `git clone` 本仓库、
`execute_hire()` 建员工目录、注入 `prompts/talent_persona.md` + autoload 的
`skills/research-eval-review/SKILL.md`,并安装 `requirements.txt` 里的引擎依赖。

### Stage 9 dispatch

`profile.yaml.skills` 含精确字符串 `peer_reviewer`(下划线),OMC 的
`pipeline_engine._find_employee_by_skill("peer_reviewer")` 据此把 Stage 9 路由给本 talent。
**不要重命名 `peer_reviewer`**,否则 Stage 9 不会自动路由。`skills/peer_reviewer/SKILL.md`
是个薄别名,真正的方法论在 `skills/research-eval-review/SKILL.md`,由 `research_eval/` 引擎实现。

### 必须设置

| Key | 必填 | 用途 |
|-----|------|------|
| `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY` | **二选一** | 评审用的 LLM(默认 Claude,长上下文论文评审最佳) |
| `TAVILY_API_KEY` | 可选 | `web_search` 核对引用(内置 dev-tier fallback) |
| `OPENROUTER_API_KEY` | 可选 | 仅 `vision_inspect` / `video_understand` 需要 |

详见 `manifest.json` 的设置项。

---

## standalone CLI

### 安装

```bash
pip install -e .          # Python ≥ 3.10
# 可选:
pip install -e ".[vision]" && playwright install chromium
cp api-key.example.md api-key.md   # 填 model / api key / base url
```

### 最小命令

```bash
research-eval review \
    --paper      ./paper.pdf \
    --workspace  ./my_project \
    --config     api-key.md \
    --output     review.md
```

### 输入 (Inputs)

| 参数 | 必填 | 含义 |
|---|---|---|
| `--paper FILE`        | ✅ | 论文文件路径(`.pdf` 或 `.md`)。PDF 用 pypdf 解析。 |
| `--workspace DIR`     | ✅ | **论文对应的代码/数据目录**(详见下方"连接 workspace")。 |
| `--template FILE`     | 可选 | 评审模板路径,默认包内 `review_template_en.md`。 |
| `--extra-context TEXT`| 可选 | 给评审员的额外说明(投稿会议、关注重点等)。 |
| `--skills-dir DIR`    | 可选 | 额外 skill `.md` 目录(可重复),注入自定义工作流。 |
| `--config FILE`       | 推荐 | API key + 模型配置(`api-key.md`)。 |
| `--provider/--model/--base-url/--api-key` | 可选 | 显式覆盖配置文件字段。 |
| `--output FILE`       | 可选 | 报告输出路径,默认 stdout。 |
| `--output-format`     | 可选 | `markdown`(默认)或 `json`。 |

### 输出 (Outputs)

**退出码**:`0` = 筛查通过且无虚构;`1` = 桌面筛查失败 / 发现虚构实验或引用 / 运行错误。
可直接做 CI 门禁:`research-eval review ... && echo PASS`。

**Markdown 报告**结构:

```
# Research Review Report
## Inputs                       ← 评审对象(论文 / workspace / 模板)
## Headline Verdict             ← 一表概览(桌面筛查 / 总分 / 实验·引用 check 数 / 是否有虚构)
  ### Experiment authenticity breakdown
  ### Citation authenticity breakdown
---
# Filled Review                 ← 模板 Part I–VI 全部填好
---
# Appendix A — Experiment Authenticity Audit   ← 每条实验声称的 status + workspace file:line 证据
# Appendix B — Citation Authenticity Audit     ← 每条引用的 status + URL/arXiv 证据
# Appendix C — Tool Call Log                    ← 可折叠工具调用 trace
```

`--output-format json` 给机读结构(字段一一对应)。评审过程的工具调用会实时打到 stderr。

---

## 连接 workspace

这是 research-eval 跟普通"评审 prompt"最大的区别 —— 它会**真的去你的 workspace 翻代码、跑脚本、读日志**。
`--workspace` 应指向**生成这篇论文的代码/数据目录**,最低限度有用的结构:

```
my_project/
├── README.md          ← agent 第一站
├── *.py               ← 训练 / 评估脚本
├── requirements.txt   ← 或 pyproject.toml / environment.yml
├── configs/           ← *.yaml/*.json 实验配置(含 seed、超参)
├── logs/              ← *.log/*.out 训练日志
└── results/           ← *.csv/*.json 最终指标
```

三种典型场景:

- **A 完整代码+日志**(推荐):完整审计 —— 实验数字、引用、代码是否真存在、日志像不像真的。
- **B 只有代码、没日志**:大量 `unverifiable`,报告会把"数字无法独立验证"写进 Weaknesses。
- **C 只审引用**:给空目录当 workspace +`--extra-context` 指示"把实验声称全标 unverifiable,预算花在引用核实"。

**安全**:`read_file`/`write_file`/`run_command` 都被 sandbox 在 workspace 内(`relative_to` 防穿越);
`run_command`/`python_eval` 有 60s 超时;`http_request` 屏蔽云元数据端点。

### 注入自定义 skill

写个 markdown(workflow 写在里面),用 `--skills-dir ./my_skills` 传给 CLI;agent 通过
`invoke_skill` 调用。参考 `research_eval/skills/*.md` 里现有的 9 个写法。

---

## 内置 skills(9)

| Skill | 用途 |
|---|---|
| `desk_rejection_screen`  | Part I:篇幅 / 主题 / 必备章节 / prompt injection |
| `extract_references`     | 从论文抽出结构化参考文献列表 |
| `verify_citation`        | 单条引用 web 验证(verified / metadata_mismatch / unverifiable / fabricated) |
| `verify_experiment_runs` | 单个实验声称对 workspace 做证据匹配 |
| `cross_check_numbers`    | 批量抽论文里所有数字,到 workspace 全文 grep |
| `check_log_authenticity` | 训练日志像不像真的(时间戳、噪声、warning 痕迹) |
| `check_code_executes`    | 论文提到的类名/方法名是否在代码里真存在 + import smoke |
| `missing_related_work`   | Part III:用 web search 找应引而漏掉的工作 |
| `check_directory_tree`   | 检查 workspace 结构是否完整 |

---

## 仓库结构

```
research-eval/  (repo: paper-reviewer)
├── profile.yaml                       # Talent 身份(skills 含 'peer_reviewer' 流水线匹配键)
├── manifest.json                      # 前端设置 UI(API keys / 审计行为)
├── DESCRIPTION.md                     # Talent Market 展示文案
├── prompts/talent_persona.md          # 人格 + 行为契约
├── vessel/vessel.yaml                 # 每-talent 超时(3600s)+ 迭代(200)+ sandbox
├── skills/
│   ├── research-eval-review/SKILL.md  # 7 步评审+审计工作流(autoload)
│   └── peer_reviewer/SKILL.md         # Stage 9 流水线匹配键别名
├── tools/research-eval/
│   ├── TOOL.md                        # 引擎/CLI 声明(talent-template tools/ 约定)
│   └── run.sh                         # `python -m research_eval` 薄包装
├── research_eval/                     # ★ agentic 引擎(真正的实现)
│   ├── cli.py / __main__.py           # CLI 入口
│   ├── evaluator.py                   # agentic 评审主循环(_MAX_TURNS=200)
│   ├── backends.py                    # Anthropic / OpenAI-compatible 后端
│   ├── tools.py / extra_tools.py      # ~16 个工具(paper/workspace/web/vision)
│   ├── models.py / report.py / config.py
│   ├── review_template_en.md          # 包内模板副本
│   └── skills/*.md                    # 9 个引擎 workflow
├── review_template_en.md              # 仓库根模板
├── examples/README.md                 # 快速上手
├── api-key.example.md                 # 凭证模板(复制成 api-key.md)
├── pyproject.toml / requirements.txt
├── avatar.jpg
├── README.md
└── LICENSE                            # TMAL v1.0
```

---

## License

[Talent Market Attribution License (TMAL) v1.0](./LICENSE)。

---

## Citation

> **DO NOT REMOVE** — required by the [Talent Market Attribution License](./LICENSE).

This talent was built using the [Talent Market](https://one-man-company.com) template by [Zhengxu Yu](mailto:yuzxfred@gmail.com) / [1mancompany](https://github.com/1mancompany).

```bibtex
@software{talentmarket,
  title  = {Talent Market - AI Agent Marketplace},
  author = {Zhengxu Yu},
  email  = {yuzxfred@gmail.com},
  url    = {https://one-man-company.com},
  year   = {2026}
}
```

If you publish or deploy a talent based on this template, please keep this section intact in your README or equivalent documentation.
