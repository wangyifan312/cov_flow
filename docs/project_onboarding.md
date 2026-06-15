# 项目接入指南

本文档帮助你将自己的验证项目接入 cov_flow 框架。
阅读前，请确认已完成 [快速入门](getting_started.md) 的 Step 1-3（安装、Skills 注册、MCP 配置）。

---

## 你需要准备什么

### 必填项（3 项）

| # | 类别 | 需要准备什么 | 格式要求 | 用途 |
|---|------|-------------|---------|------|
| 1 | 覆盖率报告 | URG HTML 报告目录 | Synopsys VCS `urg` 命令的输出（包含 session.xml、grp*.html、mod*.html） | 解析未覆盖的 gap（功能覆盖率 + 代码覆盖率） |
| 2 | UVM 测试环境 | env / seq_lib / tests 等目录的 `.sv` 源文件 | 标准 UVM 类结构，包含 `uvm_component_utils` / `uvm_object_utils` 注册 | 构建 TB 索引，支持场景查询和代码生成 |
| 3 | 仿真命令模板 | compile / run / coverage 命令 | 含 `{test}` 和 `{seed}` 占位符，如 `make run TEST={test} SEED={seed}` | 执行定向仿真测试 |

### 可选项（5 项）

| # | 类别 | 需要准备什么 | 格式要求 | 用途 |
|---|------|-------------|---------|------|
| 4 | 功能规格文档 | Spec markdown 文件 | `.md` 最佳（自动索引），`.pdf` 需手动创建 markdown 摘要 | 支持 spec 搜索，辅助 gap 分类 |
| 5 | 寄存器定义 | YAML / IP-XACT / CSV 文件 | YAML 格式最方便（直接解析），IP-XACT 需符合标准 | 支持寄存器查询和 RAL 路径生成 |
| 6 | RTL 源码 | filelist.f + SystemVerilog 文件 | 标准 SV 语法，`module` / `endmodule` 结构 | 支持信号查找和扇入追踪 |
| 7 | 仿真历史 | sim_results/ 目录，子目录命名 `{test}_{seed}/` | 每个子目录含 `sim_result.json` 或 compile.log/run.log | 覆盖率命中趋势分析 |
| 8 | RAL 模型 | UVM RAL SystemVerilog 文件 | 标准 `uvm_reg` / `uvm_reg_block` 继承 | 寄存器访问路径生成 |

> **最小接入**：只需准备 1-3 项（URG 报告 + UVM 环境 + 命令模板），即可跑通覆盖率闭环的核心流程。

---

## 你的项目目录结构

cov_flow **不要求**你的项目遵循特定目录结构。只要 manifest 中的路径正确指向即可。
以下是一个典型项目的参考布局：

```
my_project/
├── sim/
│   ├── filelist.f              # RTL 文件列表
│   └── Makefile                # compile / run targets
├── rtl/
│   ├── my_design_top.sv
│   └── my_design_sub.sv
├── tb/
│   ├── env/
│   │   └── my_env.sv
│   ├── sequences/
│   │   └── my_base_seq.sv
│   ├── tests/
│   │   └── my_base_test.sv
│   ├── agents/
│   │   └── my_agent.sv
│   ├── config/
│   │   └── my_config.sv
│   └── reg_model/
│       └── my_reg_block.sv
├── spec/
│   └── my_spec.md
├── registers/
│   └── my_regs.yaml
├── coverage/
│   ├── urg_report/             # URG HTML 输出
│   │   ├── session.xml
│   │   ├── grp0.html
│   │   └── mod0.html
│   └── coverage_model/         # 覆盖率模型 SV 源码
│       └── my_cov.sv
├── sim_results/                # 仿真结果（构建后自动生成）
│   └── my_test_1/
│       ├── compile.log
│       └── run.log
└── .dv_ai_index/               # 索引文件（构建后自动生成）
    ├── coverage_index.json
    ├── tb_index.json
    └── ...
```

---

