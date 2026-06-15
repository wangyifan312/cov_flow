# cov_flow 项目目录结构

## 总览

```
cov_flow/
├── dv_mcp/          — MCP Server（26 个查询工具）
├── lib/             — 共享 Python 库
├── scripts/         — 离线 CLI 脚本（索引构建、验证、仿真）
├── schemas/         — JSON Schema 定义
├── skills/          — Claude Code Skill 定义（5 个）
├── mock_data/       — 示例项目数据（测试用）
├── docs/            — 用户文档
├── examples/        — 使用示例 walkthrough
├── evals/           — Eval 测试用例
├── tests/           — 测试套件（686 tests）
└── 根目录文件
```

---

## `dv_mcp/` — MCP Server

Claude Code 通过 MCP 协议调用的 **26 个查询工具**，是 Agent 与项目数据交互的唯一接口。

```
dv_mcp/
├── __init__.py
└── dv_context_server/
    ├── server.py              — FastMCP 服务器入口，注册 26 个工具
    ├── config.py              — 服务器配置
    ├── tools/                 — 工具实现（按领域分组）
    │   ├── coverage_tools.py  — 4 个：cov_list_uncovered, cov_get_gap_detail,
    │   │                        cov_get_coverpoint_source, cov_get_hit_history
    │   ├── spec_tools.py      — 2 个：spec_search, spec_get_section
    │   ├── register_tools.py  — 4 个：reg_find_field, reg_find_fields_affecting_feature,
    │   │                        reg_search_by_description, reg_get_ral_path
    │   ├── tb_tools.py        — 7 个：tb_get_existing_tests_for_feature, tb_find_tests_for_gap,
    │   │                        tb_read_source, tb_find_sequence, tb_get_base_test_template,
    │   │                        tb_find_config_knob, tb_get_sequence_source_snippet
    │   ├── rtl_tools.py       — 4 个：rtl_find_signal, rtl_get_instance_info,
    │   │                        rtl_get_source_snippet, rtl_trace_fanin
    │   └── sim_tools.py       — 5 个：sim_run_targeted_test, sim_get_test_result,
    │                            sim_search_log, cov_get_coverage_diff, wave_check_condition
    ├── services/              — 横切服务
    │   ├── project_loader.py  — 项目加载（manifest → Manifest 对象）
    │   ├── summarizer.py      — 信封格式（envelope/error_envelope/truncate_list）
    │   ├── evidence.py        — 证据封装
    │   └── audit.py           — 审计日志
    └── indexes/
        └── readers.py         — 索引文件读取器（IndexReader）
```

**作用**：Agent 需要查看 coverage gap、查 spec、读 RTL 源码、跑仿真时，都通过这里。所有工具返回统一的信封格式 `{ok, tool, project, result, evidence, truncated, audit}`。

---

## `lib/` — 共享 Python 库

被 MCP tools 和 scripts 共同依赖的核心库。

```
lib/
├── manifest.py            — Manifest 类：加载/解析 project_manifest.yaml
├── project_registry.py    — 项目注册表：project name → manifest path
├── source_resolver.py     — 源码片段读取（安全边界：路径遍历防护、max_lines/max_bytes）
├── sim_executor.py        — 仿真执行器：subprocess 执行 compile/run/urg（安全：test name 验证、shell=False）
├── sim_log_parser.py      — VCS/UVM 日志解析：pass/fail 检测、UVM count 提取
├── urg_runner.py          — URG 报告生成 + 解析管线
├── coverage_diff.py       — 覆盖率 diff 计算（before/after 对比）
├── semantic_matcher.py    — 语义匹配：gap 关键词 → TB 序列搜索
├── sv_parser.py           — SystemVerilog 解析器：13 种模式提取模块/端口/信号
├── schema_validator.py    — JSON Schema 校验器
├── index_paths.py         — 索引路径常量定义
├── eda_adapters/          — EDA 工具适配器（永久 stub）
│   ├── base.py            — 抽象接口
│   ├── stub_verdi.py      — Verdi stub（waveform/signal query）
│   └── stub_vcs.py        — VCS stub（compile/simulate）
└── urg_parser/            — URG HTML 报告解析器
    ├── session.py         — session.xml 元数据
    ├── structure.py       — modlist/groups 结构映射
    ├── functional.py      — 功能覆盖率解析
    ├── code_coverage.py   — 代码覆盖率解析
    ├── gap_assembler.py   — gap ID 分配 + 路径归一化
    └── index_builder.py   — coverage_index.json 输出
```

**作用**：`dv_mcp/` 中的工具调用 `lib/` 来执行实际操作（读 manifest、解析日志、运行仿真）。`scripts/` 也依赖 `lib/` 做离线工作。

---

