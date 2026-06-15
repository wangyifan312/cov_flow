# Phase 6 Server Migration Guide

## 概述

将 cov_flow 项目迁移到带有 VCS + Claude Code 的服务器，启用真实仿真执行模式。

**前提条件**:
- 服务器已安装 VCS (Synopsys VCS O-2018.09-SP2 或更新)
- 服务器已安装 Claude Code CLI
- 服务器已安装 Python 3.11+
- 服务器已有 axi2ahb UVM 项目源码

---

## 步骤 1: 本地准备 (当前机器)

### 1.1 提交所有 Phase 5b 变更

```bash
cd /path/to/cov_flow

# 检查未提交变更
git status

# 添加所有 Phase 5b 文件
git add -A

# 提交
git commit -m "feat(phase-5b): real simulation execution infrastructure

- SimExecutor: subprocess management with security (test name validation, path traversal rejection, shlex+shell=False, cwd lock)
- SimLogParser: VCS/UVM log parsing with priority-based pass/fail detection
- UrgRunner: URG report generation and parsing pipeline
- Manifest schema: 6 new simulation fields
- MCP tools: real mode branching for 4 sim tools
- CLI: sim_runner.py --dry-run flag
- Tests: 521 total, 123 new tests for Phase 5b

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"

# 推送到远程
git push origin main
```

### 1.2 确认推送成功

```bash
git log --oneline -5
# 应该看到刚才的 commit
```

---

## 步骤 2: 服务器环境准备

### 2.1 登录服务器

```bash
ssh user@your-server.com
```

### 2.2 克隆项目

```bash
cd /path/to/workspace  # 选择工作目录

git clone https://github.com/your-org/cov_flow.git
cd cov_flow
```

### 2.3 安装 Python 依赖

```bash
# 安装项目 (editable mode + dev dependencies)
pip install -e ".[dev]"
```

### 2.4 验证安装

```bash
# 检查依赖
pip list | grep -E "mcp|jsonschema|pyyaml|beautifulsoup|lxml|pytest|ruff|mypy"

# 运行测试套件
make test
# 期望: 521 passed, 18 skipped

# Lint + typecheck
make lint
make typecheck
# 期望: ruff 0, mypy 0
```

---

## 步骤 3: 配置真实 axi2ahb 项目

### 3.1 定位 axi2ahb 项目

假设服务器上的 axi2ahb 项目路径为:
```
/home/user/projects/AXI2AHB-Lite-Bridge-UVM-Verification/
```

确认项目结构:
```bash
ls /home/user/projects/AXI2AHB-Lite-Bridge-UVM-Verification/
# 期望看到:
#   seq_lib/         # sequences
#   tests/           # test classes
#   env/             # environment
#   agent/           # agents
#   config/          # config classes
#   sim/             # simulation scripts
#   Makefile         # compile/run targets
```

### 3.2 设置环境变量

```bash
export AXI2AHB_ROOT=/home/user/projects/AXI2AHB-Lite-Bridge-UVM-Verification
```

**建议**: 添加到 `~/.bashrc` 或 `~/.zshrc`:
```bash
echo 'export AXI2AHB_ROOT=/home/user/projects/AXI2AHB-Lite-Bridge-UVM-Verification' >> ~/.bashrc
source ~/.bashrc
```

### 3.3 配置项目 manifest

```bash
cd /path/to/cov_flow

# 编辑 manifest 配置 VCS 命令
nano mock_data/axi2ahb/project_manifest.yaml
```

**关键配置项**:

```yaml
project_root: $AXI2AHB_ROOT

simulation:
  compile_cmd_template: "make compile TEST={test}"
  run_cmd_template: "make run TEST={test} SEED={seed}"
  urg_cmd_template: "urg -dir {vdb_dir} -report {report_dir} -format html"
  urg_binary: "urg"
  timeout_seconds: 600
  urg_timeout_seconds: 300
  results_root: "sim_results"
  vdb_dir_template: "sim_results/coverage/{test}_{seed}.vdb"
```

