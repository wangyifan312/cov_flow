**DV AI Coverage Closure Skill Pack**

公司内部复用方案设计文档（V2：实现细化版）

基于 Claude Code Agent + Skills + MCP 的数字 IC 验证覆盖率收敛提效方案

| **适用对象** | 公司内部数字 IC 验证团队、验证平台团队、CAD/EDA 支撑团队                                    |
|--------------|---------------------------------------------------------------------------------------------|
| **文档版本** | v1.0                                                                                        |
| **日期**     | 2026-05-21                                                                                  |
| **交付形态** | Claude Code Skill Pack + DV Context MCP Server + Project Context Indexer + Project Manifest |
| **文档用途** | 立项评审、方案评审、MVP 实施拆解、团队推广使用说明                                          |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>核心结论</strong></p>
<p>Skill 不应承载 RTL/FS/寄存器文档/UVM 环境等项目大数据。<br />
推荐将 Skill 定位为“验证团队的操作手册和任务流程”，将项目上下文通过 MCP
Server 与结构化索引按需暴露给 Claude Code Agent。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 文档目录

- 1\. 文档目的与范围

- 2\. 背景与问题定义

- 3\. 目标形态与设计原则

- 4\. 总体架构

- 5\. Skill Pack 产品化设计

- 6\. Project Manifest 规范

- 7\. DV Context MCP Server 设计

- 8\. Project Context Indexer 设计

- 9\. 上下文爆炸控制机制

- 10\. 标准工作流设计

- 11\. 输出模板与数据 Schema

- 12\. 安全、权限与人工评审机制

- 13\. MVP 实施路线

- 14\. 评价指标与验收标准

- 15\. 团队推广与使用指南

- 16\. 风险清单与应对策略

- 附录 A：示例 SKILL.md

- 附录 B：示例 Project Manifest

- 附录 C：常用提示词模板

- 附录 D：参考资料

- 18\. 实现分工总览：脚本 / MCP / LLM / Skill

- 19\. Offline Scripts 与 Indexer 实现设计

- 20\. DV Context MCP Server 实现设计

- 21\. Skill 与 Claude Code 实现设计

- 22\. 端到端执行链路与数据流

- 23\. MVP 工程 Backlog 与任务拆分

- 24\. 关键代码骨架示例

- 25\. 落地检查清单

# 1. 文档目的与范围

本文档用于定义一个面向公司内部数字 IC 验证团队的可复用 AI Skill Pack。该
Skill Pack 依赖 Claude Code Agent 执行任务，通过 MCP Server
和项目索引读取覆盖率、RTL、FS、寄存器、UVM
验证环境、仿真日志等上下文，帮助验证工程师完成覆盖率收敛中的分析、场景生成、case
生成和反馈闭环。

该方案关注工程化落地，不把目标设定为“AI 完全自动完成验证”，而是将 AI
Agent 定位为验证工程师的分析与生成助手，输出必须可审阅、可追溯、可回滚。

| **范围** | **包含**                                                                                                 | **不包含**                                  |
|----------|----------------------------------------------------------------------------------------------------------|---------------------------------------------|
| 首期功能 | Functional coverage gap triage、scenario card 生成、UVM sequence/test patch 初稿、coverage diff 反馈分析 | 全芯片 signoff、自动 waiver、无审核提交代码 |
| 输入方式 | project manifest、coverage report id/path、block/feature scope、gap id、任务模式                         | 全量 RTL/FS/TB 文本直接塞入 prompt          |
| 执行主体 | Claude Code Agent + Skills + MCP tools                                                                   | EDA 工具原生 MCP Server 的强依赖            |
| 项目数据 | 通过索引和 MCP 按需查询                                                                                  | 作为 Skill 内容打包分发                     |

# 2. 背景与问题定义

## 2.1 覆盖率收敛的工程痛点

- Regression
  后期的未覆盖项往往集中在低概率随机场景、配置组合、状态机边界、协议异常路径、cross
  组合和采样条件问题上，单靠人工逐项排查成本较高。

- 覆盖率报告、coverage model、FS、寄存器文档、RTL 和 UVM
  环境之间缺乏统一可检索链路，验证工程师需要跨多个系统手工定位。

- 未覆盖不一定等于缺 case，可能来自约束过严、寄存器配置缺失、coverage
  model 错误、monitor 采样时机问题、RTL unreachable 或 spec illegal
  场景。

- AI Agent
  如果直接读取全量工程文件，会出现上下文爆炸、检索噪声大、生成代码幻觉、IP
  暴露范围过大等问题。

## 2.2 目标用户与典型任务

| **角色**                       | **典型任务**                                        | **期望结果**                            |
|--------------------------------|-----------------------------------------------------|-----------------------------------------|
| Block DV Engineer              | 分析 block-level coverage gap，补 directed sequence | 更快获得 gap 分类、补场景建议、代码初稿 |
| DV Lead                        | 评估 coverage closure 进度和难点                    | 按 feature/gap 类型聚合的 triage report |
| Verification Platform Engineer | 维护 UVM 模板、MCP 工具、索引器                     | 使 Skill Pack 可跨项目复用              |
| CAD/EDA Support                | 接入 Verdi/VCS/KDB/coverage database                | 提供稳定的上下文查询 API                |

# 3. 目标形态与设计原则

## 3.1 最终产品形态

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>产品定义</strong></p>
<p>DV AI Coverage Closure Kit = Skill Pack + DV Context MCP Server +
Project Context Indexer + Project Manifest + Eval Suite。<br />
其中 Skill Pack 面向验证工程师使用，MCP Server 和 Indexer 面向平台工程与
CAD/EDA 支撑团队维护。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

| **组件**                | **职责**                                                     | **主要维护者**          |
|-------------------------|--------------------------------------------------------------|-------------------------|
| Skill Pack              | 固化覆盖率收敛流程、工具调用策略、输出模板、review checklist | 验证方法学/平台团队     |
| DV Context MCP Server   | 提供 coverage/RTL/spec/reg/TB/sim/wave 查询工具              | 平台团队 + CAD/EDA 支撑 |
| Project Context Indexer | 从原始项目数据生成结构化索引和摘要                           | 平台团队                |
| Project Manifest        | 声明项目数据位置、索引路径、命令模板和策略开关               | 各项目 DV owner         |
| Eval Suite              | 验证 skill 可触发、上下文受控、输出可用、生成代码质量        | 平台团队 + 使用团队     |

## 3.2 核心设计原则

1.  Skill 不携带项目大数据，只携带任务方法、规则、模板和工具调用策略。

2.  Agent 不读取全量 RTL/FS/TB，只围绕目标 gap 进行按需查询。

3.  MCP tool 默认返回 summary，只有在需要证据或生成代码时才 expand 到
    source snippet。

4.  每个输出必须可追溯：gap → coverage source → spec/register/RTL/TB
    evidence → scenario/testcase → coverage diff。

5.  生成代码必须基于已有 base test/sequence/config knob，不允许凭空创造
    UVM 组件或路径。

6.  任何 waiver、unreachable 结论、主干代码修改都必须由验证工程师确认。

# 4. 总体架构

总体架构采用“Skill 编排 + MCP 工具 + 项目索引 +
原始数据”的分层模式。Claude Code Agent 负责理解任务和生成结果，Skill
Pack 负责约束流程与输出，MCP Server 负责查询，Indexer
负责把大规模项目数据结构化。

<img src="/mnt/data/dv_ai_coverage_md_assets/media/image1.png"
style="width:6.6in;height:3.8285in" />

图 1 DV AI Coverage Closure Skill Pack 总体架构

## 4.1 与直接长上下文输入的区别

| **方式**               | **优点**                         | **问题/限制**                                | **本方案选择** |
|------------------------|----------------------------------|----------------------------------------------|----------------|
| 直接上传全量 RTL/FS/TB | 启动快，无需基础设施             | 上下文爆炸、隐私面扩大、噪声高、不可复用     | 不推荐         |
| Skill 内置项目知识     | 表面上便于复用                   | Skill 变成数据仓库，版本失控，跨项目不可维护 | 禁止           |
| Skill + MCP + Index    | 上下文受控、可追溯、可跨项目扩展 | 需要建设索引器和工具层                       | 推荐           |

# 5. Skill Pack 产品化设计

Skill Pack 应采用主 Skill + 专业子 Skill 的组合。主 Skill
负责入口和编排；子 Skill 专注于 triage、scenario、testcase、feedback
等单一任务，避免一个 Skill 过大、过宽。