## Step 1：创建 project_manifest.yaml

### 1.1 设置环境变量

将你的项目根目录设为环境变量，manifest 中的相对路径会基于此解析：

```bash
export MY_PROJECT_ROOT=/path/to/my_project
echo 'export MY_PROJECT_ROOT=/path/to/my_project' >> ~/.bashrc
```

### 1.2 从模板创建 manifest

在 cov_flow 仓库中创建 manifest 文件：

```bash
mkdir -p mock_data/my_project
cat > mock_data/my_project/project_manifest.yaml << 'EOF'
project: my_project
owner_team: dv_my_team
top_instance: tb_top.u_dut

project_root: $MY_PROJECT_ROOT

coverage:
  default_report_id: latest
  reports_root: coverage/urg_report
  format: urg_html
  coverage_model_root: coverage/coverage_model

rtl:
  filelist: sim/filelist.f
  design_db:
    type: none
  index_path: .dv_ai_index

spec:
  fs:
    path: spec/my_spec.md
    index_path: .dv_ai_index

registers:
  source:
    type: yaml
    path: registers/my_regs.yaml
  ral_root: tb/reg_model
  index_path: .dv_ai_index

testbench:
  type: uvm
  env_root: tb/env
  base_test: my_base_test
  sequence_root: tb/sequences
  agent_root: tb/agents
  config_root: tb/config
  test_root: tb/tests
  index_path: .dv_ai_index

simulation:
  results_root: sim_results
  compile_cmd_template: "make compile TEST={test}"
  run_cmd_template: "make run TEST={test} SEED={seed}"
  coverage_cmd_template: "make cov TEST={test}"
  urg_cmd_template: "urg -dir {vdb_dir} -report {report_dir} -format html"
  urg_binary: "urg"
  timeout_seconds: 600
  urg_timeout_seconds: 300
  vdb_dir_template: "sim_results/coverage/{test}_{seed}.vdb"

policy:
  allow_direct_file_modification: false
  allow_running_simulation: true
  require_human_review_before_commit: true
EOF
```

### 1.3 逐字段说明

**项目标识**（必填）

| 字段 | 说明 | 示例 |
|------|------|------|
| `project` | 项目唯一标识，MCP 工具用它定位索引 | `my_project` |
| `owner_team` | 负责该项目 DV 的团队 | `dv_my_team` |
| `top_instance` | DUT 顶层实例路径 | `tb_top.u_dut` |

**project_root**（可选但推荐）

根目录路径，支持 `$ENV_VAR` 展开。所有 manifest 中的相对路径都基于此目录解析。
如果不设置，默认使用 manifest 文件所在目录。

**coverage**（必填）

| 字段 | 必填 | 说明 |
|------|------|------|
| `reports_root` | 是 | URG HTML 报告目录（含 session.xml） |
| `coverage_model_root` | 是 | 覆盖率模型 SV 源码目录（可设为 `null`） |
| `default_report_id` | 否 | 默认报告 ID，一般填 `latest` |
| `format` | 否 | 报告格式，目前仅支持 `urg_html` |

**rtl**（必填，但内容可为空）

| 字段 | 必填 | 说明 |
|------|------|------|
| `filelist` | 是 | RTL filelist.f 路径（无 RTL 时填 `null`） |
| `design_db.type` | 否 | 设计数据库类型：`verdi_kdb` / `vcs_elab` / `none` |
| `index_path` | 否 | 索引输出目录 |

**spec**（可选）

| 字段 | 说明 |
|------|------|
| `fs.path` | 功能规格文档路径（`.md` 格式最佳） |
| `micro_arch.path` | 微架构文档路径（可选） |

**registers**（必填，但 source 可为 none）

| 字段 | 必填 | 说明 |
|------|------|------|
| `source.type` | 是 | 格式类型：`yaml` / `ipxact` / `csv` / `excel` / `ral_model` / `none` |
| `source.path` | 否 | 寄存器定义文件路径（type 为 none 时可不填） |
| `ral_root` | 否 | UVM RAL 模型 SV 源码目录 |
| `index_path` | 否 | 索引输出目录 |

