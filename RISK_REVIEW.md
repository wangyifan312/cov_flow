# cov_flow Phase 3 风险评审与处理计划

> 文档用途：本文档用于记录 `cov_flow` 仓库当前 Phase 3 状态下仍需关注的工程风险，并为 Claude Code coding agent 提供可执行的修复任务。
>
> 当前建议状态：`PASS WITH ISSUES`
>
> 推荐动作：先完成 Phase 3 hardening / release hygiene，再决定是否进入 Phase 4 / Phase 5。

---

## 1. 当前阶段判断

当前仓库已从 Phase 0 / Phase 1 mock MVP 推进到 Phase 3，主要能力包括：

- Phase 0：工程骨架、README、CLAUDE.md、Makefile、pyproject、基础目录结构。
- Phase 1：mock schemas、mock data、mock index、mock MCP tools、基础 tests。
- Phase 2：Skills references、scenario card validation、patch metadata validation、sim dry-run、coverage diff、eval dry-run。
- Phase 3：URG HTML coverage report parser、AXI2AHB demo coverage data、real coverage index demo、MCP coverage tools integration。

当前不建议直接进入 Phase 4 / Phase 5。进入下一阶段前，应先处理本文档列出的 P1 风险，尤其是：

1. 确认 `mock_data/axi2ahb` 数据安全边界；
2. 统一 eval runner LLM execution 的阶段口径；
3. 明确 `cov_get_coverpoint_source` 仍不是真实 coverage model source resolver；
4. 建立 CI 或至少保留明确的本地验收记录；
5. 限定 URG parser 当前支持范围。

---

## 2. 风险等级定义

| 等级 | 含义 | 处理策略 |
|---|---|---|
| P0 | 阻塞当前 MVP 或导致核心命令失败 | 必须立即修复 |
| P1 | 进入下一阶段前必须处理或明确豁免 | 优先修复 |
| P2 | 不阻塞当前阶段，但影响复用、稳定性或工程质量 | 纳入后续迭代 |
| P3 | 文档、清理、可维护性问题 | 可延后处理 |

> 说明：原风险列表中的序号 1、2 已确认可忽略：`pyproject.toml` 与 `Makefile` 格式没有问题，因此本文档不再纳入处理范围。

---

## 3. 风险总览表