## 5.1 推荐目录结构

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>dv-coverage-closure-skill-pack/<br />
README.md<br />
CHANGELOG.md<br />
SECURITY.md<br />
skills/<br />
dv-coverage-closure/<br />
SKILL.md<br />
references/<br />
workflow.md<br />
gap_classification.md<br />
scenario_card_schema.md<br />
testcase_generation_rules.md<br />
review_checklist.md<br />
prompt_examples.md<br />
scripts/<br />
validate_manifest.py<br />
validate_scenario_card.py<br />
validate_patch_metadata.py<br />
dv-coverage-gap-triage/<br />
SKILL.md<br />
references/<br />
triage_policy.md<br />
gap_priority_rules.md<br />
unreachable_heuristics.md<br />
dv-coverage-scenario-generation/<br />
SKILL.md<br />
references/<br />
scenario_patterns.md<br />
protocol_scenario_templates.md<br />
dv-testcase-generation/<br />
SKILL.md<br />
references/<br />
uvm_generation_rules.md<br />
patch_rules.md<br />
compile_check_rules.md<br />
dv-simulation-feedback/<br />
SKILL.md<br />
references/<br />
coverage_diff_rules.md<br />
log_analysis_rules.md<br />
mcp/<br />
dv_context_server/<br />
tools/<br />
coverage_tools.py<br />
rtl_tools.py<br />
spec_tools.py<br />
register_tools.py<br />
tb_tools.py<br />
sim_tools.py<br />
schemas/<br />
project_manifest.schema.json<br />
coverage_gap.schema.json<br />
scenario_card.schema.json<br />
testcase_patch.schema.json<br />
feedback_report.schema.json<br />
examples/<br />
evals/</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 5.2 主 Skill：dv-coverage-closure

| **项目** | **内容**                                                                            |
|----------|-------------------------------------------------------------------------------------|
| 定位     | 统一入口和任务编排器                                                                |
| 触发场景 | 用户要求分析 coverage report、覆盖率收敛、生成场景、生成 case、分析 coverage diff   |
| 输入     | project id/manifest、regression id/report path、scope、task mode                    |
| 输出     | triage report、scenario cards、testcase generation plan、UVM patch、feedback report |
| 关键规则 | 不加载全量文件；先 triage 再 context routing；所有结论给 evidence 和 confidence     |

## 5.3 子 Skill 划分

| **子 Skill**                    | **职责**                                         | **必需输入**                                             | **主要输出**              |
|---------------------------------|--------------------------------------------------|----------------------------------------------------------|---------------------------|
| dv-coverage-gap-triage          | 缺口初筛、分类、优先级排序、下一步上下文需求判断 | gap list、coverage model snippet、history、waiver status | Triage report             |
| dv-coverage-scenario-generation | 把未覆盖点转为验证场景                           | 单个 gap、相关 spec/reg/RTL/TB 摘要                      | Scenario card             |
| dv-testcase-generation          | 基于场景卡和已有模板生成 UVM patch               | scenario card、base test/sequence 模板、config knob      | sequence/test/config diff |
| dv-simulation-feedback          | 分析仿真与 coverage diff，判断是否关闭 gap       | test result、log summary、coverage diff、target gap      | Feedback report           |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>Skill 编写边界</strong></p>
<p>Skill 文件中只写流程、工具调用策略、输出格式、few-shot
示例和门禁规则。<br />
不得把项目级 RTL、FS、寄存器文档、UVM 环境代码打包进 Skill。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 6. Project Manifest 规范

Project Manifest
是团队复用的关键入口。它描述一个项目的数据位置、索引路径、默认回归、仿真命令模板、权限策略和生成代码限制。验证工程师使用
Skill 时只需提供 project id 或 manifest 路径，Agent
即可按规范发现上下文来源。

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>project: dma_subsystem<br />
owner_team: dv_dma<br />
top_instance: tb_top.u_dut.u_dma<br />
<br />
coverage:<br />
default_report_id: latest<br />
reports_root: /proj/dma/regression/coverage<br />
format: urg_html<br />
coverage_model_root: /proj/dma/tb/cov<br />
<br />
rtl:<br />
filelist: /proj/dma/filelist/rtl.f<br />
design_db:<br />
type: verdi_kdb<br />
path: /proj/dma/sim/simv.daidir<br />
index_path: /proj/dma/.dv_ai_index/rtl<br />
<br />
spec:<br />
fs:<br />
path: /proj/dma/doc/dma_fs.pdf<br />
index_path: /proj/dma/.dv_ai_index/spec/dma_fs<br />
micro_arch:<br />
path: /proj/dma/doc/dma_uarch.docx<br />
index_path: /proj/dma/.dv_ai_index/spec/uarch<br />
<br />
registers:<br />
source:<br />
type: ipxact<br />
path: /proj/dma/reg/dma_regs.xml<br />
ral_root: /proj/dma/tb/reg_model<br />
index_path: /proj/dma/.dv_ai_index/registers<br />
<br />
testbench:<br />
type: uvm<br />
env_root: /proj/dma/tb<br />
base_test: dma_base_test<br />
sequence_root: /proj/dma/tb/sequences<br />
index_path: /proj/dma/.dv_ai_index/tb<br />
<br />
simulation:<br />
compile_cmd_template: make compile TEST={test}<br />
run_cmd_template: make run TEST={test} SEED={seed}<br />
coverage_cmd_template: make cov TEST={test}<br />
<br />
policy:<br />
allow_direct_file_modification: false<br />
allow_running_simulation: true<br />
require_human_review_before_commit: true</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

| **字段**       | **说明**                                                  | **首期是否必需** |
|----------------|-----------------------------------------------------------|------------------|
| project        | 项目唯一标识，供 MCP tools 定位索引                       | 必需             |
| top_instance   | DUT 或 block 的默认顶层 instance path                     | 必需             |
| coverage       | coverage report 和 coverage model 根路径                  | 必需             |
| rtl.design_db  | Verdi KDB/VCS elaboration DB 或其他设计数据库路径         | 建议必需         |
| spec/registers | FS、micro-architecture、寄存器/RAL 数据源与索引           | 必需             |
| testbench      | UVM env、base test、sequence root、TB 索引路径            | 必需             |
| simulation     | compile/run/cov 命令模板                                  | 反馈闭环阶段必需 |
| policy         | 是否允许直接改文件、是否允许运行仿真、是否需要人工 review | 必需             |

# 7. DV Context MCP Server 设计

MCP Server 是 Agent
与内部项目数据之间的受控接口。它不应简单返回大段原文，而应提供结构化、可审计、可限权、可摘要的工具调用结果。

## 7.1 工具分组

| **工具组**       | **代表工具**                                                                             | **用途**                                                        |
|------------------|------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| Coverage Tools   | cov_list_uncovered、cov_get_gap_detail、cov_get_coverpoint_source、cov_get_coverage_diff | 读取 gap、hit history、coverage source、diff                    |
| RTL Tools        | rtl_get_instance_info、rtl_find_signal、rtl_trace_fanin、rtl_get_source_snippet          | 按需查询 elaborated design 层级、信号、source map、fanin/fanout |
| Spec Tools       | spec_search、spec_get_section、spec_find_feature                                         | 检索 FS/uArch 中的相关 feature、状态机、协议规则                |
| Register Tools   | reg_find_field、reg_find_fields_affecting_feature、reg_get_ral_path                      | 定位寄存器字段、配置依赖、RAL 访问路径                          |
| TB Tools         | tb_find_sequence、tb_get_base_test_template、tb_find_config_knob、tb_find_constraint     | 复用现有 UVM 模板、sequence、constraint 和 config knob          |
| Simulation Tools | sim_run_targeted_test、sim_search_log、sim_get_coverage_diff、wave_check_condition       | 执行或分析定向仿真、日志和 coverage diff                        |

## 7.2 工具返回规范

每个 MCP 工具默认返回
summary，不直接返回全量文件。需要原文证据时，必须通过 file + line range
扩展片段。

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>{<br />
"query": "linked list descriptor mode",<br />
"matches": [<br />
{<br />
"type": "register_field",<br />
"name": "DMA_CFG.LL_MODE_EN",<br />
"relevance": 0.92,<br />
"summary": "Enables linked-list descriptor mode",<br />
"source": "reg/dma_reg.yaml"<br />
},<br />
{<br />
"type": "rtl_signal",<br />
"name": "u_dma.u_desc_parser.ll_mode_en",<br />
"relevance": 0.88,<br />
"summary": "Controls transition from NORMAL_DESC to LINK_DESC",<br />
"source": "rtl/dma_desc_parser.sv:144"<br />
}<br />
]<br />
}</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>工程建议</strong></p>
<p>MCP Server
应把权限、路径白名单、日志审计、返回大小限制和敏感信息过滤作为基础能力。Claude
Code Agent 只看到必要摘要和片段，而不是原始数据库本体。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 8. Project Context Indexer 设计

Indexer 是解决上下文爆炸的工程基础。它在 Agent
执行前离线处理原始数据，把大文件、大代码库、大覆盖报告变成可查询的结构化索引。