**testbench**（必填）

| 字段 | 必填 | 说明 |
|------|------|------|
| `type` | 是 | 固定填 `uvm` |
| `env_root` | 是 | UVM environment 源码目录 |
| `base_test` | 否 | 基础测试类名 |
| `sequence_root` | 否 | sequence 源码目录 |
| `agent_root` | 否 | agent 源码目录 |
| `config_root` | 否 | config 类源码目录 |
| `test_root` | 否 | test 类源码目录 |
| `index_path` | 否 | 索引输出目录 |

**simulation**（可选但推荐）

| 字段 | 说明 | 占位符 |
|------|------|--------|
| `compile_cmd_template` | 编译命令模板 | `{test}` |
| `run_cmd_template` | 运行命令模板 | `{test}`, `{seed}` |
| `coverage_cmd_template` | 覆盖率收集命令 | `{test}` |
| `urg_cmd_template` | URG 报告生成命令 | `{vdb_dir}`, `{report_dir}` |
| `urg_binary` | URG 二进制路径（默认 `urg`） | - |
| `timeout_seconds` | 编译/运行超时（默认 600 秒） | - |
| `urg_timeout_seconds` | URG 超时（默认 300 秒） | - |
| `results_root` | 仿真结果目录（默认 `sim_results`） | - |
| `vdb_dir_template` | VDB 目录模板 | `{test}`, `{seed}` |

**policy**（必填）

| 字段 | 说明 | 推荐值 |
|------|------|--------|
| `allow_direct_file_modification` | 是否允许 agent 直接修改源文件 | `false` |
| `allow_running_simulation` | 是否允许 agent 触发仿真 | `true` |
| `require_human_review_before_commit` | 生成结果是否需要人工审核 | `true` |

### 1.4 常见场景配置

**场景 A：标准项目（URG 报告 + UVM 环境）**

完整配置如上面 1.2 模板所示。这是最常见的接入方式，覆盖率闭环的 4 个阶段都能完整运行。

**场景 B：只有覆盖率报告，没有 TB 源码**

适用于只想做 gap 分类分析、不需要自动生成测试用例的场景：

```yaml
project: coverage_only_project
top_instance: tb_top.u_dut

coverage:
  default_report_id: latest
  reports_root: coverage/urg_report
  format: urg_html
  coverage_model_root: null          # 没有覆盖率模型 SV 源码

rtl:
  filelist: null                     # 没有 RTL 源码
  design_db:
    type: none

registers:
  source:
    type: none                       # 没有寄存器定义

testbench:
  type: uvm
  env_root: null                     # 没有 TB 源码
  index_path: .dv_ai_index

policy:
  allow_direct_file_modification: false
  allow_running_simulation: false     # 无法运行仿真
  require_human_review_before_commit: true
```

此配置支持 `cov_list_uncovered`、`cov_get_gap_detail`、`spec_search` 等只读查询工具，但不支持 TB 查询和仿真执行。

**场景 C：有寄存器定义（IP-XACT 格式）**

```yaml
registers:
  source:
    type: ipxact
    path: registers/my_ipxact.xml
  ral_root: tb/reg_model
  index_path: .dv_ai_index
```

`source.type` 支持的格式：`yaml`、`ipxact`、`csv`、`excel`、`ral_model`、`none`。

---

## Step 2：构建索引

### 2.1 必需索引

| 索引 | 命令 | 输入 | 输出 |
|------|------|------|------|
| 覆盖率索引 | `make build-real-index` | URG HTML 报告目录 | `.dv_ai_index/coverage_index.json` + `coverage_gaps.json` |
| TB 索引 | `make build-real-tb-index` | UVM 源文件目录 | `.dv_ai_index/tb_index.json` |

### 2.2 可选索引