| 序号 | 风险等级 | 风险项 | 当前表现 | 影响 | 建议处理 | 是否阻塞下一阶段 |
|---:|---|---|---|---|---|---|
| 3 | P1 | 缺少 GitHub Actions CI | GitHub 仓库未看到 `.github/workflows/ci.yml` | README 中声明 acceptance clean，但外部无法自动验证 | 新增 CI，执行安装、`make accept`、eval dry-run | 不强阻塞，但强烈建议补 |
| 4 | P1 | `mock_data/axi2ahb` 数据安全边界不清 | README 描述为 real AXI2AHB bridge project / URG parser demo | 如果包含真实公司路径、模块名、coverage 点，可能泄露 IP 信息 | 明确标注为 public / synthetic / sanitized demo；如不能确认，脱敏或移除 | 可能阻塞公开发布 |
| 5 | P1 | `cov_get_coverpoint_source` 能力描述可能被误解 | Phase 3 已接 URG parser，但该 tool 仍返回 generated/mock source snippet | 用户可能误以为已支持真实 coverage model source 追踪 | README / CLAUDE.md 明确：Phase 3 不包含真实 coverage model source resolver | 不阻塞，但需文档说明 |
| 6 | P1 | Eval runner 阶段口径不一致 | README Next Steps 写 Phase 6，但 README/evals 中仍有 “Phase 3+” 表述 | coding agent 可能误把 LLM eval execution 提前到 Phase 3/4 | 统一为：`LLM execution is deferred to Phase 6` | 建议进入下一阶段前修复 |
| 7 | P1 | Phase 3 release-ready 缺少可见验收记录 | 静态 review 看到结构完整，但缺少可见验收记录 | 可能存在隐藏依赖、路径、测试或环境问题 | 本地或 CI 运行完整验收命令，并记录结果 | 若未跑通则阻塞 |
| 8 | P1/P2 | 真实 URG parser 支持范围未充分限定 | README 声称 URG HTML parser complete，但不同 VCS/URG 版本 HTML 结构可能不同 | 用户拿真实报告测试时可能解析失败 | 文档说明当前支持的 URG report 版本/样例结构；增加 unsupported cases | 不阻塞，但影响用户预期 |
| 9 | P2 | `.mcp.json` 绑定本地 `.venv/bin/python` | 对开发者本机可用，但其他同事环境可能不同 | 团队复用时 MCP 启动失败 | 提供 `.mcp.json.example`，README 说明如何按本地环境配置 | 不阻塞当前开发 |
| 10 | P2 | Project registry 尚未完善 | MCP tools 可能主要依赖 manifest path | 用户体验不够产品化，每次都要传 manifest 路径 | 后续增加 `projects.yaml`、环境变量或 registry 机制 | 不阻塞 Phase 3 |
| 11 | P2 | Phase 4/5 边界容易被提前突破 | 已完成 Phase 3，下一步 coding agent 容易直接跳到 Verdi/VCS 或 UVM generation | 可能过早引入真实 EDA、真实项目数据和安全风险 | 明确：Phase 4/5 必须用户批准；下一步先做 Phase 3 hardening | 流程风险，需管控 |
| 12 | P2 | 真实 coverage source resolver 缺失 | 当前能解析 coverage gap，但不能映射到真实 coverage model 源码片段 | scenario 生成时 evidence 链不完整 | 后续增加 bounded source snippet resolver：`file + line range + allowlist + max bytes` | 不阻塞 parser，但影响闭环质量 |
| 13 | P2 | AXI2AHB coverage gap 数量较大，可能带来性能问题 | README 提到 982 gaps | MCP 查询、eval、测试可能随数据量增大变慢 | 增加 pagination、limit、truncation tests | 不阻塞，但需测试保护 |
| 14 | P2 | MCP tool 输出 contract 需持续锁定 | 当前使用 envelope，但后续新增 parser / adapter 后可能出现字段漂移 | Claude Code 调用稳定性下降 | 增加 contract tests，固定 `ok/tool/project/result/evidence/truncated/next_actions` | 不阻塞，但应纳入测试 |
| 15 | P2/P3 | “real project data”措辞容易引发误解 | README 同时写 real AXI2AHB 和 no real project data except URG demo | 对外 review 时容易被质疑安全边界 | 改成 “sample / public / sanitized URG demo data”，并说明来源 | 不阻塞，但影响可信度 |
| 16 | P3 | README 状态表可能过于乐观 | 直接标 Phase 3 Done，但仍有 parser 边界和 CI 风险 | 用户可能误解为生产可用 | 改成 “Phase 3 implemented, pending release validation”，直到 CI/验收通过 | 不阻塞，但建议修正 |
| 17 | P3 | `implementation_plan.md` 可能落后于当前实现 | 项目已进入 Phase 3，但规划文档可能仍偏 Phase 0–2 | reviewer / coding agent 可能依据旧计划做决策 | 增加 `ROADMAP.md` 或更新 implementation plan 阶段状态 | 不阻塞 |
| 18 | P3 | 测试数量声明可能过期 | README/CLAUDE 里提到测试数量，后续容易不一致 | 文档可信度下降 | 避免写死测试数量，或由 CI badge / pytest summary 证明 | 不阻塞 |

---

## 4. 重点风险详细说明

### 4.1 风险 3：缺少 GitHub Actions CI

#### 风险描述

当前项目 README 中声明 Phase 3 已完成，并列出完整的 acceptance 命令。但如果 GitHub 仓库没有 CI workflow，则外部 reviewer 无法在 GitHub 页面上看到这些命令是否真的通过。

#### 影响

- 多 Claude Code 会话协作时，容易出现某个会话修改代码后破坏基础链路但未被及时发现。
- Reviewer 只能依赖本地运行，缺少公共验收信号。
- README 中 “acceptance clean” 的可信度不足。

#### 建议修复

新增：

```text
.github/workflows/ci.yml
```