| **索引类型**       | **输入**                                                     | **输出**                                                                                  |
|--------------------|--------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| Coverage Index     | coverage report、coverage model、coverage history、waiver DB | gap list、coverpoint source map、hit history、coverage clustering                         |
| RTL Design Index   | RTL source、Verdi KDB/VCS elaboration DB                     | instance hierarchy、signal index、source map、parameter override、fanin/fanout、FSM index |
| Spec Index         | FS、uArch、protocol spec                                     | feature index、section summary、state machine summary、error scenario summary             |
| Register Index     | IP-XACT、CSV/YAML/Excel、RAL model                           | reg/field DB、field-to-feature、field-to-RTL、RAL path                                    |
| TB Index           | UVM env、sequence、base test、constraint、config object      | sequence summary、test mapping、config knob、constraint index、factory override           |
| Sim/Wave/Log Index | regression log、sim log、FSDB/VCD、coverage diff             | failure summary、signal transition summary、sample condition summary                      |

## 8.1 RTL 索引建议

对 RTL 层级和 elaboration context，推荐优先使用 VCS/Verdi
产生的设计数据库导出结构化信息，而不是只做文本 grep。原因是 coverage
closure 需要 generate 展开、parameter override、interface 连接、真实
instance path 等 elaborated design 信息。

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th># 推荐流程示意，具体命令以公司工具版本和 CAD 规范为准<br />
vcs -full64 -sverilog -f filelist.f -top tb_top -debug_access+all -kdb
-l compile.log<br />
verdi -dbdir simv.daidir -nologo -nogui -play
export_design_context.tcl<br />
<br />
# 目标产物<br />
design_context.json<br />
hierarchy.json<br />
signal_index.json<br />
source_map.json<br />
fanin_fanout_graph.json</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 9. 上下文爆炸控制机制

上下文控制不是简单扩大模型上下文窗口，而是通过 context
routing、摘要优先、逐级展开和 token budget
约束来保证每次任务只携带必要信息。

## 9.1 Context Routing

每个 coverage gap 先被分类，再决定需要哪些上下文。不同类型的 gap
需要不同数据源。

| **Gap 类型**                | **优先上下文**                                        | **通常不需要** |
|-----------------------------|-------------------------------------------------------|----------------|
| coverpoint/bin 未 hit       | coverage model、FS、register、已有 sequence           | 全量 RTL       |
| cross 未 hit                | coverage model、constraint、test history、配置组合    | 全量 FS        |
| FSM state/transition 未 hit | RTL FSM、FS 状态机、config、sequence                  | 全量 UVM env   |
| branch/condition 未 hit     | RTL fanin、register field、formal/unreachability 证据 | 所有 testcase  |
| covergroup 未 sample        | monitor、采样条件、simulation log/wave                | 全量寄存器文档 |
| feature 完全未覆盖          | vPlan/FS、register、test index、coverage clustering   | 全量波形       |

## 9.2 上下文预算

| **上下文类型**         | **单 gap 建议预算** | **说明**                                                        |
|------------------------|---------------------|-----------------------------------------------------------------|
| Coverage gap detail    | 1-2 KB              | gap id、covergroup、coverpoint、bin、hit count、source location |
| Coverage model snippet | 3-5 KB              | 只取相关 covergroup/coverpoint/bin                              |
| Spec sections          | 5-10 KB             | 只取相关 feature 的摘要和必要原文                               |
| Register fields        | 2-4 KB              | 字段描述、reset、access、RAL path                               |
| RTL snippets           | 5-15 KB             | 只取相关信号和 fanin/fanout 的片段                              |
| TB templates           | 5-15 KB             | 只取 base test/sequence/config knob 相关片段                    |
| History/log summary    | 2-5 KB              | hit history、失败摘要、coverage diff 摘要                       |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>硬性限制</strong></p>
<p>单个 gap 的正常上下文应控制在 20-50 KB；复杂 gap 最多 100
KB。禁止一次性读取 MB 级 RTL、FS、UVM 或波形数据。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 10. 标准工作流设计

公司内部同事应通过固定工作流使用 Skill，而不是自行编写复杂
prompt。每个工作流有固定输入、工具调用路径、输出模板和门禁条件。

<img src="/mnt/data/dv_ai_coverage_md_assets/media/image2.png"
style="width:6.6in;height:3.04893in" />

图 2 覆盖率收敛标准工作流

## 10.1 工作流 A：Coverage Triage

| **项目** | **内容**                                                                                  |
|----------|-------------------------------------------------------------------------------------------|
| 用户输入 | 项目、回归、scope、coverage 类型、top N                                                   |
| 工具调用 | cov_list_uncovered → cov_get_gap_detail → cov_get_coverpoint_source → cov_get_hit_history |
| 输出     | gap 分类、优先级、根因假设、下一步动作                                                    |
| 禁止     | 生成代码、直接 waiver、读取全量 RTL                                                       |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>用户示例：<br />
使用 dv-coverage-closure，对 dma 项目 latest regression 做 functional
coverage triage。<br />
范围：u_dma。输出 top 20 gaps。不要修改代码。</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 10.2 工作流 B：Scenario Card Generation

| **项目** | **内容**                                                                                                                                                         |
|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 用户输入 | project + gap id                                                                                                                                                 |
| 工具调用 | cov_get_gap_detail → cov_get_coverpoint_source → spec_search → reg_find_fields_affecting_feature → tb_get_existing_tests_for_feature → rtl_trace_fanin（必要时） |
| 输出     | scenario card：目标覆盖、语义解释、required config、stimulus、expected behavior、reuse plan、confidence、risk                                                    |
| 门禁     | 没有足够 evidence 时必须降低 confidence 或列出 open questions                                                                                                    |

## 10.3 工作流 C：UVM Testcase/Sequence Generation

| **项目** | **内容**                                                                                                                                |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------|
| 用户输入 | project + gap id 或 scenario card                                                                                                       |
| 工具调用 | tb_get_base_test_template → tb_get_existing_tests_for_feature → tb_get_sequence_source_snippet → tb_find_config_knob → reg_get_ral_path |
| 输出     | 最小 patch、新增文件、compile/run 命令、coverage target mapping、review checklist                                                       |
| 门禁     | 必须复用已有模板；不允许直接改主干；不允许编造不存在的 UVM 组件                                                                         |

## 10.4 工作流 D：Simulation Feedback

| **项目** | **内容**                                                                                   |
|----------|--------------------------------------------------------------------------------------------|
| 用户输入 | project + test name + target gap                                                           |
| 工具调用 | sim_get_test_result → sim_search_log → sim_get_coverage_diff → cov_get_gap_detail          |
| 输出     | compile/sim 结果、hit count 变化、是否关闭、下一轮建议                                     |
| 门禁     | 如果 test 没 hit 目标 coverage，必须区分激励没到、配置没开、采样条件没满足、仿真失败等原因 |

# 11. 输出模板与数据 Schema

## 11.1 Coverage Gap Triage Report

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th># Coverage Gap Triage Report<br />
<br />
Project: dma_subsystem<br />
Regression: latest<br />
Scope: tb_top.u_dut.u_dma<br />
Coverage Type: functional<br />
<br />
| Rank | Gap ID | Coverpoint | Bin | Classification | Priority |
Recommended Action |<br />
|---|---|---|---|---|---|---|<br />
| 1 | GAP_0012 | desc_mode_cp | linked_list | Config Missing + Missing
Stimulus | P0 | Generate directed linked-list descriptor scenario
|<br />
<br />
Evidence:<br />
- Coverage source: tb/cov/dma_cov.sv:88-105<br />
- Related spec: DMA FS Section 4.3 Linked-list descriptor mode<br />
- Related register: DMA_CFG.LL_MODE_EN<br />
- Existing tests: dma_normal_desc_test, dma_single_desc_random_test</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 11.2 Scenario Card Schema

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>gap_id: GAP_0012<br />
target_coverage:<br />
covergroup: dma_desc_cg<br />
coverpoint: desc_mode_cp<br />
bin: linked_list<br />
classification: Config Missing + Missing Stimulus<br />
semantic_interpretation: &gt;<br />
Linked-list descriptor mode has not been exercised. The scenario
requires enabling<br />
linked-list mode and providing a descriptor with a non-zero next
pointer.<br />
required_config:<br />
- register: DMA_CFG.LL_MODE_EN<br />
value: 1<br />
- descriptor_field: next_ptr<br />
constraint: non_zero<br />
stimulus:<br />
- program descriptor base address<br />
- build two linked descriptors<br />
- start DMA channel<br />
expected_behavior:<br />
- descriptor parser enters LINK_DESC state<br />
- next descriptor is fetched<br />
- completion interrupt is generated<br />
tb_reuse:<br />
base_test: dma_base_test<br />
candidate_sequence: dma_desc_base_seq<br />
confidence: medium<br />
risk:<br />
- confirm linked-list mode is enabled in current build
configuration</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 11.3 Generated Patch Metadata

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>patch_id: PATCH_GAP_0012_001<br />
gap_id: GAP_0012<br />
new_files:<br />
- tb/sequences/dma_linked_list_desc_seq.sv<br />
- tb/tests/dma_linked_list_desc_test.sv<br />
modified_files: []<br />
base_reuse:<br />
base_test: dma_base_test<br />
base_sequence: dma_desc_base_seq<br />
compile_command: make compile TEST=dma_linked_list_desc_test<br />
run_command: make run TEST=dma_linked_list_desc_test SEED=1<br />
coverage_target:<br />
- dma_desc_cg.desc_mode_cp.linked_list<br />
review_checklist:<br />
- confirm RAL path for DMA_CFG.LL_MODE_EN<br />
- confirm descriptor memory allocation helper<br />
- confirm sequence starts on correct virtual sequencer</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 12. 安全、权限与人工评审机制

