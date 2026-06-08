# Phase 5b Coding Agent Prompt: WP-4 CLI Script Upgrade

> **执行顺序**: WP-1 → WP-2 → WP-3 → **WP-4** → WP-5  
> **本文档**: WP-4（CLI Script Upgrade）  
> **前置依赖**: WP-1 + WP-2 完成  
> **后续**: WP-4 完成后回来 review，再执行 WP-5

---

## Objective

升级 `scripts/sim_runner.py`，新增 `--real` 模式，使用 WP-1 的 `SimExecutor` 执行真实的 compile + run 流程。

## File to Modify (1 file)

| File | Action | Purpose |
|------|--------|---------|
| `scripts/sim_runner.py` | Modify | 新增 `--real` flag + SimExecutor 集成 |

---

## Current Behavior

先读一下 `scripts/sim_runner.py` 的现有代码，了解当前 CLI 接口。

现有行为（`--real` 不传时）：
- 从 `sim_data/` 读取 mock 结果
- 输出 mock 的 pass/fail 和覆盖率摘要
- 不调用任何 subprocess

## Changes

### 新增 CLI 参数

```python
parser.add_argument(
    "--real", action="store_true",
    help="Run real VCS simulation (requires simulation.mode: real in manifest)",
)
```

### Real Mode 逻辑

```python
if args.real:
    from lib.sim_executor import SimExecutor

    # Load manifest and check mode
    manifest = Manifest.load(args.manifest)
    if manifest.sim_mode != "real":
        print(f"ERROR: manifest simulation.mode is '{manifest.sim_mode}', not 'real'.")
        print("To run real simulation, set mode: real in the manifest.")
        sys.exit(1)

    # Create executor
    executor = SimExecutor(
        project_root=manifest.project_root,
        results_root=manifest.sim_results_root,
        timeout_seconds=manifest.sim_timeout,
        urg_timeout_seconds=manifest.sim_urg_timeout,
    )

    # Validate test name and seed
    try:
        executor.validate_test_name(args.test)
        executor.validate_seed(args.seed)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Render commands from manifest
    sim_config = manifest.data.get("simulation", {})
    compile_cmd = sim_config.get("compile_cmd_template", "make compile TEST={test}").format(
        test=args.test, seed=args.seed,
    )
    run_cmd = sim_config.get("run_cmd_template", "make run TEST={test} SEED={seed}").format(
        test=args.test, seed=args.seed,
    )

    # URG command (optional)
    urg_cmd = None
    urg_template = sim_config.get("urg_cmd_template")
    if urg_template:
        vdb_dir = sim_config.get(
            "vdb_dir_template", "sim_results/coverage/{test}_{seed}.vdb",
        ).format(test=args.test, seed=args.seed)
        report_dir = f"{executor.get_results_dir(args.test, args.seed)}/urg_report"
        urg_cmd = urg_template.format(vdb_dir=vdb_dir, report_dir=report_dir)

    # Run pipeline
    print(f"Running real simulation: test={args.test} seed={args.seed}")
    print(f"  compile: {compile_cmd}")
    print(f"  run:     {run_cmd}")
    if urg_cmd:
        print(f"  urg:     {urg_cmd}")

    result = executor.run_pipeline(
        test=args.test, seed=args.seed,
        compile_cmd=compile_cmd, run_cmd=run_cmd, urg_cmd=urg_cmd,
    )

    # Persist
    result_path = executor.save_result(args.test, args.seed, result)
    print(f"\nResults saved to: {result_path}")

    # Print summary
    print(f"\n--- Results ---")
    if result.compile:
        print(f"Compile: {result.compile.status} ({result.compile.duration_seconds:.1f}s)")
        if result.compile.status != "pass":
            print(f"  Log: {result.compile.log_path}")
    if result.run:
        print(f"Run:     {result.run.status} ({result.run.duration_seconds:.1f}s)")
        print(f"  Log: {result.run.log_path}")
    if result.urg:
        print(f"URG:     {result.urg.status} ({result.urg.duration_seconds:.1f}s)")
        print(f"  Log: {result.urg.log_path}")

    # Exit code based on run status
    if result.run and result.run.status == "pass":
        sys.exit(0)
    elif result.compile and result.compile.status != "pass":
        sys.exit(2)  # compile failure
    else:
        sys.exit(1)  # run failure or timeout
```

### Output 格式

```
Running real simulation: test=wrap8_targeted_test seed=42
  compile: make compile TEST=wrap8_targeted_test
  run:     make run TEST=wrap8_targeted_test SEED=42
  urg:     urg -dir sim_results/coverage/wrap8_targeted_test_42.vdb -report .../urg_report -format html

--- Results ---
Compile: pass (23.4s)
Run:     pass (67.2s)
  Log: /path/to/sim_results/wrap8_targeted_test_42/run.log
URG:     ok (45.1s)
  Log: /path/to/sim_results/wrap8_targeted_test_42/urg.log

Results saved to: /path/to/sim_results/wrap8_targeted_test_42/sim_result.json
```

---

## Verification

```bash
# 1. 现有 mock 行为不变
.venv/bin/python scripts/sim_runner.py --manifest mock_data/dma_subsystem/project_manifest.yaml \
    --test dma_basic_test --seed 1

# 2. --real 模式拒绝 mock manifest
.venv/bin/python scripts/sim_runner.py --manifest mock_data/axi2ahb/project_manifest.yaml \
    --test test1 --seed 42 --real
# 期望: ERROR: manifest simulation.mode is 'mock', not 'real'.

# 3. --real 模式验证 test name
.venv/bin/python scripts/sim_runner.py --manifest mock_data/axi2ahb/project_manifest_real.yaml.example \
    --test "../../../etc/passwd" --seed 42 --real
# 期望: ERROR: Invalid test name ...

# 4. --real 模式验证 negative seed
.venv/bin/python scripts/sim_runner.py --manifest mock_data/axi2ahb/project_manifest_real.yaml.example \
    --test test1 --seed -1 --real
# 期望: ERROR: Seed must be non-negative ...

# 5. Lint + typecheck
.venv/bin/ruff check scripts/sim_runner.py
.venv/bin/mypy scripts/sim_runner.py

# 6. 现有测试不破坏
.venv/bin/python -m pytest --tb=short -q

# 7. 通用性检查
grep -n "axi\|ahb\|dma" scripts/sim_runner.py
# 期望: 无新增匹配
```

---

## Quality Checklist

- [ ] 不带 `--real` 时行为完全不变（现有 mock 测试通过）
- [ ] `--real` 拒绝 `mode: mock` 的 manifest
- [ ] `--real` 验证 test name（拒绝 `..`、`/`）
- [ ] `--real` 验证 seed（拒绝负数）
- [ ] `--real` 正确渲染 compile/run/urg 命令
- [ ] `--real` 调用 `SimExecutor.run_pipeline`
- [ ] 结果持久化到 `sim_result.json`
- [ ] 输出可读的 summary
- [ ] Exit code: 0=pass, 1=run fail, 2=compile fail
- [ ] ruff 0 issues
- [ ] mypy 0 errors
- [ ] 现有测试全部通过
- [ ] 无硬编码项目名