建议 CI 执行：

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
make accept
python scripts/run_eval.py --eval-dir evals/ --dry-run
```

#### 验收标准

- GitHub Actions 页面能看到 CI workflow。
- push / pull request 后自动运行。
- CI 通过时显示绿色状态。
- CI 失败时能指出失败命令。

---

### 4.2 风险 4：`mock_data/axi2ahb` 数据安全边界不清

#### 风险描述

当前 Phase 3 引入了 `mock_data/axi2ahb`，并在 README 中描述为 real AXI2AHB bridge project / URG parser demo。由于该仓库是 GitHub 上的公开仓库，如果该目录中包含真实公司项目的 coverage report、模块名、层级名、文件路径或测试名，可能构成 IP 泄露风险。

#### 影响

即使没有 RTL 源码，coverage report 也可能包含：

- 设计模块名；
- 层级结构；
- covergroup / coverpoint / bin 名称；
- 测试名；
- 文件路径；
- 功能特性名称；
- 未覆盖项分布。

这些信息足以暴露部分设计结构和验证意图。

#### 建议修复

在 README 和 `mock_data/axi2ahb/README.md` 中明确声明数据来源：

```text
The AXI2AHB URG report under mock_data/axi2ahb is public, synthetic, or sanitized demo data. It must not contain proprietary RTL source code, confidential file paths, private test names, customer project identifiers, or internal design hierarchy that is not approved for public sharing.
```

如果无法确认数据来源，则应：

1. 删除该目录；
2. 使用 synthetic URG-like sample；
3. 或对所有路径、模块名、测试名、coverpoint 名称做脱敏。

#### 验收标准

- README 明确说明 `axi2ahb` 数据是否 public / synthetic / sanitized。
- `mock_data/axi2ahb/README.md` 存在并说明数据边界。
- 仓库中不存在真实公司路径、用户名、项目代号、客户名称、内部 IP 名称。

---

### 4.3 风险 5：`cov_get_coverpoint_source` 能力描述可能被误解

#### 风险描述

Phase 3 已实现 URG coverage report parser，并可以生成 real coverage index demo。但当前 `cov_get_coverpoint_source` 仍然是 generated/mock source snippet，不读取真实 coverage model source file。

如果文档中只写 “Phase 3 URG parser complete”，用户可能误以为已经支持真实 coverage model source tracing。

#### 影响

- Claude Code 在 scenario generation 时可能给出不完整 evidence。
- 用户可能误认为工具已经能定位真实 coverpoint 定义源码。
- 后续需求范围容易膨胀，过早要求支持真实 SV source resolver。

#### 建议修复

在 README、CLAUDE.md、REVIEW_GUIDE.md 中明确：

```text
Phase 3 supports URG HTML report parsing and coverage index integration. It does not yet implement real coverage model source snippet resolution. cov_get_coverpoint_source currently returns generated/mock snippets based on parsed coverage metadata. A bounded source snippet resolver is deferred to a later phase.
```

#### 验收标准

- README 中 Phase 3 scope 明确包含 “not source resolver”。
- CLAUDE.md 中禁止 coding agent 将其误解为已实现真实源码追踪。
- REVIEW_GUIDE.md 中加入检查项。

---

### 4.4 风险 6：Eval runner 阶段口径不一致

#### 风险描述

部分文档将 eval runner 的 LLM execution mode 描述为 Phase 3+，而 Next Steps 中又将其放在 Phase 6。这会给 coding agent 造成错误信号。

#### 影响

- coding agent 可能在 Phase 3 或 Phase 4 过早实现 LLM execution eval。
- 可能引入不稳定的 agent-in-the-loop 测试逻辑。
- 可能影响 mock MVP 的确定性和 CI 稳定性。

#### 建议修复

统一所有文档中的口径：

```text
LLM execution mode is deferred to Phase 6.
Current eval runner supports dry-run validation only.
```

需要检查并修改：

- README.md
- evals/README.md
- CLAUDE.md
- REVIEW_GUIDE.md

#### 验收标准

执行：

```bash
grep -R "Phase 3+" README.md evals/README.md CLAUDE.md REVIEW_GUIDE.md
```

不应再出现将 LLM execution 放在 Phase 3+ 的表述。

---

### 4.5 风险 7：Phase 3 release-ready 缺少可见验收记录

#### 风险描述

静态 review 能看到代码和目录结构，但无法证明：

- 所有依赖可安装；
- 所有 Makefile target 可执行；
- tests 全部通过；
- eval dry-run 正常；
- MCP smoke test 正常；
- real index build 正常。

#### 影响

- README 的状态声明缺少运行时证据。
- 后续进入 Phase 4/5 时可能在旧问题上继续堆功能。
- reviewer 无法判断 Phase 3 是否真正 release-ready。

#### 建议修复

至少本地运行并记录以下命令结果：

```bash
python -m pip install -e ".[dev]"
make validate
make validate-gaps
make build-indexes
make build-real-index
make lint
make typecheck
make test
make smoke-server
make accept
python scripts/run_eval.py --eval-dir evals/ --dry-run
```

推荐将主要验收放入 GitHub Actions CI。

#### 验收标准

- 本地或 CI 显示完整命令通过。
- README 中的状态由 “Phase 3 Done” 改为更精确表述，例如：
  - `Phase 3 implemented, pending release validation`
  - 或在 CI 通过后恢复为 `Phase 3 release-ready`

---

### 4.6 风险 8：真实 URG parser 支持范围未充分限定

#### 风险描述

URG HTML 报告可能随 VCS/URG 版本、coverage 类型、命令选项、目录结构变化而变化。当前 parser 即使能解析 sample report，也不代表能支持所有真实 URG HTML 报告。

#### 影响

- 用户把不同版本的 URG report 丢进来时可能解析失败。
- parser 失败原因可能不清晰。
- 后续误判为 coverage 数据错误。

#### 建议修复

在文档中明确当前支持范围：

- 支持的 URG report 类型；
- 支持的 coverage metric；
- 支持的目录结构；
- 支持的 HTML 文件类型；
- 不支持的情况；
- parser 失败时的错误策略。

建议新增：

```text
docs/urg_parser_support_matrix.md
```

或在 `lib/urg_parser/README.md` 中添加 support matrix。

#### 验收标准

- 有文档说明支持与不支持范围。
- tests 中至少包含一个 unsupported case。
- parser 对 unsupported format 给出明确 warning 或 error，而不是 silent failure。

---

### 4.7 风险 9：`.mcp.json` 绑定本地 `.venv/bin/python`

#### 风险描述

当前 `.mcp.json` 如果直接绑定 `.venv/bin/python`，对单个开发者环境可用，但对其他同事可能不可用。

#### 影响

- 同事 clone 仓库后 MCP server 启动失败。
- 不同系统下 `.venv` 路径不同。
- 团队推广时需要额外解释。

#### 建议修复

新增：

```text
.mcp.json.example
```

并在 README 中说明：

1. 先创建 `.venv`；
2. 安装依赖；
3. 复制 `.mcp.json.example` 为 `.mcp.json`；
4. 按本地路径调整 Python command。

#### 验收标准

- `.mcp.json.example` 存在。
- README 有 “Claude Code MCP setup” 章节。
- `.mcp.json` 可以继续保留为本地开发默认，但文档应说明其环境假设。

---

### 4.8 风险 10：Project registry 尚未完善

#### 风险描述

当前 MCP tools 可能主要依赖 manifest path。对开发者来说可接受，但对团队用户来说，理想体验应是：

```text
project = dma_subsystem
```

而不是每次传完整 path。

#### 影响

- 使用门槛较高。
- Skill prompt 不够简洁。
- 多项目扩展时需要手动传 path。

#### 建议处理

后续阶段增加 project registry：

```text
projects.yaml
~/.cov_flow/projects.yaml
COV_FLOW_PROJECTS
```

示例：

```yaml
projects:
  dma_subsystem:
    manifest: mock_data/dma_subsystem/project_manifest.yaml
  axi2ahb:
    manifest: mock_data/axi2ahb/project_manifest.yaml
