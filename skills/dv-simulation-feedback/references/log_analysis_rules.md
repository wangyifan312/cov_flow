# Log Analysis Rules

Rules for analyzing simulation logs to diagnose test failures and coverage issues.

## UVM Message Severity Hierarchy

UVM defines 4 severity levels, in increasing order of severity:

| Severity | Meaning | Action |
|----------|---------|--------|
| `UVM_INFO` | Informational message | Review for context |
| `UVM_WARNING` | Potential issue, test continues | Investigate if related to failure |
| `UVM_ERROR` | Error condition, test may continue | Root cause analysis required |
| `UVM_FATAL` | Fatal error, test terminates | Immediate investigation required |

**Analysis priority**: FATAL → ERROR → WARNING → INFO

## Failure Type Classification

### Compile Failure

**Symptoms**:
- Test does not start
- Error messages during elaboration or compilation
- No simulation log generated

**Log location**: compile.log or build.log

**Common patterns**:
- `Error: Undefined type`
- `Error: Cannot open include file`
- `Error: Syntax error`

**Action**: See compile_check_rules.md for debugging

### Link Failure

**Symptoms**:
- Compilation succeeds
- Linking fails with undefined symbols
- No simulation log

**Log location**: link.log or build.log

**Common patterns**:
- `undefined reference to`
- `multiple definition of`
- `cannot find -l<library>`

**Action**:
- Check if all packages are compiled
- Verify library paths in link command
- Check for duplicate symbol definitions

### Runtime Assertion Failure

**Symptoms**:
- Test starts but terminates early
- UVM_FATAL in log
- Assertion failure message

**Log location**: sim.log or run.log

**Common patterns**:
```
UVM_FATAL @ 1000: [ASSERT] Assertion failed: expected X, got Y
```

**Action**:
- Identify the assertion that failed
- Check if assertion is correct (may be overly strict)
- Review stimulus that triggered assertion
- Fix stimulus or adjust assertion

### Timeout

**Symptoms**:
- Test runs but does not complete
- UVM_FATAL with timeout message
- Test hangs at specific phase

**Log location**: sim.log or run.log

**Common patterns**:
```
UVM_FATAL @ 10000000: [TIMEOUT] Test timeout after 10ms
```

**Action**:
- Check if test is stuck in infinite loop
- Verify stimulus generation completes
- Check if DUT is waiting for signal that never arrives
- Increase timeout if test legitimately takes longer

### Runtime Error (Non-Fatal)

**Symptoms**:
- Test completes but with errors
- UVM_ERROR messages in log
- Test marked as FAIL

**Log location**: sim.log or run.log

**Common patterns**:
```
UVM_ERROR @ 5000: [CHECK] Data mismatch at address 0x1000
```

**Action**:
- Identify the error condition
- Check if error is expected (negative test) or unexpected
- Review stimulus and expected behavior
- Fix stimulus or DUT

## Log Search Strategy

### Step 1: Find FATAL and ERROR

Search for the most severe messages first:

```bash
grep -n "UVM_FATAL\|UVM_ERROR" sim.log
```

**What to look for**:
- Timestamp of first error
- Error message content
- Component that reported error

### Step 2: Find WARNING

If no FATAL/ERROR, check warnings:

```bash
grep -n "UVM_WARNING" sim.log
```

**What to look for**:
- Warnings that may indicate root cause
- Repeated warnings (may indicate systematic issue)

### Step 3: Review INFO Messages

If test passed but coverage unchanged, review info messages:

```bash
grep -n "UVM_INFO" sim.log | head -20
```

**What to look for**:
- Test startup and phase messages
- Stimulus generation messages
- Configuration messages
- Test completion messages

### Step 4: Search for Keywords

Search for feature-specific keywords:

```bash
grep -i "dma\|descriptor\|linked" sim.log
```

**What to look for**:
- Feature-specific messages
- Stimulus generation for target feature
- Configuration of target feature

## Common Error Patterns

### Pattern 1: Configuration Error

```
UVM_ERROR @ 100: [CFG] Failed to configure DMA: invalid mode
```

**Cause**: Configuration value out of range or invalid combination.

**Diagnosis**:
- Check configuration values in test
- Verify against spec or register description
- Check for configuration dependencies

**Fix**:
- Correct configuration values
- Ensure configuration order is correct
- Add configuration validation

### Pattern 2: Data Mismatch

```
UVM_ERROR @ 5000: [CHECK] Data mismatch: expected 0xAA, got 0x55
```

**Cause**: DUT produced incorrect output.

**Diagnosis**:
- Check stimulus that produced this output
- Verify expected value is correct
- Review DUT logic for this scenario

**Fix**:
- If expected value wrong: fix scoreboard/checker
- If DUT wrong: report bug
- If stimulus wrong: fix stimulus generation

### Pattern 3: Protocol Violation

```
UVM_ERROR @ 2000: [PROTO] AXI protocol violation: AWVALID without AWREADY
```

**Cause**: Stimulus violated protocol rules.

**Diagnosis**:
- Check stimulus generation logic
- Verify protocol compliance in sequence
- Review protocol spec

**Fix**:
- Fix stimulus to follow protocol
- Check if monitor is correct (may be false positive)

### Pattern 4: Resource Exhaustion

```
UVM_ERROR @ 8000: [FIFO] FIFO overflow: write while full
```

**Cause**: Stimulus exceeded resource capacity.

**Diagnosis**:
- Check stimulus rate vs resource capacity
- Verify backpressure handling
- Review FIFO depth configuration

**Fix**:
- Reduce stimulus rate
- Add backpressure handling
- Increase FIFO depth if appropriate

### Pattern 5: Timeout on Handshake

```
UVM_FATAL @ 10000000: [TIMEOUT] Timeout waiting for DMA completion
```

**Cause**: DUT did not complete operation within timeout.

**Diagnosis**:
- Check if operation was started
- Verify DUT is not stuck (check internal state)
- Review completion condition

**Fix**:
- Ensure operation is started
- Check for deadlock conditions
- Increase timeout if operation legitimately takes longer

## Log Analysis Tools

### sim_search_log

Use the MCP tool to search logs:

```
sim_search_log(project, test, seed, keyword)
```

**Example**: Search for DMA-related messages
```
sim_search_log("dma_subsystem", "dma_linked_list_test", 1, "descriptor")
```

### sim_get_test_result

Use to get test status and log path:

```
sim_get_test_result(project, test, seed)
```

**Returns**: sim_status, log_path, log_summary

### Manual grep

For local log analysis:

```bash
# Find all errors
grep "UVM_ERROR\|UVM_FATAL" sim.log

# Find specific feature
grep -i "dma" sim.log

# Count messages by severity
grep -c "UVM_INFO" sim.log
grep -c "UVM_WARNING" sim.log
grep -c "UVM_ERROR" sim.log
grep -c "UVM_FATAL" sim.log
```

## Log Analysis Best Practices

1. **Start with severity**: Always check FATAL/ERROR first
2. **Read context**: Look at messages before and after error
3. **Check timing**: Note when error occurred (early vs late in test)
4. **Correlate with coverage**: If test passed but coverage unchanged, review INFO messages
5. **Document findings**: Record error patterns and fixes for future reference

## Relationship to Other References

- coverage_diff_rules.md: Analyze coverage changes after test
- compile_check_rules.md: Debug compile failures
- sim_search_log tool: Search simulation logs
- sim_get_test_result tool: Get test status and log path