IC 项目数据属于高敏感
IP。方案必须把安全和可审计作为默认设计，而不是后续补丁。

| **风险**                          | **控制措施**                                                                    |
|-----------------------------------|---------------------------------------------------------------------------------|
| 模型读取过多源码或文档            | MCP 工具做路径白名单、返回大小限制、summary-first、按 line range 展开           |
| 生成代码误改公共环境              | 默认只输出 diff 或新文件；manifest policy 禁止直接修改；需要人工确认            |
| 错误 waiver 或 unreachable 判断   | Skill 明确禁止自动 waiver；unreachable 仅能标记为 candidate，需 formal/人工确认 |
| Prompt injection 或文档中恶意指令 | MCP Server 对文档内容做数据/指令隔离，Agent 只把检索结果当证据，不当系统指令    |
| 跨项目数据泄露                    | project-level 权限隔离、审计日志、最小权限访问                                  |
| 工具运行破坏工作区                | 仿真/脚本默认在 sandbox/worktree 执行，提交前人工 review                        |

# 13. MVP 实施路线

建议先在一个 block-level UVM 项目上落地 MVP，验证 Skill Pack 的可用性和
ROI，再扩展到更多项目。

| **阶段**                | **目标**                    | **交付物**                                                        | **验收标准**                           |
|-------------------------|-----------------------------|-------------------------------------------------------------------|----------------------------------------|
| 阶段 0：项目接入        | 定义 manifest，整理数据路径 | project_manifest.yaml、schema、validate_manifest.py               | 一个试点 block 能通过 manifest 校验    |
| 阶段 1：Coverage Tools  | 解析 report 并查询 gap      | cov_list_uncovered、cov_get_gap_detail、cov_get_coverpoint_source | Top gaps 可正确结构化提取              |
| 阶段 2：Triage Skill    | 缺口分类和优先级排序        | dv-coverage-closure、dv-coverage-gap-triage                       | 工程师认可 top 20 gap 分类多数有效     |
| 阶段 3：Scenario Skill  | 生成 scenario card          | spec/reg/tb/rtl summary tools、scenario template                  | 至少 5-10 个 scenario 可进入 case 生成 |
| 阶段 4：Case Generation | 生成 UVM patch 初稿         | dv-testcase-generation、patch metadata                            | 人工小改后可编译运行                   |
| 阶段 5：Feedback Loop   | 分析 coverage diff          | sim tools、feedback report                                        | 形成一次完整闭环                       |

# 14. 评价指标与验收标准

| **类别** | **指标**                    | **建议目标**                         |
|----------|-----------------------------|--------------------------------------|
| 效率     | coverage gap 初筛时间       | 相比纯人工下降 50%+                  |
| 效率     | 场景生成时间                | 单 gap 由 30-60 分钟下降到 5-15 分钟 |
| 质量     | gap 分类可接受率            | MVP 阶段 \>70%                       |
| 质量     | scenario card 有用率        | MVP 阶段 \>60%                       |
| 代码     | 生成代码编译通过率          | MVP 阶段 40-60%，迭代后 \>70%        |
| 覆盖     | 生成 case 命中目标 gap 比例 | MVP 阶段 30-50%，迭代后逐步提升      |
| 安全     | 未授权读取全量大文件次数    | 0                                    |
| 流程     | 生成结果可追溯率            | 100% 必须包含 evidence 链路          |

# 15. 团队推广与使用指南

内部推广的关键是降低同事的使用门槛。用户不应学习复杂 prompt
engineering，而应使用固定任务模板。

| **任务**   | **推荐输入模板**                                                                                                                                         |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| 覆盖率初筛 | 使用 dv-coverage-closure。项目：{project}；回归：{regression_id}；范围：{scope}；任务：分析 top {N} uncovered functional coverage gaps；不要修改代码。   |
| 生成场景   | 使用 dv-coverage-scenario-generation。项目：{project}；Gap ID：{gap_id}；任务：生成 scenario card；关联 coverage model、FS、寄存器、RTL、已有 sequence。 |
| 生成 case  | 使用 dv-testcase-generation。项目：{project}；Gap ID：{gap_id}；Scenario card：{path}；任务：生成 UVM sequence/test patch；不要直接改文件。              |
| 反馈分析   | 使用 dv-simulation-feedback。项目：{project}；Test：{test_name}；目标 Gap：{gap_id}；任务：分析 sim log 和 coverage diff。                               |

# 16. 风险清单与应对策略

| **风险**                   | **影响**                | **应对策略**                                                                |
|----------------------------|-------------------------|-----------------------------------------------------------------------------|
| coverage model 命名不规范  | Agent 无法理解 bin 语义 | 推动 coverage naming guideline；引入 vPlan/FS 关联；必要时人工标注 few-shot |
| UVM 环境复杂，生成代码易错 | 编译失败、路径错误      | 强制基于已有 base sequence/test；生成前先查模板；输出 review checklist      |
| 未覆盖点不可达             | 浪费补 case 时间        | 设置 unreachable candidate 分类；接 formal/人工 review；不自动 waiver       |
| MCP 工具返回过多内容       | 上下文爆炸、噪声大      | 工具层做 summary-first、大小限制、line range 扩展                           |
| 不同项目风格差异大         | 跨项目泛化差            | 通过 manifest、TB index 和模板适配，每个项目提供最小接入包                  |
| 同事使用方式不统一         | 结果不稳定              | 提供固定 prompt 模板、README、eval suite 和示例项目                         |

# 17. 下一步行动建议

1\. 选择一个 block-level UVM 项目作为试点，优先选择 coverage model
和寄存器文档较规范的模块。

2\. 定义并冻结 project_manifest.schema.json，完成试点项目 manifest。

3\. 实现 coverage report parser 和 coverage MCP tools，先跑通 top gaps
结构化提取。

4\. 编写 dv-coverage-closure 和 dv-coverage-gap-triage 两个最小
Skill，先只做 triage report。

5\. 接入 spec/register/TB index，升级到 scenario card 生成。

6\. 以人工 review 模式生成 UVM patch，不直接修改主干。

7\. 建立 eval suite，每次 Skill 或 MCP 工具更新后跑回归评估。

# 附录 A：示例 SKILL.md

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>---<br />
name: dv-coverage-closure<br />
description: Use this skill for digital IC verification coverage closure
workflows. It analyzes coverage gaps, retrieves minimal
RTL/spec/register/testbench context through DV MCP tools, classifies
uncovered items, proposes missing verification scenarios, and optionally
generates UVM testcase or sequence patches with human review.<br />
---<br />
<br />
# DV Coverage Closure Skill<br />
<br />
## Purpose<br />
Help digital IC verification engineers close coverage gaps using a
structured AI-assisted workflow.<br />
<br />
## Core Principle<br />
Do not request or load full RTL, full FS documents, full register
manuals, or full UVM environments.<br />
Use project manifests, MCP tools, indexes, summaries, and source
snippets.<br />
<br />
## Required Minimal Inputs<br />
- project id or project_manifest path<br />
- regression id or coverage report path<br />
- scope: block, subsystem, feature, or coverage group<br />
- task mode: triage, scenario, generate-case, feedback<br />
<br />
## Standard Workflow<br />
1. Load the project manifest.<br />
2. Validate available context sources.<br />
3. Query coverage gaps.<br />
4. Classify gap type and priority.<br />
5. Decide required context by gap type.<br />
6. Retrieve only minimal context through MCP tools.<br />
7. Produce a triage report, scenario card, testcase patch, or feedback
report.<br />
8. Never modify source files without explicit user approval.<br />
9. Always include traceability: gap -&gt; evidence -&gt;
recommendation.<br />
<br />
## Safety Rules<br />
- Do not mark a gap as waived automatically.<br />
- Do not claim RTL unreachable without formal evidence or engineer
confirmation.<br />
- Do not invent UVM components.<br />
- Generated code must be presented as patch or new file.</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 附录 B：示例 Project Manifest