### 3.4 更新项目注册表

```bash
nano projects.yaml
```

添加真实项目条目:
```yaml
projects:
  dma_subsystem:
    manifest: mock_data/dma_subsystem/project_manifest.yaml
    description: "Sample DMA project (Phase 0-2 demo)"
  axi2ahb:
    manifest: mock_data/axi2ahb/project_manifest.yaml
    description: "AXI2AHB project with VCS execution"
```

### 3.5 构建真实索引

```bash
# 构建 TB 索引 (需要 AXI2AHB_ROOT 已设置)
make build-real-tb-index

# 验证索引生成
ls mock_data/axi2ahb/.dv_ai_index/
# 期望: tb_index.json, coverage_index.json
```

---

## 步骤 4: 配置 MCP Server

### 4.1 复制 MCP 配置

```bash
cp .mcp.json.example .mcp.json
```

### 4.2 验证 MCP 配置

```bash
cat .mcp.json
# 期望内容:
# {
#   "mcpServers": {
#     "dv-context": {
#       "command": "python3",
#       "args": ["-m", "dv_mcp.dv_context_server.server"],
#       "env": {
#         "PYTHONPATH": "."
#       }
#     }
#   }
# }
```

### 4.3 测试 MCP Server

```bash
# 启动 server (阻塞模式，用于测试)
make run-server

# 在另一个终端验证
python3 -c "
from dv_mcp.dv_context_server.tools.coverage_tools import cov_list_uncovered
result = cov_list_uncovered('axi2ahb_real', coverage_type='functional', top_n=5)
print('OK:', result['ok'])
print('Gaps:', len(result['result']['gaps']))
"
```

---

## 步骤 5: 验证 VCS 环境

### 5.1 检查 VCS 可用性

```bash
which vcs
vcs -ID | head -5
# 期望: VCS 版本信息

which urg
urg -help | head -3
# 期望: URG 帮助信息
```

### 5.2 测试编译命令

```bash
cd $AXI2AHB_ROOT

# 测试编译 (不需要跑完整仿真)
make compile TEST=base_test
# 期望: 编译成功，生成 simv

ls simv simv.daidir/
# 期望: 编译产物存在
```

### 5.3 测试运行命令

```bash
# 快速运行一个测试
make run TEST=base_test SEED=1

# 检查输出
ls sim_results/base_test_1/
# 期望: run.log, coverage/
```

---

## 步骤 6: 端到端测试

### 6.1 Dry-run 模式测试 (安全)

```bash
cd /path/to/cov_flow

# 使用 dry-run 模式渲染命令（不执行）
python scripts/sim_runner.py \
  --manifest mock_data/axi2ahb/project_manifest.yaml \
  --test base_test \
  --seed 1 \
  --dry-run
```

### 6.2 Real 模式测试 (需要 VCS)

```bash
# 执行真实仿真
python scripts/sim_runner.py \
  --manifest mock_data/axi2ahb/project_manifest.yaml \
  --test base_test \
  --seed 1

# 检查输出
ls mock_data/axi2ahb/sim_results/base_test_1/
# 期望: run.log, sim_result.json, coverage/

cat mock_data/axi2ahb/sim_results/base_test_1/sim_result.json | jq '.run.status'
# 期望: "pass"
```

### 6.3 URG 报告生成

```bash
# 手动触发 URG
python scripts/sim_runner.py \
  --manifest mock_data/axi2ahb/project_manifest.yaml \
  --test base_test \
  --seed 1

# 检查 URG 输出
ls mock_data/axi2ahb/sim_results/base_test_1/urg_report/
# 期望: index.html, dashboard.txt
```

### 6.4 Coverage Diff