```

#### 验收标准

- MCP tools 支持 project id → manifest path resolution。
- README 提供 project registry 示例。
- 保持 manifest path 作为 fallback。

---

### 4.9 风险 11：Phase 4/5 边界容易被提前突破

#### 风险描述

当前 Phase 3 已经完成 URG parser，下一步 coding agent 容易直接进入：

- 真实 Verdi/VCS 接入；
- 真实 UVM testcase generation；
- 真实 simulation execution；
- FSDB wave analysis。

这些都属于高风险阶段，需要明确批准。

#### 影响

- 可能引入真实项目数据；
- 可能触发 EDA license / 权限问题；
- 可能破坏当前稳定 mock/Phase 3 flow。

#### 建议处理

在 CLAUDE.md 和 REVIEW_GUIDE.md 中明确：

```text
Phase 4/5 are prohibited unless the user explicitly approves a bounded work package.
```

#### 验收标准

- Phase 4/5 work package 必须单独提出；
- 不允许 coding agent 自行扩展；
- reviewer 必须检查是否越界。

---

### 4.10 风险 12：真实 coverage source resolver 缺失

#### 风险描述

当前可以从 URG report 解析 coverage gap，但还不能稳定定位真实 coverage model 中的 covergroup / coverpoint / bin 源码片段。

#### 影响

- evidence 链停留在 report 层面；
- scenario 生成缺少 coverage model source 细节；
- Claude Code 可能难以判断 coverpoint semantics。

#### 建议处理

后续实现 bounded source resolver：

```text
cov_get_coverpoint_source(project, gap_id)
  -> file + line range + snippet
