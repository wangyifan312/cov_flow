# 用户 Prompt 模板

按场景分类的 prompt 模板，直接复制、替换花括号参数即可使用。

**使用说明：**
- 花括号 `{xxx}` 表示需要替换的参数
- 直接粘贴到 Claude Code 对话框中即可使用
- 也可以作为 slash command 的参数传入（如 `/dv-coverage-gap-triage` + prompt）

---

## 1. 覆盖率 Triage

> 对应 Skill：`/dv-coverage-closure`、`/dv-coverage-gap-triage`

#### 基础 triage

```
对 {project} 做 functional coverage triage，列出 top {N} gaps 并分类。
```

#### 全类型覆盖率 triage

```
对 {project} 做全类型覆盖率 triage（coverage_type="all"），列出 top {N} gaps。
```

#### 指定模块 triage

```
对 {project} 的 {scope} 模块做 triage，只看 {coverage_type} 类型的 gaps。
```

#### 对比两轮 regression

```
对比 {project} 最新两轮 regression 的覆盖率 diff，列出 newly covered 和 regressed gaps。
```

---

## 2. Gap 深度分析

> 对应 Skill：`/dv-coverage-gap-triage`

#### 单 gap 深度分析

```
分析 {project} 的 {gap_id}：
1. 获取 gap 详情和 coverpoint 源码
2. 查找相关的 spec 章节和寄存器字段
3. 给分类判断（Missing Stimulus / Config Missing / Constraint Too Tight / 其他）
4. 给出闭合建议
```

#### 多 gap 优先级排序

```
比较 {gap_id_1}、{gap_id_2}、{gap_id_3}，哪个优先级更高、更容易闭合？给出排序和理由。
```

#### Gap 历史趋势

```
查看 {project} 的 {gap_id} 在历史 regression 中的命中趋势，是一直未覆盖还是曾经被覆盖过？
```

---

## 3. 场景生成

> 对应 Skill：`/dv-coverage-scenario-generation`

#### 基础场景卡

```
为 {project} 的 {gap_id} 生成 scenario card，包含 required config、stimulus、expected behavior。
```

#### 结合 TB 上下文

```
为 {project} 的 {gap_id} 生成 scenario card，先查看现有 TB 是否能覆盖这个 gap，如果能就不需要新测试。
```

#### 多 gap 场景合并

```
{gap_id_1} 和 {gap_id_2} 能否用同一个测试场景同时覆盖？如果可以，生成合并的 scenario card。
```

---

## 4. 测试用例生成

> 对应 Skill：`/dv-testcase-generation`

#### 基于现有 sequence

```
为 {project} 的 {gap_id} 生成 UVM testcase，基于 {sequence_name} 作为模板。
```

#### 确定性测试

```
为 {project} 的 {gap_id} 生成确定性测试（固定参数，不要随机），确保每次都能命中目标 gap。
```

#### 最小 patch

```
为 {project} 的 {gap_id} 生成最小 UVM patch，只新增文件不修改现有文件，输出 compile 和 run 命令。
```

#### 批量生成

```
为 {project} 的 top 5 gaps 各生成一个 targeted test，列出每个 test 的目标 gap 和预期覆盖效果。
```

---

## 5. 仿真与反馈

> 对应 Skill：`/dv-simulation-feedback`

#### 跑现有测试

```
用 sim_run_targeted_test 跑 {test} SEED={seed}，然后检查 {gap_id} 有没有被命中。
```

#### 分析仿真结果

```
分析 {test} SEED={seed} 的仿真结果，告诉我：
1. 编译和仿真是否通过
2. 有没有 UVM_ERROR 或 UVM_FATAL
3. {gap_id} 是否被覆盖
```

#### 多 seed 扫描

```
跑 {test} 用 SEED=1,2,3,4,5，看哪个 seed 能命中 {gap_id}，给出命中率统计。
```

#### 覆盖率 diff 分析

```
对比 {project} 仿真前后的覆盖率 diff，列出 newly covered gaps 和仍然未覆盖的 gaps。
```

---

## 6. 端到端流程

> 对应 Skill：`/dv-coverage-closure`（完整编排）

#### 单 gap 全闭环

```
对 {project} 的 {gap_id} 做完整的闭环：
1. Triage：分类和优先级
2. Scenario：生成场景卡
3. Testcase：生成 UVM patch
4. Simulate：编译运行
5. Feedback：确认 gap 是否关闭
```

#### 批量 triage

```
对 {project} 的 top 10 gaps 逐个分析，输出一份完整的 triage report，包含优先级排序、分类、建议动作。
```

#### 项目覆盖率健康检查

```
对 {project} 做一次覆盖率健康检查：
1. 总体覆盖率统计（按类型分组）
2. Top 20 未覆盖 gaps
3. 趋势分析（improving / regressing / stable）
4. 建议优先闭合的 gaps 和理由
```

---

## 7. 辅助查询

> 不需要 Skill，直接在 Claude Code 对话中使用。

#### 查寄存器

```
查 {project} 中 {field_name} 这个寄存器字段的详细信息（offset、bit、access、reset、RAL path）。
```

#### 查 spec

```
搜索 {project} 的 spec 中与 {keyword} 相关的章节。
```

#### 查 TB

```
{project} 中有哪些和 {feature} 相关的 test 和 sequence？
```

#### 查 RTL

```
{project} 中 {signal_name} 信号在哪个模块、哪个文件？给我源码片段。
```

---

## 参数速查

| 参数 | 说明 | 示例值 |
|---|---|---|
| `{project}` | 项目名（`projects.yaml` 中注册的名称） | `axi2ahb`、`dma_subsystem` |
| `{N}` | 返回的 gap 数量 | `10`、`20` |
| `{gap_id}` | 覆盖率 gap 标识符 | `GAP_0006`、`GAP_L003` |
| `{gap_id_1}` / `{gap_id_2}` / `{gap_id_3}` | 多个 gap 标识符 | `GAP_0001`、`GAP_0003` |
| `{scope}` | 实例路径过滤 | `tb_top.u_dut.u_dma` |
| `{coverage_type}` | 覆盖率类型 | `functional`、`line`、`branch`、`toggle`、`fsm`、`all` |
| `{test}` | UVM 测试名 | `wrap8_test` |
| `{seed}` | 随机种子 | `42` |
| `{sequence_name}` | 序列名 | `wrap_burst_seq` |
| `{field_name}` | 寄存器字段名 | `LL_MODE_EN` |
| `{keyword}` | 搜索关键词 | `linked_list`、`burst` |
| `{feature}` | 功能特性关键词 | `interrupt`、`power` |
| `{signal_name}` | RTL 信号名 | `axi_valid`、`wr_state` |