```bash
# 再跑一个测试
python scripts/sim_runner.py \
  --manifest mock_data/axi2ahb/project_manifest.yaml \
  --test base_test \
  --seed 2

# 计算 diff
python3 -c "
from lib.coverage_diff import compute_diff
import json

with open('mock_data/axi2ahb/sim_results/base_test_1/urg_report/coverage_gaps.json') as f:
    before = json.load(f)

with open('mock_data/axi2ahb/sim_results/base_test_2/urg_report/coverage_gaps.json') as f:
    after = json.load(f)

diff = compute_diff(before, after)
print('Newly covered:', diff['summary']['newly_covered'])
print('Regressed:', diff['summary']['regressed'])
"
```

---

## 步骤 7: Claude Code 集成

### 7.1 启动 Claude Code

```bash
cd /path/to/cov_flow

# 确保 .mcp.json 存在
ls .mcp.json

# 启动 Claude Code
claude
```

### 7.2 测试 MCP Tools

在 Claude Code 中执行:

```
请帮我列出 axi2ahb_real 项目的 top 5 functional coverage gaps
```

Claude 应该:
1. 调用 `cov_list_uncovered("axi2ahb_real", coverage_type="functional", top_n=5)`
2. 返回 5 个 gaps (GAP_0001 ~ GAP_0005)

### 7.3 端到端工作流测试

**场景 1: Coverage Triage**
```
使用 dv-coverage-closure，对 axi2ahb_real 项目 latest regression 做 functional coverage triage。
范围：u_axi2ahb。输出 top 10 gaps。不要修改代码。
```

**场景 2: Scenario Generation**
```
使用 dv-coverage-scenario-generation。
项目：axi2ahb_real
Gap ID：GAP_0006
任务：生成 scenario card
```

**场景 3: Testcase Generation**
```
使用 dv-testcase-generation。
项目：axi2ahb_real
Gap ID：GAP_0006
Scenario card：scenario_card_GAP_0006.md
任务：生成 UVM sequence patch
```

**场景 4: Simulation & Feedback**
```
使用 dv-simulation-feedback。
项目：axi2ahb_real
Test：wrap8_targeted_test
Seed：42
目标 Gap：GAP_0006
任务：运行仿真并分析 coverage diff
```

---

## 步骤 8: 故障排查

### 8.1 VCS 编译失败

**症状**: `compile_cmd` 返回非零退出码

**排查**:
```bash
# 查看编译日志
cat mock_data/axi2ahb/sim_results/base_test_1/compile.log | tail -20

# 常见错误:
# - 缺少 include path → 检查 Makefile 中的 +incdir+
# - 未定义宏 → 检查 +define+
# - 文件找不到 → 检查 filelist.f
```

### 8.2 URG 报告生成失败

**症状**: `urg_cmd` 失败

**排查**:
```bash
# 手动运行 URG
cd $AXI2AHB_ROOT
urg -dir sim_results/base_test_1/coverage/base_test_1.vdb \
    -report sim_results/base_test_1/urg_report \
    -format html

# 常见错误:
# - .vdb 文件不存在 → 检查仿真是否启用了 coverage (-cm line+cond+fsm+tgl+branch)
# - urg 找不到 → 检查 $VCS_HOME/bin 在 PATH 中
```

### 8.3 MCP Tools 无法访问

**症状**: Claude Code 不调用 MCP tools

**排查**:
```bash
# 检查 .mcp.json 格式
cat .mcp.json | python -m json.tool

# 手动测试 server
python3 -m dv_mcp.dv_context_server.server --help

# 检查 Claude Code 是否识别 MCP server
# 在 Claude Code 中输入: /mcp
# 应该看到 "dv-context" server
```

### 8.4 环境变量未生效

**症状**: `$AXI2AHB_ROOT` 为空