```

必须具备：

- project root allowlist；
- max line count；
- max bytes；
- no full-file read；
- evidence_id；
- source path sanitization。

#### 验收标准

- 能读取小范围 source snippet；
- 不能读取全量文件；
- 有安全测试和 path traversal test。

---

### 4.11 风险 13：AXI2AHB coverage gap 数量较大，可能带来性能问题

#### 风险描述

Phase 3 demo 包含接近千级 coverage gaps。当前 MCP tools 和 tests 如果主要基于小 mock 数据，可能没有充分覆盖较大数据量下的查询性能。

#### 影响

- `cov_list_uncovered` 返回过大；
- Claude Code 上下文膨胀；
- eval / tests 运行变慢；
- truncation 行为不稳定。

#### 建议处理

增加：

- pagination；
- limit 参数；
- truncation behavior tests；
- max result size；
- sorted top-N query。

#### 验收标准

- `cov_list_uncovered(limit=20)` 默认只返回有限结果；
- 大数据集下 `truncated=true` 正确；
- tests 覆盖 982 gaps 或类似规模。

---

### 4.12 风险 14：MCP tool 输出 contract 需持续锁定

#### 风险描述

当前 MCP tools 使用统一 envelope。但随着后续 parser / source resolver / Verdi adapter 加入，不同工具可能返回结构漂移。

#### 影响

Claude Code 依赖稳定字段：

```text
ok
tool
project
result
evidence
truncated
next_actions
```

如果字段漂移，Skill workflow 会不稳定。

#### 建议处理

增加 contract tests：

```text
tests/test_tool_contracts.py
```

检查所有 MCP tools：

- 成功返回 envelope；
- error 返回 error envelope；
- evidence 格式一致；
- truncated 字段存在；
- next_actions 为 list。

#### 验收标准

每个 tool 都通过 contract test。

---

### 4.13 风险 15：“real project data”措辞容易引发误解

#### 风险描述

README 中如果同时出现：

```text
real AXI2AHB bridge project
```

和

```text
no real project data except URG demo
```

会给 reviewer 造成安全边界上的疑问。

#### 影响

- 对外 review 时容易被质疑；
- 用户不清楚是否可以公开分享；
- 后续贡献者可能放入真实数据。

#### 建议处理

统一措辞：

```text
sample / public / sanitized URG demo data
```

不要使用模糊的 “real project data”。

#### 验收标准

README、CLAUDE.md、REVIEW_GUIDE.md、mock_data/axi2ahb/README.md 口径一致。

---

### 4.14 风险 16：README 状态表可能过于乐观

#### 风险描述

README 直接标记 Phase 3 Done，但当前仍存在：

- parser scope 未充分说明；
- CI 未建立；
- source resolver 未实现；
- data security boundary 需确认。

#### 影响

用户可能误解为生产可用，而不是 Phase 3 demo / parser implementation。

#### 建议处理

更准确写法：

```text
Phase 3: Implemented, pending release validation
```

或者在 CI 通过且风险处理后标记：

```text
Phase 3: Release-ready
```

#### 验收标准

README 状态表反映真实成熟度。

---

### 4.15 风险 17：`implementation_plan.md` 可能落后于当前实现

#### 风险描述

项目推进到 Phase 3 后，早期 implementation plan 可能仍主要描述 Phase 0–2 的架构。

#### 影响

- reviewer 依据旧计划判断；
- coding agent 可能重复做已完成工作；
- Phase 3/4 roadmap 不清晰。

#### 建议处理

新增：

```text
ROADMAP.md
```

或更新 implementation plan 中的阶段状态。

建议 ROADMAP 包含：

- current phase；
- completed milestones；
- next allowed phase；
- disallowed scope；
- risk register；
- release checklist。

#### 验收标准

CLAUDE.md 指向 ROADMAP.md 作为当前阶段依据。

---

### 4.16 风险 18：测试数量声明可能过期

#### 风险描述

README / CLAUDE.md 如果写死测试数量，例如 “181 tests”，后续很容易过期。

#### 影响

- 文档可信度下降；
- reviewer 可能质疑状态；
- coding agent 可能修改文档而不是实际质量。

#### 建议处理

避免写死测试数量，改成：

```text
Test count is reported by pytest in CI.
```

或者仅由 CI badge / pytest summary 提供事实。

#### 验收标准

文档中不写死易过期的测试数量，或者明确由 CI 自动证明。

---

## 5. 推荐处理优先级

### 5.1 进入 Phase 4/5 前必须处理

| 优先级 | 风险编号 | 处理项 |
|---:|---:|---|
| 1 | 4 | 确认并说明 `axi2ahb` 数据是否 public / synthetic / sanitized |
| 2 | 7 | 本地或 CI 跑完整验收命令 |
| 3 | 6 | 统一 eval runner LLM execution 到 Phase 6 |
| 4 | 5 | 明确 `cov_get_coverpoint_source` 仍是 mock/generated snippet |
| 5 | 8 | 限定 URG parser 当前支持范围 |

### 5.2 团队推广前建议处理

| 优先级 | 风险编号 | 处理项 |
|---:|---:|---|
| 1 | 3 | 增加 GitHub Actions CI |
| 2 | 9 | 增加 `.mcp.json.example` 和 MCP setup 文档 |
| 3 | 13 | 增加大数据量 pagination / truncation tests |
| 4 | 14 | 增加 MCP tool contract tests |
| 5 | 15 | 统一 real/sample/sanitized data 措辞 |

### 5.3 可延后处理

| 风险编号 | 处理项 |
|---:|---|
| 10 | Project registry |
| 12 | 真实 coverage source resolver |
| 16 | README 状态成熟度措辞 |
| 17 | ROADMAP.md |
| 18 | 测试数量声明清理 |

---

## 6. 建议 Claude Code 本轮工作范围

### 6.1 本轮目标

本轮建议作为：

```text
Phase 3 hardening / release hygiene
```

本轮只处理风险收口，不进入 Phase 4 / Phase 5。

### 6.2 允许修改

```text
README.md
CLAUDE.md
REVIEW_GUIDE.md
evals/README.md
mock_data/axi2ahb/README.md
.github/workflows/ci.yml
.mcp.json.example
docs/urg_parser_support_matrix.md
tests/test_tool_contracts.py
tests/test_large_coverage_index_behavior.py
```

是否新增 tests 取决于现有结构，不要求一次性全部完成。

### 6.3 禁止修改 / 禁止新增

```text
不要实现真实 Verdi/VCS/KDB/NPI/VPI/FSDB 接入
不要实现真实 UVM testcase generation
不要读取或新增真实 RTL/FS/Reg/UVM/waveform 数据
不要扩展到 Phase 4/5/6
不要让 MCP tool 执行任意 shell command
不要把真实项目数据写进 Skill
```

---

## 7. 可直接复制给 Claude Code 的处理 Prompt

```text
当前目录：~/Desktop/AI/cov_flow