可直接参考第 6 节 YAML 示例。实际落地时建议用 JSON Schema/YAML Schema 做
CI 校验，并要求每个试点项目提交 manifest PR。

# 附录 C：常用提示词模板

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th># Coverage triage<br />
使用 dv-coverage-closure。<br />
项目：{project}<br />
回归：{regression_id}<br />
范围：{scope}<br />
任务：分析 top {N} uncovered functional coverage gaps。<br />
要求：不修改代码；输出 gap 分类、优先级、是否适合生成 case
和下一步建议。<br />
<br />
# Scenario generation<br />
使用 dv-coverage-scenario-generation。<br />
项目：{project}<br />
Gap ID：{gap_id}<br />
任务：生成 scenario card。<br />
要求：关联 coverage model、FS、寄存器、RTL、已有 sequence；输出 required
config、stimulus、expected behavior、confidence。<br />
<br />
# Testcase generation<br />
使用 dv-testcase-generation。<br />
项目：{project}<br />
Gap ID：{gap_id}<br />
Scenario card：{scenario_card_path}<br />
任务：生成 UVM sequence/test patch。<br />
要求：复用已有 base sequence；不直接修改文件；输出 diff、compile/run
命令和目标 coverage。<br />
<br />
# Feedback analysis<br />
使用 dv-simulation-feedback。<br />
项目：{project}<br />
Test：{test_name}<br />
目标 Gap：{gap_id}<br />
任务：分析 sim log 和 coverage diff，判断 gap 是否关闭。</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 附录 D：参考资料