## `scripts/` — 离线 CLI 脚本

在 Agent 运行**之前**执行的确定性脚本，用于构建索引、验证数据、运行仿真。

```
scripts/
├── 索引构建器（6 个）
│   ├── build_coverage_index.py    — 解析 URG HTML → coverage_index.json
│   ├── build_tb_index.py          — 扫描 SV 文件 → tb_index.json
│   ├── build_rtl_index.py         — 扫描 RTL → rtl_index.json
│   ├── build_spec_index.py        — 解析 spec → spec_index.json
│   ├── build_reg_index.py         — 解析寄存器 → reg_db.json
│   └── build_sim_history_index.py — 聚合仿真历史 → sim_history.json
│
├── 验证器（5 个）
│   ├── validate_manifest.py       — 校验 project_manifest.yaml 符合 schema
│   ├── validate_coverage_gaps.py  — 校验 coverage_gaps.json
│   ├── validate_scenario_card.py  — 校验 scenario card 输出
│   ├── validate_patch_metadata.py — 校验 testcase patch 元数据
│   └── validate_feedback_report.py — 校验 feedback report
│
├── 执行器（2 个）
│   ├── sim_runner.py              — 仿真运行 CLI（--dry-run 或 real execution）
│   └── coverage_diff.py           — 覆盖率 diff CLI
│
├── 辅助工具（4 个）
│   ├── generate_mock_index.py     — 为 dma_subsystem 生成示例索引
│   ├── static_patch_check.py      — 静态检查生成的 UVM patch
│   ├── smoke_server.py            — MCP server 启动验证
│   └── run_eval.py                — Eval 测试运行器（--dry-run 模式）
```

**作用**：`make build-indexes` 调用索引构建器；`make validate` 调用验证器。Agent 不直接调用 scripts，而是通过 MCP tools 读取 scripts 生成的索引文件。

---

## `schemas/` — JSON Schema 定义

```
schemas/
├── project_manifest.schema.json   — project_manifest.yaml 的 schema
├── coverage_gap.schema.json       — coverage gap 数据结构
├── scenario_card.schema.json      — scenario card 输出格式
├── testcase_patch.schema.json     — testcase patch 输出格式
└── feedback_report.schema.json    — 仿真反馈报告格式
```

**作用**：定义项目中所有数据交换的结构。`scripts/validate_*.py` 用这些 schema 做校验。

---

## `skills/` — Claude Code Skill 定义

5 个 Skill 的工作流定义和参考文档，注册到 Claude Code 后变成 `/slash-command`。

```
skills/
├── dv-coverage-closure/           — 主 skill：端到端覆盖率闭合
│   ├── SKILL.md                   — 工作流入口
│   └── references/ (5 个)         — gap 分类、review checklist、scenario schema 等
│
├── dv-coverage-gap-triage/        — gap 分诊：分类 + 优先级
│   ├── SKILL.md
│   └── references/ (3 个)         — 优先级规则、分诊策略、不可达启发式
│
├── dv-coverage-scenario-generation/ — 场景生成：gap → scenario card
│   ├── SKILL.md
│   └── references/ (2 个)         — 协议模板（AXI/AHB/APB）、场景模式
│
├── dv-testcase-generation/        — 测试用例生成：scenario → UVM patch
│   ├── SKILL.md
│   └── references/ (3 个)         — UVM 生成规则、patch 规则、编译检查
│
└── dv-simulation-feedback/        — 仿真反馈：分析 sim 结果 + coverage diff
    ├── SKILL.md
    └── references/ (2 个)         — diff 规则、日志分析规则
```

**作用**：用户输入 `/dv-coverage-closure` 等命令时，Claude Code 加载对应的 SKILL.md 和 references，按照定义的工作流调用 MCP tools 完成任务。

---

## `mock_data/` — 示例项目数据

两个示例验证项目，用于测试和演示。

```
mock_data/
├── dma_subsystem/                 — 全合成的 DMA 子系统（27 个 gap）
│   ├── project_manifest.yaml      — 项目 manifest
│   ├── .dv_ai_index/              — 预构建索引（coverage/spec/reg/rtl/tb/sim_history）
│   ├── rtl/ (7 .sv)               — 示例 RTL 源码
│   ├── spec/ (dma_fs.md)          — 示例功能规格
│   ├── registers/ (dma_regs.yaml) — 示例寄存器定义
│   ├── tb/ (sequences/, env/)     — 示例 UVM TB
│   ├── coverage/ (model + urg)    — 覆盖率模型
│   ├── sim_data/                  — 测试 fixture 数据
│   └── sim_results/ (14 tests)    — 预存仿真结果
│
└── axi2ahb/                       — AXI2AHB 桥接（982 个 gap，真实 URG 报告）
    ├── project_manifest.yaml
    ├── .dv_ai_index/ (coverage + tb index)
    └── urg_report/ (URG HTML)     — 真实 Synopsys VCS URG 报告（脱敏后）
```