| 索引 | 命令 | 输入 | 输出 |
|------|------|------|------|
| Spec 索引 | `python scripts/build_spec_index.py --manifest mock_data/my_project/project_manifest.yaml` | Spec markdown | `.dv_ai_index/spec_index.json` |
| 寄存器索引 | `python scripts/build_reg_index.py --manifest mock_data/my_project/project_manifest.yaml` | YAML 寄存器定义 | `.dv_ai_index/reg_db.json` |
| RTL 索引 | `python scripts/build_rtl_index.py --manifest mock_data/my_project/project_manifest.yaml` | filelist.f + SV 文件 | `.dv_ai_index/rtl_index.json` |
| 仿真历史索引 | `python scripts/build_sim_history_index.py --manifest mock_data/my_project/project_manifest.yaml` | sim_results/ 目录 | `.dv_ai_index/sim_history.json` |

### 2.3 验证索引文件

```bash
ls mock_data/my_project/.dv_ai_index/
# 期望至少看到：coverage_index.json, tb_index.json
```

---

## Step 3：注册项目

编辑 `projects.yaml`（仓库根目录），添加项目条目：

```yaml
projects:
  dma_subsystem:
    manifest: mock_data/dma_subsystem/project_manifest.yaml
    description: "Sample DMA project (Phase 0-2 demo)"
  axi2ahb:
    manifest: mock_data/axi2ahb/project_manifest.yaml
    description: "AXI2AHB project with VCS execution"
  my_project:
    manifest: mock_data/my_project/project_manifest.yaml
    description: "My verification project"
```

验证注册：

```bash
python3 -c "from lib.project_registry import get_registry; r = get_registry(); print(r.list_projects())"
```

注册后，所有 MCP 工具可以直接用项目名调用：
`cov_list_uncovered(project="my_project")`

---

## Step 4：配置 MCP（如未配置）

如果已完成 [快速入门](getting_started.md) 的 Step 3，可跳过此步。

确认 `.mcp.json` 存在且路径正确：

```bash
cat .mcp.json
```

在 Claude Code 中输入 `/mcp`，确认 `dv-context` server 显示为已连接。

---

## Step 5：验证接入

在 Claude Code 中依次执行以下 3 个查询：

### 5.1 覆盖率查询

```
列出 my_project 的 top 5 未覆盖 functional coverage gaps
```

**预期**：Claude 调用 `cov_list_uncovered(project="my_project", coverage_type="functional", top_n=5)`，返回 gap 列表。

**如果返回空**：检查 `coverage_index.json` 是否包含 gap 数据；确认 `reports_root` 路径正确。

### 5.2 TB 查询

```
查看 my_project 中有哪些已有的 UVM 测试
```

**预期**：Claude 调用 `tb_get_existing_tests_for_feature(project="my_project", feature="...")` 或 `tb_get_base_test_template(project="my_project")`，返回测试列表。

**如果返回空**：检查 `tb_index.json` 是否已构建；确认 `testbench.env_root` 路径指向包含 `.sv` 文件的目录。

### 5.3 Spec 搜索（如已构建 spec 索引）

```
搜索 my_project 中关于 xxx 的 spec 章节
```

**预期**：Claude 调用 `spec_search(project="my_project", query="xxx")`，返回匹配的 spec 段落。

**如果返回错误**：确认已运行 `python scripts/build_spec_index.py`；确认 `spec.fs.path` 指向存在的 `.md` 文件。

---

## Step 6：开始使用 Skills

| 推荐顺序 | Skill | 说明 |
|----------|-------|------|
| 1 | `/dv-coverage-gap-triage` | 对 gap 分类，确定优先级 |
| 2 | `/dv-coverage-scenario-generation` | 根据分类生成测试场景卡 |
| 3 | `/dv-testcase-generation` | 基于场景卡生成 UVM 测试代码 |
| 4 | `/dv-simulation-feedback` | 运行仿真，分析覆盖率变化 |
| 5 | `/dv-coverage-closure` | 端到端编排以上 4 步 |