**排查**:
```bash
# 检查环境变量
echo $AXI2AHB_ROOT

# 如果为空，重新设置
export AXI2AHB_ROOT=/path/to/AXI2AHB-Lite-Bridge-UVM-Verification

# 验证 manifest 能解析
python3 -c "
from lib.manifest import Manifest
m = Manifest.load('mock_data/axi2ahb/project_manifest.yaml')
print('project_root:', m.get('project_root'))
print('Resolved:', m.resolve_path(m.get('project_root')))
"
```

---

## 步骤 9: 性能优化 (可选)

### 9.1 并行仿真

如果服务器有多核，可以修改 Makefile 启用并行:

```makefile
# $AXI2AHB_ROOT/Makefile
compile:
	vcs -sverilog -full64 -timescale=1ns/1ps \
	    -debug_access+all \
	    -j4 \                    # ← 4 核并行编译
	    -f sim/filelist.f \
	    -o simv

run:
	./simv +UVM_TESTNAME=$(TEST) +UVM_VERBOSITY=UVM_MEDIUM \
	    +ntb_random_seed=$(SEED) \
	    -l sim_results/$(TEST)_$(SEED)/run.log \
	    -cm line+cond+fsm+tgl+branch \
	    -cm_dir sim_results/coverage/$(TEST)_$(SEED).vdb
```

### 9.2 增量编译

```makefile
# 只在源文件变化时重新编译
compile: simv

simv: $(shell cat sim/filelist.f | grep '\.sv$$')
	vcs -sverilog -full64 -timescale=1ns/1ps \
	    -debug_access+all \
	    -f sim/filelist.f \
	    -o simv
```

---

## 步骤 10: 记录配置

### 10.1 创建服务器配置文档

```bash
cat > SERVER_CONFIG.md << 'EOF'
# Server Configuration

## Environment
- Server: user@your-server.com
- VCS Version: VCS O-2018.09-SP2
- Python: 3.11.0
- Claude Code: Latest

## Paths
- cov_flow: /path/to/cov_flow
- axi2ahb: /home/user/projects/AXI2AHB-Lite-Bridge-UVM-Verification
- AXI2AHB_ROOT: /home/user/projects/AXI2AHB-Lite-Bridge-UVM-Verification

## MCP Server
- Command: python3 -m dv_mcp.dv_context_server.server
- Env: PYTHONPATH=.

## Projects
- dma_subsystem: sample (Phase 0-2 demo)
- axi2ahb: sample (Phase 3 demo)
- axi2ahb_real: real (VCS execution enabled)

## Test Results
- 521 tests passed
- 18 tests skipped (require real axi2ahb)
- ruff 0, mypy 0
EOF
```

### 10.2 提交配置到 Git

```bash
git add SERVER_CONFIG.md
git commit -m "docs: add server configuration guide"
git push
```

---

## Checklist

- [ ] Git push Phase 5b changes
- [ ] Git clone on server
- [ ] Install Python dependencies
- [ ] Set AXI2AHB_ROOT environment variable
- [ ] Configure project_manifest.yaml with VCS commands
- [ ] Update projects.yaml
- [ ] Build real indexes (tb_index.json, coverage_index.json)
- [ ] Configure .mcp.json
- [ ] Test MCP server
- [ ] Verify VCS availability
- [ ] Test compile/run/urg commands
- [ ] Run dry-run mode test
- [ ] Run real mode test
- [ ] Start Claude Code
- [ ] Test 4 workflows (triage, scenario, generation, feedback)
- [ ] Document configuration

---

## Next Steps

完成迁移后:

1. **收集指标**: 按 implementation_plan.md §14 收集真实数据
   - gap 分类可接受率
   - scenario card 有用率
   - 生成代码编译通过率
   - 生成 case 命中目标 gap 比例

2. **运行 Eval Suite**: 启用 LLM 执行模式
   ```bash
   python scripts/run_eval.py --eval-dir evals/ --llm-mode
   ```

3. **用户试用**: 邀请 1-2 位验证工程师试用，收集反馈

4. **迭代优化**: 根据真实使用数据调整 prompts, skills, tools