**作用**：CI 测试用 dma_subsystem（echo 命令，无需 VCS）；端到端演示用 axi2ahb（真实 URG 报告）。接入真实项目时，在 `projects.yaml` 中注册自己的 manifest。

---

## `docs/` — 用户文档

```
docs/
├── getting_started.md             — 入门指南（clone → install → 第一次使用）
├── mcp_tool_reference.md          — 26 个 MCP 工具速查表
├── user_prompt_templates.md       — 25 个 Prompt 模板
├── server_setup_guide.md          — 服务器部署指南（VCS + Claude Code）
├── quick_start_checklist.md       — 快速部署 checklist
└── testcase_gen_generic_prompt.md — 通用用例生成 prompt
```

---

## `examples/` — 使用示例

```
examples/
├── README.md                      — 示例索引
├── triage_walkthrough.md          — gap 分诊 walkthrough
├── full_closure_walkthrough.md    — 端到端闭环 walkthrough
└── mcp_server_setup.md            — MCP 配置指南
```

---

## `evals/` — Eval 测试用例

```
evals/
├── README.md                          — Eval 框架说明
├── triage_gap_0001.yaml               — gap 分诊 eval
├── triage_code_coverage_line.yaml     — 代码覆盖率分诊
├── triage_code_coverage_fsm.yaml      — FSM 覆盖率分诊
├── scenario_gen_0001.yaml             — 场景生成 eval
├── generate_case_0001.yaml            — 用例生成 eval
└── simulation_feedback_0001.yaml      — 仿真反馈 eval
```

**作用**：6 个 eval case 覆盖 5 个 skill 的 4 种 task_mode。当前只支持 `--dry-run`，LLM 执行需要 Phase 6+ 的 eval harness。

---

## `tests/` — 测试套件

```
tests/
├── conftest.py                      — 共享 fixture
├── test_mcp_coverage_tools.py       — coverage tools 测试
├── test_mcp_spec_tools.py           — spec tools 测试
├── test_mcp_register_tools.py       — register tools 测试
├── test_mcp_tb_tools.py             — TB tools 测试
├── test_mcp_tb_tools_axi2ahb.py     — TB tools (axi2ahb) 测试
├── test_mcp_rtl_tools.py            — RTL tools 测试
├── test_mcp_rtl_tools_6b.py         — RTL tools (Phase 6B) 测试
├── test_mcp_sim_tools.py            — sim tools + wave stub 测试
├── test_sim_tools_real_mode.py      — sim tools real 模式测试
├── test_sim_executor.py             — SimExecutor 单元测试
├── test_sim_log_parser.py           — 日志解析测试
├── test_sim_runner.py               — sim_runner CLI 测试
├── test_urg_runner.py               — UrgRunner 测试
├── test_coverage_diff.py            — coverage diff 计算测试
├── test_eda_adapters.py             — EDA stub adapter 测试
├── test_source_resolver.py          — 源码读取器测试
├── test_sv_parser.py                — SV 解析器测试
├── test_semantic_matcher.py         — 语义匹配测试
├── test_project_registry.py         — 项目注册表测试
├── test_large_dataset.py            — 大数据集（axi2ahb 982 gap）测试
├── test_tool_contracts.py           — 工具信封格式契约测试
├── test_schemas.py                  — JSON Schema 测试
├── test_audit.py                    — 审计日志测试
├── test_validate_*.py (5 个)        — 各 validator 测试
├── test_build_*.py (3 个)           — 各 indexer 测试
├── test_generate_mock_index.py      — mock 索引生成测试
├── test_static_patch_check.py       — 静态检查测试
├── test_run_eval.py                 — eval runner 测试
├── test_tb_find_tests_for_gap.py    — 语义桥接测试
└── test_tb_read_source.py           — TB 源码读取测试
```

**686 tests, 18 skipped, 0 failed**

---

## 根目录文件

```
├── CLAUDE.md                — Agent 工作指令（scope、forbidden rules、testing policy）
├── README.md                — 项目入口（overview、status table、quick start）
├── implementation_plan.md   — 权威架构设计文档（1540 行，26 章节）
├── REVIEW_GUIDE.md          — Reviewer 工作标准和 checklist
├── Makefile                 — 构建/验证/测试入口命令
├── pyproject.toml           — Python 包配置和依赖
├── projects.yaml            — 项目注册表（project name → manifest path）
├── .mcp.json.example        — MCP server 配置模板
└── .mcp.json                — 本地 MCP 配置（gitignore）
```