详细用法参见 [Prompt Templates](user_prompt_templates.md) 中的 25 个即用模板。

---

## 接入 Checklist

| # | 步骤 | 完成标志 | 状态 |
|---|------|----------|------|
| 1 | URG HTML 报告就位 | `ls $PROJECT_ROOT/coverage/urg_report/` 能看到 session.xml | [ ] |
| 2 | UVM 源文件就位 | `ls $PROJECT_ROOT/tb/env/` 能看到 .sv 文件 | [ ] |
| 3 | project_manifest.yaml 创建 | `python scripts/validate_manifest.py --manifest mock_data/my_project/project_manifest.yaml` 通过 | [ ] |
| 4 | 覆盖率索引构建 | `.dv_ai_index/coverage_index.json` 存在且包含 gap 数据 | [ ] |
| 5 | TB 索引构建 | `.dv_ai_index/tb_index.json` 存在且包含 test/sequence 列表 | [ ] |
| 6 | 项目注册 | `projects.yaml` 包含项目条目 | [ ] |
| 7 | MCP 连接正常 | Claude Code 中 `/mcp` 显示 dv-context 已连接 | [ ] |
| 8 | 验证查询通过 | `cov_list_uncovered` 返回 gap 列表 | [ ] |

---

## Troubleshooting

### Q1：URG 报告路径不对，索引构建失败

**症状**：`make build-real-index` 报错 `reports_root not found`

**排查**：
```bash
# 检查 manifest 中的路径
grep reports_root mock_data/my_project/project_manifest.yaml

# 确认目录存在
ls $MY_PROJECT_ROOT/coverage/urg_report/session.xml
```

**解决**：修改 `reports_root` 为正确的相对路径（相对于 `project_root`）。

### Q2：SV 文件解析失败，TB 索引为空

**症状**：`tb_index.json` 生成但 `tests` 和 `sequences` 为空数组

**排查**：
```bash
# 检查 env_root 路径
grep env_root mock_data/my_project/project_manifest.yaml
ls $MY_PROJECT_ROOT/tb/env/*.sv

# 确认 SV 文件包含 uvm_component_utils 注册
grep -r "uvm_component_utils\|uvm_object_utils" $MY_PROJECT_ROOT/tb/
```

**解决**：确认 `env_root`、`sequence_root`、`test_root` 等路径指向包含 `.sv` 文件的目录，且文件中包含标准 UVM 宏注册。

### Q3：MCP 工具调用返回 "project not found"

**症状**：`cov_list_uncovered(project="my_project")` 返回错误

**排查**：
```bash
# 检查项目注册
cat projects.yaml | grep my_project

# 检查 manifest 路径是否可访问
python3 -c "
from lib.project_registry import get_registry
r = get_registry()
print(r.resolve('my_project'))
"
```

**解决**：确认 `projects.yaml` 中的 manifest 路径正确，且文件存在。

### Q4：仿真命令不执行

**症状**：`sim_run_targeted_test` 返回 `policy_checked: false`

**排查**：
```bash
# 检查 policy 设置
grep allow_running_simulation mock_data/my_project/project_manifest.yaml
```

**解决**：确认 `policy.allow_running_simulation: true`。调用时需传入 `confirm=true`。

### Q5：覆盖率 diff 为空

**症状**：`cov_get_coverage_diff` 返回无差异数据

**排查**：
```bash
# 确认至少运行过两次仿真
ls mock_data/my_project/sim_results/

# 确认 URG 报告已生成
ls mock_data/my_project/sim_results/*/urg_report/
```

**解决**：至少需要两次仿真结果（不同 test 或 seed），每次都需要生成 URG 报告。

### Q6：索引构建后 MCP 工具仍返回旧数据

**症状**：重建索引后工具返回的内容没有更新

**排查**：MCP server 使用文件读取，不存在缓存。

**解决**：确认索引文件确实已更新（检查文件时间戳），确认 MCP 工具调用的 `project` 参数与 `projects.yaml` 中的键名一致。