请阅读 RISK_REVIEW.md，并执行一次 Phase 3 hardening / release hygiene。

本轮目标：
处理当前 Phase 3 状态下的 P1/P2 风险，统一文档口径，明确数据安全边界，增加可验证性，并防止 coding agent 过早进入 Phase 4/5。

重点风险：
1. 缺少 GitHub Actions CI；
2. mock_data/axi2ahb 数据安全边界不清；
3. cov_get_coverpoint_source 容易被误解为真实 source resolver；
4. eval runner LLM execution 阶段口径不一致；
5. Phase 3 release-ready 缺少可见验收记录；
6. URG parser 支持范围未充分限定；
7. .mcp.json 对团队复用不够友好；
8. MCP tool envelope contract 需要测试保护。

允许新增/修改：
- README.md
- CLAUDE.md
- REVIEW_GUIDE.md
- evals/README.md
- mock_data/axi2ahb/README.md
- .github/workflows/ci.yml
- .mcp.json.example
- docs/urg_parser_support_matrix.md
- tests/test_tool_contracts.py
- tests/test_large_coverage_index_behavior.py
- RISK_REVIEW.md 如需补充

严格禁止：
1. 不要实现 Phase 4/5/6。
2. 不要接入真实 Verdi/VCS/KDB/NPI/VPI/FSDB。
3. 不要读取或新增真实公司 RTL/FS/Reg/UVM/coverage database/waveform。
4. 不要实现真实 UVM testcase generation。
5. 不要修改 URG parser 主逻辑，除非测试或文档更新确实需要。
6. 不要把真实项目数据写进 Skill。
7. 不要引入任意 shell command execution。

