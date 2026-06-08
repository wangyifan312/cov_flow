# Server Migration Quick Checklist

## 本地操作 (当前机器)

```bash
# 1. 提交所有变更
cd /Users/wangyifan/Desktop/AI/cov_flow
git add -A
git status  # 检查
git commit -m "feat(phase-5b): real simulation execution infrastructure

- SimExecutor: subprocess management with security boundaries
- SimLogParser: VCS/UVM log parsing with priority-based pass/fail detection  
- UrgRunner: URG report generation and parsing pipeline
- Manifest schema: mode: mock|real, 7 new simulation fields
- MCP tools: real mode branching for 4 sim tools
- CLI: sim_runner.py --real flag
- Tests: 521 total, 123 new tests for Phase 5b

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"

git push origin main
```

## 服务器操作

```bash
# 2. 克隆项目
ssh user@server
cd /path/to/workspace
git clone https://github.com/your-org/cov_flow.git
cd cov_flow

# 3. 安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 4. 验证安装
make test        # 521 passed, 18 skipped
make lint        # ruff 0
make typecheck   # mypy 0

# 5. 设置环境变量 (替换为你的实际路径)
export AXI2AHB_ROOT=/home/user/projects/AXI2AHB-Lite-Bridge-UVM-Verification
echo 'export AXI2AHB_ROOT=/home/user/projects/AXI2AHB-Lite-Bridge-UVM-Verification' >> ~/.bashrc

# 6. 创建 real manifest
cp mock_data/axi2ahb/project_manifest_real.yaml.example mock_data/axi2ahb/project_manifest_real.yaml
# 编辑确认配置正确

# 7. 更新项目注册表
cat >> projects.yaml << 'EOF'
  axi2ahb_real:
    manifest: mock_data/axi2ahb/project_manifest_real.yaml
    description: "Real AXI2AHB project with VCS execution"
EOF

# 8. 构建真实索引
make build-real-tb-index
ls mock_data/axi2ahb/.dv_ai_index/
# 期望: tb_index.json, coverage_index.json

# 9. 配置 MCP
cp .mcp.json.example .mcp.json

# 10. 验证 VCS
which vcs && vcs -ID | head -3
which urg && urg -help | head -3

# 11. 测试编译 (可选，验证 VCS 环境)
cd $AXI2AHB_ROOT
make compile TEST=base_test
ls simv

# 12. 返回 cov_flow
cd -

# 13. 测试 mock 模式
python scripts/sim_runner.py \
  --manifest mock_data/axi2ahb/project_manifest.yaml \
  --test base_test --seed 1 --out /tmp/test.json
cat /tmp/test.json | grep dry_run

# 14. 测试 real 模式 (如果步骤 11 成功)
python scripts/sim_runner.py \
  --manifest mock_data/axi2ahb/project_manifest_real.yaml \
  --test base_test --seed 1 --real

# 15. 启动 Claude Code
claude
# 输入: /mcp  (检查 dv-context server 是否连接)
# 输入: 列出 axi2ahb_real 的 top 5 gaps
```

## 快速验证命令

```bash
# 一键验证脚本
cat > verify_setup.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Verifying cov_flow setup ==="

echo "1. Python dependencies..."
python -c "import mcp, jsonschema, yaml, bs4, lxml" && echo "✓ OK"

echo "2. Tests..."
make test | tail -1

echo "3. Lint + typecheck..."
make lint | grep "0 issues" && make typecheck | grep "0 errors"

echo "4. MCP server..."
.venv/bin/python -c "from dv_mcp.dv_context_server.server import mcp; print('✓ OK')"

echo "5. AXI2AHB_ROOT..."
[ -n "$AXI2AHB_ROOT" ] && echo "✓ $AXI2AHB_ROOT"

echo "6. VCS..."
which vcs && echo "✓ OK"

echo "7. Indexes..."
[ -f mock_data/axi2ahb/.dv_ai_index/tb_index.json ] && echo "✓ tb_index.json"
[ -f mock_data/axi2ahb/.dv_ai_index/coverage_index.json ] && echo "✓ coverage_index.json"

echo "8. MCP config..."
[ -f .mcp.json ] && echo "✓ .mcp.json"

echo "=== All checks passed ==="
EOF

chmod +x verify_setup.sh
./verify_setup.sh
```

## 故障排查

| 问题 | 解决 |
|------|------|
| `make test` 失败 | 检查 Python 版本 >= 3.11, 重新 `pip install -e ".[dev]"` |
| `$AXI2AHB_ROOT` 为空 | `export AXI2AHB_ROOT=...` 并加入 `~/.bashrc` |
| `make build-real-tb-index` 失败 | 确认 `$AXI2AHB_ROOT` 路径正确，目录存在 |
| Claude Code 不识别 MCP | 检查 `.mcp.json` 格式，重启 Claude Code |
| VCS 编译失败 | 检查 Makefile 中的 include paths 和 filelist.f |
| URG 找不到 | 确认 `$VCS_HOME/bin` 在 PATH 中 |

## 迁移后测试工作流

```
# 在 Claude Code 中测试 4 个工作流:

1. Coverage Triage:
   "使用 dv-coverage-closure，对 axi2ahb_real 做 functional coverage triage，输出 top 10 gaps"

2. Scenario Generation:
   "使用 dv-coverage-scenario-generation，项目 axi2ahb_real，Gap ID: GAP_0006"

3. Testcase Generation:
   "使用 dv-testcase-generation，项目 axi2ahb_real，Gap ID: GAP_0006"

4. Simulation Feedback:
   "使用 dv-simulation-feedback，项目 axi2ahb_real，运行 wrap8_targeted_test seed=42，分析 GAP_0006"
```