\[1\] Anthropic Agent Skills 工程说明：说明 Skills 使用 progressive
disclosure，让模型按需加载 SKILL.md 与附属资源。
[<u>https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills</u>](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

\[2\] Anthropic Skills 公共仓库：说明 Skills 是包含
instructions、scripts 和 resources 的文件夹，供 Claude
动态加载以完成可复用任务。
[<u>https://github.com/anthropics/skills</u>](https://github.com/anthropics/skills)

\[3\] Anthropic Model Context Protocol 介绍：MCP 用于把 AI
应用与外部数据源和工具建立安全双向连接。
[<u>https://www.anthropic.com/news/model-context-protocol</u>](https://www.anthropic.com/news/model-context-protocol)

\[4\] Model Context Protocol 官方文档：MCP 是连接 AI
应用与外部系统的开放标准。
[<u>https://modelcontextprotocol.io/docs/getting-started/intro</u>](https://modelcontextprotocol.io/docs/getting-started/intro)

\[5\] Anthropic Skills 构建指南：介绍 Skill 结构、触发、测试和与 MCP
结合的实践。
[<u>https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf</u>](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)

# **18. 实现分工总览：脚本 / MCP / LLM / Skill**

本章用于把前文的产品化规划进一步落到工程实现层面。核心原则是：脚本确定事实，MCP
暴露能力，LLM 负责推理和生成，Skill
固化团队流程与边界。这样可以避免把大量 RTL、FS、寄存器文档和 UVM
环境直接塞入模型上下文，同时保证输出可审计、可复现、可迭代。

<img src="/mnt/data/dv_ai_coverage_md_assets/media/image3.png"
style="width:6.5in;height:3.97222in" />

图 3 实现职责分层图

## **18.1 四类实现对象的边界**

| **对象**          | **主要职责**                                                                                 | **不应承担的职责**                                      | **典型产物**                                                            |
|-------------------|----------------------------------------------------------------------------------------------|---------------------------------------------------------|-------------------------------------------------------------------------|
| Scripts / Indexer | 解析 coverage、构建 RTL/FS/Reg/TB 索引、运行仿真、计算 coverage diff、做静态校验             | 不做开放式语义推理，不直接生成最终验证结论              | \*.json / \*.sqlite / vector index / diff report                        |
| MCP Server        | 把脚本与索引包装成受控工具，提供结构化查询、权限校验、结果裁剪、命令执行入口                 | 不做重型离线索引构建，不把全量文件返回给 LLM            | cov_get_gap_detail、rtl_trace_fanin、tb_get_base_test_template 等 tools |
| Claude Code / LLM | 根据 Skill 规划步骤，调用 MCP，综合多源证据，做 gap 归因、场景生成、patch 初稿生成、报告生成 | 不直接扫全库，不凭空猜测寄存器/路径/类名，不自动 waiver | Scenario Card、triage report、patch draft、feedback report              |
| Skill Pack        | 定义任务流程、上下文预算、工具调用顺序、输出模板、安全边界、review checklist                 | 不保存项目大数据，不实现 coverage parser，不运行仿真    | SKILL.md、references/\*.md、schemas/\*.json                             |

## **18.2 判断某个能力应该放在哪里**

| **判断问题**                                                                     | **推荐实现**   | **理由**                                     |
|----------------------------------------------------------------------------------|----------------|----------------------------------------------|
| 结果是否必须准确且可复现，例如 hit count、寄存器 bit 位、RTL source line？       | 脚本 / Indexer | 这类事实不能依赖 LLM 记忆或推断。            |
| 是否需要被 Claude Code 反复按需调用，例如查询某个 gap、某个信号、某个 sequence？ | MCP tool       | MCP 是 Agent 与内部数据/工具之间的稳定接口。 |
| 是否需要理解语义、跨文档归因、推导验证场景？                                     | LLM            | 这类任务依赖验证经验、语义整合和开放式推理。 |
| 是否属于团队标准流程、输出格式、禁止事项、review 门禁？                          | Skill          | Skill 是流程规范，不是数据仓库。             |

## **18.3 总功能分工表**

| **功能**                     | **脚本实现**                           | **MCP 暴露**                                       | **LLM 实现**                | **Skill 约束**                   |
|------------------------------|----------------------------------------|----------------------------------------------------|-----------------------------|----------------------------------|
| project_manifest 校验        | validate_manifest.py                   | manifest_validate                                  | 理解校验结果                | 必须先加载 manifest              |
| coverage report 解析         | build_coverage_index.py                | cov_list_uncovered / cov_get_gap_detail            | 解释 gap 语义               | 禁止直接读完整 HTML              |
| coverage diff 计算           | coverage_diff.py                       | cov_get_coverage_diff                              | 解释是否关闭以及下一步      | 反馈报告模板                     |
| RTL hierarchy / signal index | build_rtl_index.py 或 Verdi/NPI export | rtl_get_instance_info / rtl_find_signal            | 选择相关 scope 并解释可控性 | 禁止全量 RTL 上下文              |
| Spec/FS 检索                 | build_spec_index.py                    | spec_search / spec_get_section                     | 关联验证意图                | summary 优先，必要时展开         |
| Register DB                  | build_reg_index.py                     | reg_find_field / reg_find_fields_affecting_feature | 判断配置依赖                | 寄存器事实必须来自工具           |
| UVM TB index                 | build_tb_index.py                      | tb_find_sequence / tb_get_base_test_template       | 选择模板并生成 patch        | 生成前必须查模板                 |
| 编译/仿真执行                | sim_runner.py                          | sim_run_targeted_test                              | 根据结果修复建议            | 默认需要人工确认或 manifest 授权 |
| Gap 分类                     | 规则辅助                               | 提供证据                                           | 主导分类                    | 分类枚举和置信度格式             |
| Scenario 生成                | 提供证据                               | 提供检索能力                                       | 主导生成                    | Scenario Card schema             |
| UVM patch 生成               | 静态校验                               | 提供模板/路径                                      | 主导生成                    | 最小 patch + review checklist    |

# **19. Offline Scripts 与 Indexer 实现设计**

Indexer 是整个系统的工程基础。它负责在 Claude Code
执行前，把原始工程数据变成结构化索引。MCP Server
在线查询索引，而不是每次让 LLM 或 MCP 临时扫描全库。建议把 Indexer
做成一组独立 CLI 脚本，并可在 regression 结束后自动触发。

<img src="/mnt/data/dv_ai_coverage_md_assets/media/image4.png"
style="width:6.5in;height:3.79167in" />

图 4 离线索引构建与在线 MCP 查询执行链路

## **19.1 推荐脚本目录**

dv-ai-coverage-kit/  
scripts/  
validate_manifest.py  
build_coverage_index.py  
build_rtl_index.py  
build_spec_index.py  
build_reg_index.py  
build_tb_index.py  
build_sim_history_index.py  
coverage_diff.py  
sim_runner.py  
static_patch_check.py  
indexes/  
\<project\>/  
coverage_index.json  
rtl_index.sqlite  
spec_index/  
reg_db.json  
tb_index.json  
sim_history.json  
mcp/  
dv_context_server/  
server.py  
tools/  
coverage_tools.py  
rtl_tools.py  
spec_tools.py  
register_tools.py  
tb_tools.py  
sim_tools.py

## **19.2 validate_manifest.py**

该脚本是所有工作流的入口校验器。它不做复杂业务逻辑，只检查项目接入信息是否完整，避免
Claude Code 在缺少路径、索引或权限配置时继续执行。

| **输入**              | **输出**                                            | **失败条件**                                                                      | **MCP 封装建议**                   |
|-----------------------|-----------------------------------------------------|-----------------------------------------------------------------------------------|------------------------------------|
| project_manifest.yaml | 校验报告 JSON：ok、warnings、errors、resolved_paths | coverage report 根目录不存在；index_path 不存在；仿真命令模板缺失；安全策略未配置 | manifest_validate(project_or_path) |

python scripts/validate_manifest.py --manifest
/proj/dma/project_manifest.yaml --out
/proj/dma/.dv_ai_index/manifest_check.json

## **19.3 build_coverage_index.py**

Coverage parser 必须用脚本实现。它从 URG HTML、TXT summary、XML/CSV
或内部 coverage export 中提取未覆盖项，并生成稳定 gap_id。LLM
不应直接读取完整 coverage report。

| **能力**                                | **实现要点**                                                      | **输出字段**                                                                           |
|-----------------------------------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| 解析 uncovered bins/cross/code coverage | 优先使用结构化 export；HTML 解析作为适配层；保留 source file/line | gap_id、coverage_type、covergroup、coverpoint、bin、hit_count、goal、source_file、line |
| 建立 coverpoint source map              | 从 coverage model 源码提取 covergroup/coverpoint/bin 定义         | coverpoint_path → file:line + snippet range                                            |
| 聚类相关 gaps                           | 按 covergroup、feature、source file、cross 相关性聚类             | cluster_id、related_gap_ids                                                            |
| 历史 hit 记录                           | 对比多轮 regression 或 targeted sim 结果                          | hit_history、first_seen、last_seen、trend                                              |

\# coverage_index.json 示例  
{  
"project": "dma_subsystem",  
"report_id": "reg_2026_05_20",  
"gaps": \[  
{  
"gap_id": "GAP_0012",  
"coverage_type": "functional",  
"covergroup": "dma_desc_cg",  
"coverpoint": "desc_mode_cp",  
"bin": "linked_list",  
"hit_count": 0,  
"goal": 1,  
"source_file": "tb/cov/dma_cov.sv",  
"line": 88,  
"cluster_id": "dma_desc_mode"  
}  
\]  
}

## **19.4 build_rtl_index.py**

RTL index 的目标不是把源码塞给模型，而是把 elaboration
后的设计上下文变成可查询图谱。优先路径是 VCS 生成 KDB，再用
Verdi/NPI/Tcl/C API 批量导出 hierarchy、module、signal、source
map、parameter override 和连接关系。若暂时无法接入
Verdi/NPI，可先用开源解析器或 grep/tree-sitter 做
fallback，但要在报告中标注“非 elaborated”。

| **数据项**                         | **推荐来源**                         | **用途**                                    |
|------------------------------------|--------------------------------------|---------------------------------------------|
| instance hierarchy                 | Verdi KDB / VCS elaboration DB / VPI | 将 coverage gap 映射到真实 instance path    |
| module / port / signal             | KDB/NPI 或 SV parser                 | 查找相关控制信号、状态机、接口信号          |
| file/line source map               | KDB/NPI                              | 为 LLM 提供最小 source snippet              |
| parameter override / generate 展开 | KDB/NPI                              | 判断某些覆盖点是否因配置裁剪不可达          |
| fanin/fanout graph                 | NPI trace 或自建 AST/netlist graph   | 分析目标条件是否可控、由哪些寄存器/状态驱动 |
| FSM candidates                     | RTL parser + pattern rules           | 支持 FSM state/transition coverage gap 分析 |

\# 推荐两阶段实现  
\# 1. EDA 工具生成设计数据库  
vcs -full64 -sverilog -f filelist.f -top tb_top -debug_access+all -kdb
-l compile.log  
  
\# 2. 批量导出结构化索引  
verdi -dbdir simv.daidir -nologo -nogui -play export_rtl_context.tcl  
python scripts/build_rtl_index.py --manifest project_manifest.yaml
--import-kdb-json rtl_context.json

## **19.5 build_spec_index.py**

FS/Spec 文档应先被切分成有层级的
section，再建立关键词索引与向量索引。MCP 查询时默认返回 section
summary、标题、页码和 evidence_id；只有在 LLM
需要验证原文时，才返回原文片段。

| **步骤** | **脚本职责**                                            | **输出**                                 |
|----------|---------------------------------------------------------|------------------------------------------|
| 文档解析 | 读取 PDF/DOCX/Markdown，保留页码、标题层级、表格标题    | sections.json                            |
| 章节切分 | 按 heading/feature ID/页范围切 chunk，避免超长上下文    | section_id、title、page_range、text_hash |
| 摘要生成 | 可用 LLM 批处理生成 section summary，但必须保留原文引用 | summary、key_terms、feature_tags         |
| 检索索引 | 建立 BM25/keyword + embedding index                     | spec_index/                              |

## **19.6 build_reg_index.py**

寄存器信息属于强事实数据，必须由脚本解析。输入可以是 IP-XACT、RAL
model、YAML/CSV、Excel 或寄存器文档。输出应包括
register/field/offset/bit/access/reset/description/RAL path/相关
feature。

\# reg_db.json 示例  
{  
"registers": \[  
{  
"block": "DMA",  
"register": "DMA_CFG",  
"offset": "0x004",  
"fields": \[  
{  
"field": "LL_MODE_EN",  
"bit_range": "\[3\]",  
"access": "RW",  
"reset": "0",  
"description": "Enable linked-list descriptor mode",  
"ral_path": "ral.dma.DMA_CFG.LL_MODE_EN",  
"feature_tags": \["linked_list_descriptor"\]  
}  
\]  
}  
\]  
}

## **19.7 build_tb_index.py**

UVM 环境索引用于约束 LLM
生成代码时“只能复用真实存在的组件”。脚本负责扫描已有
base_test、sequence、virtual sequence、sequencer、config
object、constraint、factory registration 和 RAL access helper。LLM
可以基于源码片段生成自然语言摘要，但类名、路径、config_db key、RAL path
必须来自索引。

| **索引对象**                | **解析方式**                                        | **用于**                      |
|-----------------------------|-----------------------------------------------------|-------------------------------|
| base_test                   | 扫描 extends uvm_test / 项目 base_test              | 生成新 testcase 时继承模板    |
| sequence / virtual sequence | 扫描 class extends uvm_sequence / virtual_seq       | 复用已有 stimulus             |
| config object / knobs       | 扫描 uvm_object fields、config_db set/get、plusargs | 决定场景参数如何配置          |
| constraint                  | 扫描 constraint block 与 rand fields                | 判断是否 constraint too tight |
| sequencer path              | 从 env/virtual sequencer 结构提取                   | 避免生成不存在的 start path   |
| existing tests for feature  | 文件名、注释、coverage history、tag 关联            | 避免重复造 case               |

## **19.8 sim_runner.py 与 coverage_diff.py**

编译、仿真、coverage merge 和 diff 必须由脚本执行，不由 LLM 直接拼 shell
任意执行。sim_runner.py 只允许执行 manifest 中 allowlist
的命令模板，并记录 command、seed、log path、return code、coverage report
id。

| **脚本**              | **职责**                                                                              | **输出**                                                  |
|-----------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------|
| sim_runner.py         | 根据 manifest 的 compile/run/cov 模板执行 targeted test；限制工作目录和命令 allowlist | sim_result.json、compile.log、sim.log、coverage_report_id |
| coverage_diff.py      | 比较 before/after report，输出目标 gap hit_count 变化和新增覆盖                       | coverage_diff.json                                        |
| static_patch_check.py | 检查 patch 是否引用不存在的类/路径，运行基本语法/lint/grep 规则                       | patch_check.json                                          |

# **20. DV Context MCP Server 实现设计**

MCP Server 是 Claude Code 与项目上下文之间的在线接口。MCP
不应该承担离线重处理，也不应该把全量 RTL/FS/TB 直接返回给
LLM。它的职责是读取索引、执行受控查询、返回小而准的结构化结果。MCP
是开放标准，用于让 AI 应用连接外部系统、数据源和工具；Python SDK
可用于构建暴露工具的 MCP server。

## **20.1 哪些能力应该做成 MCP tool**

| **适合做 MCP tool**                                                                             | **不适合做 MCP tool**                                       |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| Agent 在任务过程中需要按需多次查询的能力，例如 cov_get_gap_detail、spec_search、rtl_trace_fanin | 耗时很长的全量索引构建，例如 build_rtl_index.py 全量扫描    |
| 需要权限控制和审计的能力，例如 sim_run_targeted_test、get_source_snippet                        | 直接返回全量大文件，例如 get_full_rtl_repo、get_full_fs_doc |
| 需要结构化返回并被 LLM 综合判断的能力，例如 reg_find_fields_affecting_feature                   | 不稳定、不可复现的自由 shell 命令执行                       |
| 需要跨项目复用的标准能力，例如 tb_get_base_test_template                                        | 只在一次性批处理中使用的内部转换逻辑                        |

## **20.2 MCP Server 推荐结构**

mcp/dv_context_server/  
server.py \# MCP server 入口  
config.py \# 读取企业级配置、路径白名单、权限策略  
auth.py \# 用户/项目权限校验  
tools/  
coverage_tools.py \# cov\_\* tools  
rtl_tools.py \# rtl\_\* tools  
spec_tools.py \# spec\_\* tools  
register_tools.py \# reg\_\* tools  
tb_tools.py \# tb\_\* tools  
sim_tools.py \# sim\_\* tools  
services/  
project_loader.py \# manifest + index path resolver  
evidence.py \# evidence_id/source_ref 生成  
summarizer.py \# 长结果裁剪与摘要  
indexes/  
readers.py \# json/sqlite/vector index 读取  
tests/  
test_tools_contract.py

## **20.3 MCP tool 返回协议**

所有工具返回都应遵守统一 envelope，便于 Claude Code 做 evidence
trace，也便于后续自动评估。

{  
"ok": true,  
"tool": "cov_get_gap_detail",  
"project": "dma_subsystem",  
"result": {...},  
"evidence": \[  
{  
"evidence_id": "cov:GAP_0012:source",  
"source_type": "coverage_model",  
"source_ref": "tb/cov/dma_cov.sv:88-96",  
"summary": "desc_mode_cp bin linked_list definition"  
}  
\],  
"truncated": false,  
"next_actions": \["cov_get_coverpoint_source", "spec_search"\]  
}

## **20.4 最小 MCP tool 集合**

| **工具组** | **MVP tools**                                                                                                 | **返回重点**                                      |
|------------|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| Coverage   | cov_list_uncovered, cov_get_gap_detail, cov_get_coverpoint_source, cov_get_hit_history, cov_get_coverage_diff | gap 元数据、source snippet、历史趋势、diff        |
| Spec       | spec_search, spec_get_section                                                                                 | section summary、页码、feature tags、必要原文片段 |
| Register   | reg_find_field, reg_search_by_description, reg_find_fields_affecting_feature, reg_get_ral_path                | 字段事实、offset、bit、reset、RAL path            |
| RTL        | rtl_find_signal, rtl_get_instance_info, rtl_trace_fanin, rtl_get_source_snippet                               | 相关信号、层级、fanin 摘要、最小代码片段          |
| TB         | tb_find_sequence, tb_get_base_test_template, tb_find_config_knob, tb_get_sequence_source_snippet              | 可复用模板、config knob、真实路径                 |
| Simulation | sim_run_targeted_test, sim_get_test_result, sim_search_log                                                    | 受控执行结果、关键 log、错误摘要                  |

## **20.5 权限与安全实现要求**

- MCP server 默认 read-only；仿真执行、写文件、生成 patch 落盘必须经过
  manifest policy 和用户确认。

- 所有路径必须经过 project root allowlist
  校验，禁止通过相对路径逃逸到项目外。

- 所有 shell 命令必须来自 manifest command template，不允许 LLM 传入任意
  command。

- source snippet 返回必须限制 line range 和最大字节数。

- 所有 tool call 记录审计日志：user、project、tool、arguments
  hash、timestamp、result size。

# **21. Skill 与 Claude Code 实现设计**

Skill Pack 不实现 parser，也不保存项目数据。它实现的是 Claude Code
的工作规程：什么时候调用哪个 MCP
tool、每步拿多少上下文、生成什么格式、哪些行为禁止。

## **21.1 Skill 文件应该写什么**

| **文件**                                | **内容**                                                              | **长度建议**                    |
|-----------------------------------------|-----------------------------------------------------------------------|---------------------------------|
| SKILL.md                                | 触发条件、核心原则、标准 workflow、上下文预算、工具调用顺序、输出模式 | 尽量短，适合 Claude 立即加载    |
| references/gap_classification.md        | gap 分类定义、判断依据、反例、置信度规则                              | 中等长度，triage 时按需读取     |
| references/scenario_card_schema.md      | scenario card 字段、示例、质量门禁                                    | 中等长度                        |
| references/testcase_generation_rules.md | UVM 生成规则、禁止事项、patch 格式、compile checklist                 | 较长，只有 generate-case 时加载 |
| references/simulation_feedback.md       | log/coverage diff 解释规则、下一轮建议模板                            | 较短                            |
| schemas/\*.json                         | 机器可校验 schema，用于脚本验证输出                                   | 结构化文件                      |

## **21.2 LLM 负责的具体推理任务**

- 根据 gap 名称、coverpoint snippet、FS/Reg/RTL/TB evidence
  推断未覆盖场景的验证意图。

- 把 gap 分类为 Missing Stimulus、Config Missing、Constraint Too
  Tight、Coverage Model Issue、Monitor Sampling Issue、Unreachable
  Candidate 等。

- 生成 scenario card，包括 required config、stimulus steps、expected
  behavior、target signals、confidence 和 risks。

- 基于已有 base sequence/test 模板生成最小 UVM patch 初稿。

- 根据 compile/sim/coverage diff 的结构化结果，解释未 hit
  原因和下一轮修改建议。

## **21.3 LLM 不允许负责的事项**

- 不允许凭空发明寄存器字段、RAL path、sequencer path、UVM component
  名称。

- 不允许直接判断某 coverage gap 可以 waiver；只能输出 waiver
  candidate，并列出证据缺口。

- 不允许绕过 MCP 直接读取全量 RTL/FS/TB。

- 不允许自动提交代码或覆盖主干文件。

- 不允许把仿真是否通过、coverage 是否 hit
  建立在文本猜测上；必须使用脚本返回结果。

# **22. 端到端执行链路与数据流**

下面给出四个主要工作流的实现级步骤。团队可以直接把这些步骤写入 SKILL.md
或 references/workflows.md。

## **22.1 Workflow A：Coverage Triage**

| **步骤** | **执行方**   | **动作**                                                             | **输出**               |
|----------|--------------|----------------------------------------------------------------------|------------------------|
| 1        | Skill/Claude | 读取 manifest，确认 scope/report_id                                  | 任务上下文             |
| 2        | MCP/Script   | cov_list_uncovered(scope, report_id)                                 | Top gaps               |
| 3        | MCP/Script   | cov_get_gap_detail + cov_get_coverpoint_source + cov_get_hit_history | gap 事实与 evidence    |
| 4        | Claude       | 判断 gap 类型、优先级、是否需要更多上下文                            | context plan           |
| 5        | MCP          | 按需 spec/reg/tb/rtl 查询                                            | 最小上下文             |
| 6        | Claude       | 输出 triage report                                                   | 分类、优先级、建议动作 |

## **22.2 Workflow B：Scenario Card Generation**

| **步骤** | **执行方** | **动作**                                                                            | **输出**                                           |
|----------|------------|-------------------------------------------------------------------------------------|----------------------------------------------------|
| 1        | MCP        | 获取单个 gap detail/source/history                                                  | gap evidence                                       |
| 2        | Claude     | 判断语义关键词和上下文需求                                                          | query plan                                         |
| 3        | MCP        | spec_search + reg_find_fields_affecting_feature + tb_get_existing_tests_for_feature | FS/Reg/TB evidence                                 |
| 4        | MCP        | 必要时 rtl_find_signal / rtl_trace_fanin                                            | RTL controllability evidence                       |
| 5        | Claude     | 生成 scenario card                                                                  | required config、stimulus、expected behavior、risk |
| 6        | Script     | validate_scenario_card.py 校验 schema                                               | validation report                                  |

## **22.3 Workflow C：UVM Testcase/Sequence Generation**

| **步骤** | **执行方** | **动作**                                                           | **输出**           |
|----------|------------|--------------------------------------------------------------------|--------------------|
| 1        | Claude     | 读取 scenario card，确认生成目标是 sequence/test/config patch      | generation plan    |
| 2        | MCP        | tb_get_base_test_template + tb_find_sequence + tb_find_config_knob | 真实模板与 knob    |
| 3        | Claude     | 生成最小 patch，不直接覆盖文件                                     | patch draft        |
| 4        | Script     | static_patch_check.py                                              | 类名/路径/引用检查 |
| 5        | MCP/Script | 可选 compile dry-run 或用户确认后 compile                          | compile result     |
| 6        | Claude     | 输出 patch 说明、compile/run 命令、review checklist                | 生成报告           |

## **22.4 Workflow D：Simulation Feedback**

| **步骤** | **执行方** | **动作**                              | **输出**                |
|----------|------------|---------------------------------------|-------------------------|
| 1        | MCP/Script | sim_get_test_result / sim_search_log  | 编译/仿真结果与关键错误 |
| 2        | MCP/Script | cov_get_coverage_diff                 | before/after hit count  |
| 3        | MCP/Script | 必要时 wave_check_condition           | 目标信号行为摘要        |
| 4        | Claude     | 解释是否关闭、未 hit 原因、下一步动作 | feedback report         |
| 5        | Script     | 记录 case 与 gap 的关系               | history update          |

# **23. MVP 工程 Backlog 与任务拆分**

建议 MVP 只覆盖一个 block-level UVM 项目和 functional
coverage，先跑通“coverage gap → scenario card → UVM patch → targeted sim
→ coverage diff”的闭环。

| **阶段** | **任务**                                          | **实现类型** | **交付物**                                                               | **验收标准**                                 |
|----------|---------------------------------------------------|--------------|--------------------------------------------------------------------------|----------------------------------------------|
| M0       | 定义 project_manifest.schema.json 与示例 manifest | Schema/脚本  | schemas/project_manifest.schema.json, examples/dma/project_manifest.yaml | validate_manifest.py 可发现缺失路径和策略    |
| M1       | 实现 coverage parser 与 coverage index            | 脚本         | build_coverage_index.py, coverage_index.json                             | 能提取 top uncovered bins 与 source location |
| M2       | 实现 coverage MCP tools                           | MCP          | cov_list_uncovered, cov_get_gap_detail, cov_get_coverpoint_source        | Claude 可通过 MCP 查询 gap                   |
| M3       | 实现 spec/reg/tb 最小索引                         | 脚本 + MCP   | spec_search, reg_find_field, tb_get_base_test_template                   | 能为单个 gap 返回证据                        |
| M4       | 编写 dv-coverage-closure 与 scenario skill        | Skill        | SKILL.md, scenario_card_schema.md                                        | 能生成结构化 scenario card                   |
| M5       | 实现 UVM patch 生成规则与静态检查                 | Skill + 脚本 | testcase_generation_rules.md, static_patch_check.py                      | 生成 patch 不引用明显不存在的类名/路径       |
| M6       | 实现 sim_runner 与 coverage_diff                  | 脚本 + MCP   | sim_run_targeted_test, cov_get_coverage_diff                             | 能判断目标 gap 是否 hit                      |
| M7       | 建立 eval suite                                   | 测试/评估    | evals/\*.yaml                                                            | 固定 prompts 能稳定触发正确 workflow         |

# **24. 关键代码骨架示例**

以下代码是实现骨架，不是最终生产代码。实际项目中需要接入公司内部路径规范、权限系统、EDA
工具版本和日志标准。

## **24.1 Indexer CLI 骨架**

\# scripts/build_coverage_index.py  
import argparse, json  
from pathlib import Path  
  
  
def parse_urg_html(report_dir: Path) -\> list\[dict\]:  
\# 生产实现：解析 URG HTML/XML/CSV，提取 uncovered bins/cross/code
coverage  
\# 这里仅表示输出结构，不建议让 LLM 直接读完整 HTML。  
return \[\]  
  
  
def main():  
ap = argparse.ArgumentParser()  
ap.add_argument('--manifest', required=True)  
ap.add_argument('--report-id', required=True)  
ap.add_argument('--out', required=True)  
args = ap.parse_args()  
  
gaps = parse_urg_html(Path('/path/from/manifest'))  
index = {  
'report_id': args.report_id,  
'gaps': gaps,  
'schema_version': 'coverage_index.v1'  
}  
Path(args.out).write_text(json.dumps(index, indent=2),
encoding='utf-8')  
  
if \_\_name\_\_ == '\_\_main\_\_':  
main()

## **24.2 MCP Server 骨架**

\# mcp/dv_context_server/server.py  
\# 示例以 Python MCP SDK / FastMCP 风格表示，具体 import
以公司锁定版本为准。  
from mcp.server.fastmcp import FastMCP  
from tools.coverage_tools import load_gap_detail,
load_coverpoint_source  
from tools.register_tools import find_fields_affecting_feature  
  
mcp = FastMCP('dv-context')  
  
@mcp.tool()  
def cov_get_gap_detail(project: str, gap_id: str) -\> dict:  
"""Return one coverage gap with structured metadata and evidence."""  
return load_gap_detail(project, gap_id)  
  
@mcp.tool()  
def cov_get_coverpoint_source(project: str, gap_id: str, max_lines: int
= 80) -\> dict:  
"""Return a bounded source snippet for the coverpoint/bin
definition."""  
return load_coverpoint_source(project, gap_id, max_lines=max_lines)  
  
@mcp.tool()  
def reg_find_fields_affecting_feature(project: str, feature: str) -\>
dict:  
"""Find register fields likely controlling a feature."""  
return find_fields_affecting_feature(project, feature)  
  
if \_\_name\_\_ == '\_\_main\_\_':  
mcp.run()

## **24.3 MCP Tool 内部实现要点**

\# mcp/dv_context_server/tools/coverage_tools.py  
from pathlib import Path  
import json  
  
  
def \_project_index_root(project: str) -\> Path:  
\# 生产实现：从企业配置或 manifest registry 解析，并做 allowlist 校验  
root = Path('/proj') / project / '.dv_ai_index'  
if not root.exists():  
raise FileNotFoundError(f'index root not found: {root}')  
return root  
  
  
def load_gap_detail(project: str, gap_id: str) -\> dict:  
idx = json.loads((\_project_index_root(project) /
'coverage_index.json').read_text())  
for gap in idx\['gaps'\]:  
if gap\['gap_id'\] == gap_id:  
return {  
'ok': True,  
'tool': 'cov_get_gap_detail',  
'project': project,  
'result': gap,  
'evidence': \[{  
'evidence_id': f'cov:{gap_id}',  
'source_type': 'coverage_report',  
'source_ref': idx.get('report_id'),  
'summary': 'coverage gap metadata from parsed report'  
}\],  
'truncated': False  
}  
return {'ok': False, 'error': f'gap_id not found: {gap_id}'}

## **24.4 SKILL.md 关键片段**

\# DV Coverage Closure Skill - critical policy excerpt  
  
When analyzing coverage gaps:  
1. Load project manifest first.  
2. Do not load full RTL, FS, register manual, UVM environment, or
coverage HTML.  
3. Call cov_get_gap_detail and cov_get_coverpoint_source before any
semantic conclusion.  
4. Use
spec_search/reg_find_fields_affecting_feature/tb_get_existing_tests_for_feature
as needed.  
5. Use rtl_trace_fanin only when signal controllability is unclear.  
6. Generated testcase must be based on existing
base_test/sequence/config knob.  
7. Present generated code as patch or new files. Never overwrite source
files silently.  
8. Do not mark gaps as waived or unreachable without formal evidence or
engineer approval.

# **25. 落地检查清单**

以下清单用于评审项目是否已经从概念规划进入可执行状态。

| **类别**   | **检查项**                                   | **通过标准**                                             |
|------------|----------------------------------------------|----------------------------------------------------------|
| 项目接入   | 是否存在 project_manifest.yaml               | 路径、scope、policy、命令模板完整且 validate 通过        |
| Coverage   | 是否能稳定生成 coverage_index.json           | Top uncovered gaps、source file/line、hit history 可查询 |
| MCP        | 是否实现最小 cov/spec/reg/tb tools           | Claude Code 能按自然语言任务成功调用                     |
| 上下文控制 | 是否禁止全量文件返回                         | MCP 返回 summary + evidence，expand 有行数限制           |
| Scenario   | 是否有 scenario_card schema 与 validator     | LLM 输出可被脚本校验                                     |
| Case 生成  | 是否能查到真实 base sequence/test            | 生成 patch 基于已有模板，不发明组件                      |
| 仿真闭环   | 是否能运行 targeted sim 并计算 coverage diff | 能判断目标 gap hit_count 是否变化                        |
| 安全审计   | 是否有路径 allowlist 和 tool call log        | 所有 MCP 调用可追溯                                      |
| 团队复用   | 是否有 README、prompt 模板、eval suite       | 新同事能按模板完成 triage/scenario/generate/feedback     |

# **26. 建议的最终实现结论**

该方案的最终实现不应理解为“写一个很长的 Skill
文件”。真正可复用的公司级能力应由四部分构成：

1\. Skill Pack：定义流程、规则、模板和边界。

2\. Offline Scripts / Indexer：把 coverage、RTL、FS、Reg、TB、Sim
结果转成结构化索引。

3\. DV Context MCP Server：把索引和受控执行能力暴露给 Claude Code。

4\. Claude Code Agent：在 Skill 约束下调用
MCP，完成语义归因、场景生成、patch 初稿和反馈报告。

只有把这四层分清楚，才能解决上下文爆炸、结果不可追溯、生成代码幻觉和团队复用困难等问题。