具体任务：
1. 新增或更新 GitHub Actions CI：
   - .github/workflows/ci.yml
   - 执行 pip install -e ".[dev]"
   - 执行 make accept
   - 执行 python scripts/run_eval.py --eval-dir evals/ --dry-run

2. 明确 mock_data/axi2ahb 的数据边界：
   - 新增或更新 mock_data/axi2ahb/README.md
   - README.md 中说明该数据必须是 public / synthetic / sanitized demo data
   - 如无法确认，标记为需要人工确认

3. 统一 eval runner 阶段口径：
   - README.md
   - evals/README.md
   - CLAUDE.md
   - REVIEW_GUIDE.md
   全部改为：LLM execution mode is deferred to Phase 6.

4. 明确 cov_get_coverpoint_source 当前能力边界：
   - 文档中说明 Phase 3 不包含真实 coverage model source snippet resolver
   - 当前 tool 返回 generated/mock source snippet
   - 真实 bounded source resolver 是后续阶段

5. 新增 URG parser support matrix：
   - docs/urg_parser_support_matrix.md
   - 说明当前支持的 URG HTML report 范围
   - 说明不支持的情况
   - 说明失败策略和 parser warnings

6. 增加 .mcp.json.example：
   - 说明如何配置 Claude Code MCP server
   - README 中补充 MCP setup 步骤

7. 如时间允许，增加 MCP tool contract tests：
   - tests/test_tool_contracts.py
   - 检查所有 MCP tool 成功/失败返回均包含统一 envelope 字段：
     ok, tool, project, result, evidence, truncated, next_actions
   - 不要求覆盖所有业务分支，但要锁定接口契约

8. 如时间允许，增加大 coverage index 行为测试：
   - tests/test_large_coverage_index_behavior.py
   - 检查 limit/truncated 行为
   - 防止 982 gaps 一次性返回过多内容

必须运行：
- python -m pip install -e ".[dev]"
- make validate
- make validate-gaps
- make build-indexes
- make build-real-index
- make test
- make smoke-server
- make accept
- python scripts/run_eval.py --eval-dir evals/ --dry-run

最终输出：
1. 修改/新增文件列表；
2. 每个风险编号的处理状态：fixed / documented / deferred / needs human confirmation；
3. 所有命令运行结果；
4. 是否可以标记为 Phase 3 release-ready；
5. 是否仍然禁止进入 Phase 4/5；
6. 下一步建议。
```

---

## 8. Phase 3 Release-ready 判断标准

只有满足以下条件后，才建议把当前仓库标记为 `Phase 3 release-ready`：

| 条件 | 要求 |
|---|---|
| 完整验收 | `make accept` 通过 |
| Eval dry-run | `python scripts/run_eval.py --eval-dir evals/ --dry-run` 通过 |
| 数据安全边界 | `mock_data/axi2ahb` 明确为 public / synthetic / sanitized |
| 文档一致性 | README / CLAUDE / REVIEW_GUIDE / evals README 阶段口径一致 |
| Source resolver 边界 | 明确 Phase 3 不包含真实 coverage model source resolver |
| URG parser 范围 | 有 support matrix 或等价说明 |
| CI | GitHub Actions 存在并通过，或本地验收记录明确 |
| Phase 边界 | Phase 4/5 仍然禁止，除非用户明确批准 |

---

## 9. 当前建议结论

当前仓库不应直接进入 Phase 4 / Phase 5。推荐下一步是：

```text
Phase 3 hardening / release hygiene
```

优先完成：

1. 数据安全边界说明；
2. 文档阶段口径统一；
3. CI / 本地验收记录；
4. URG parser 支持范围说明；
5. MCP tool contract 保护。

完成后，再评估是否进入：

```text
Phase 4: Coverage source resolver / UVM testcase generation planning
```

或：

```text
Phase 4: Verdi/VCS adapter skeleton planning
```

实际 Phase 4 方向需要单独审批，不建议让 coding agent 自行决定。
