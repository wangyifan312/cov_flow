# 快速入门指南

本文档帮助新同事从零开始，完成仓库安装、Skills 注册、MCP 配置，
并在示例数据上跑通一次完整的覆盖率闭环流程。

---

## 前置条件

| 条件 | 说明 |
|---|---|
| Python 3.11+ | `python3 --version` 确认版本 |
| Claude Code CLI | `claude --version` 能正常输出（安装见 [claude.ai](https://claude.ai)） |
| Git | 用于克隆仓库 |
| （可选）VCS 仿真环境 | 仅在使用真实仿真时需要 |

---

## Step 1：安装（约 2 分钟）

```bash
git clone <repo_url>
cd cov_flow
pip install -e ".[dev]"
make accept
```

`make accept` 会依次执行以下检查，全部通过才表示安装成功：

| 步骤 | 说明 |
|---|---|
| `validate` | 校验 project_manifest.yaml 格式 |
| `validate-gaps` | 校验 coverage_gaps.json 格式 |
| `build-indexes` | 构建所有索引文件 |
| `build-dma-indexes` | 构建 dma_subsystem 的 spec/reg/rtl/sim_history 索引 |
| `build-real-index` | 解析 axi2ahb 的 URG HTML 报告生成索引 |
| `lint` | ruff 代码风格检查（要求 0 问题） |
| `typecheck` | mypy 类型检查（要求 0 错误） |
| `test` | pytest 运行全部测试 |
| `smoke-server` | 验证 MCP server 能正常导入和注册工具 |

> **提示**：国内 pip 安装超时可使用阿里云镜像：
> ```bash
> pip install -e ".[dev]" -i https://mirrors.aliyun.com/pypi/simple/
> ```

---

## Step 2：注册 Skills（约 1 分钟）

Skills 以 slash command 的形式注册到 Claude Code。执行以下脚本，
自动为 `skills/` 目录下的 5 个 skill 生成对应命令文件：

```bash
mkdir -p .claude/commands
for skill in skills/*/; do
  name=$(basename "$skill")
  cat > ".claude/commands/${name}.md" << EOF
\$ARGUMENTS

Read and follow the instructions in skills/${name}/SKILL.md to complete this task.
EOF
done
```

执行后，在 Claude Code 中输入 `/dv-` 即可看到 5 个可用命令。

---

## Step 3：配置 MCP（约 1 分钟）

```bash
cp .mcp.json.example .mcp.json
```

确认 `.mcp.json` 中的 `command` 为 `python3`：

```json
{
  "mcpServers": {
    "dv-context": {
      "command": "python3",
      "args": ["-m", "dv_mcp.dv_context_server.server"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

---

## Step 4：第一次使用（约 5 分钟）

启动 Claude Code：

```bash
claude
```

进入后，输入以下自然语言指令：

```
帮我列出 axi2ahb 项目 top 10 未覆盖的 functional coverage gaps
```

预期 Claude 会：
1. 调用 `cov_list_uncovered(project="axi2ahb", coverage_type="functional", top_n=10)`
2. 返回一个结构化表格，包含 gap_id、covergroup、coverpoint、bin、priority 等字段

如果没有看到工具调用结果，请检查：
- `.mcp.json` 中的路径是否正确
- Python 版本是否为 3.11+（`python3 --version`）

---

## Step 5：完整闭环体验

仓库提供了 5 个 skill，覆盖覆盖率闭环的完整流程：

| Skill | 用途 | 触发命令 |
|---|---|---|
| `/dv-coverage-closure` | 端到端编排，串联以下 4 个步骤 | `/dv-coverage-closure` |
| `/dv-coverage-gap-triage` | 对 gap 进行分类和优先级判定 | `/dv-coverage-gap-triage` |
| `/dv-coverage-scenario-generation` | 根据 gap 生成测试场景卡 | `/dv-coverage-scenario-generation` |
| `/dv-testcase-generation` | 基于场景卡生成 UVM 测试用例代码 | `/dv-testcase-generation` |
| `/dv-simulation-feedback` | 运行仿真并分析覆盖率反馈 | `/dv-simulation-feedback` |

### 快速闭环示例（echo 命令，无需 VCS）

在 Claude Code 中依次执行：

```
1. /dv-coverage-gap-triage
   输入：axi2ahb GAP_0006
   → Claude 调用 cov_get_gap_detail 和 spec_search，输出分类结果

2. /dv-coverage-scenario-generation
   输入：基于上面的 triage 结果
   → Claude 生成 scenario card（JSON 格式）

3. /dv-testcase-generation
   输入：基于上面的 scenario card
   → Claude 调用 tb_get_base_test_template 和 tb_find_sequence，
     生成 UVM sequence 代码

4. /dv-simulation-feedback
   输入：运行生成的测试
   → Claude 调用 sim_run_targeted_test（执行 echo 命令返回仿真结果）
```

---

## Step 6：接入真实项目

> **详细接入指南**请参见 [项目接入指南](project_onboarding.md)，包含完整的字段说明、场景配置和 Checklist。

以下 4 步将你的真实项目接入 cov_flow 框架。

### 6.1 设置环境变量

```bash
export YOUR_PROJECT_ROOT=/path/to/your/rtl/project
```

### 6.2 创建项目 manifest

从 axi2ahb 的示例 manifest 复制并修改：

```bash
cp mock_data/axi2ahb/project_manifest.yaml \
   mock_data/<your_project>/project_manifest.yaml
```

编辑 `project_manifest.yaml`，重点修改：
- `project_root`：指向你的项目根目录
- `compile_cmd_template` / `run_cmd_template`：填入你的 VCS 编译和运行命令

### 6.3 构建索引

```bash
# 构建覆盖率索引（解析 URG HTML 报告）
make build-real-index

# 构建 TB 索引（解析 UVM 源文件，需设置环境变量指向源文件目录）
make build-real-tb-index

# 构建 spec / register / RTL / sim_history 索引（按需）
make build-dma-indexes
```

### 6.4 注册项目

编辑 `projects.yaml`，添加你的项目：

```yaml
projects:
  your_project:
    manifest: mock_data/your_project/project_manifest.yaml
    description: "Your project description"
```

注册后，MCP 工具可以直接用项目名调用，例如：
`cov_list_uncovered(project="your_project")`

---

## 常用文档速查

| 我要做什么 | 看哪个文档 |
|---|---|
| 查某个工具怎么用 | `docs/mcp_tool_reference.md` |
| 找 prompt 模板 | `docs/user_prompt_templates.md` |
| 服务端部署（VCS 集成） | `docs/server_setup_guide.md` |
| 看完整 walkthrough 示例 | `examples/README.md` |
| 了解项目架构和设计决策 | `implementation_plan.md` |
| 了解每个目录的作用 | `docs/project_structure.md` |
| 快速检查清单 | `docs/quick_start_checklist.md` |

---

## Troubleshooting

| 问题 | 排查方法 |
|---|---|
| `pip install` 超时 | 使用阿里云镜像：`-i https://mirrors.aliyun.com/pypi/simple/` |
| MCP 连接失败 | 检查 `.mcp.json` 中的 `command` 是否为 `python3`，且 Python 3.11+ 已安装 |
| `make smoke-server` 报错 | 确认 `PYTHONPATH` 包含仓库根目录；确认 Python 3.11+ 已安装 |
| Claude Code 看不到 Skills | 确认 `.claude/commands/` 目录存在且包含 5 个 `.md` 文件；重启 Claude Code |
| VCS 编译失败 | 检查 manifest 中的 `compile_cmd_template` 是否正确，`{test}` 占位符是否匹配 |
| 索引构建失败 | 检查 `projects.yaml` 中的 manifest 路径是否正确；确认 URG 报告文件存在 |
| 工具调用返回空结果 | 确认索引文件已构建（`ls mock_data/<project>/*_index.json`） |
| `ModuleNotFoundError` | 重新执行 `pip install -e ".[dev]"`，确保 `dv_mcp` 和 `lib` 包已安装 |

---

## 下一步

完成入门指南后，推荐阅读顺序：

1. **`examples/triage_walkthrough.md`** — 看一个完整的 gap 分类案例
2. **`examples/full_closure_walkthrough.md`** — 看端到端闭环案例
3. **`docs/mcp_tool_reference.md`** — 熟悉全部 26 个 MCP 工具
4. **`implementation_plan.md`** — 理解项目架构和设计原则
