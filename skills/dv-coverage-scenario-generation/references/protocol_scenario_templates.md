# Protocol Scenario Templates

Concrete scenario templates for common bus protocols and features.
These are structural placeholders to be filled in by the LLM based on actual project parameters.

## DMA Descriptor Transfer Template

**Feature**: DMA descriptor-based transfer (linked list, scatter-gather)

**Config prerequisites**:
- Enable DMA controller: `{ral_path}.dma_ctrl.enable = 1`
- Set descriptor mode: `{ral_path}.dma_ctrl.mode = {DESCRIPTOR_MODE}`
- Configure descriptor base address: `{ral_path}.desc_base_addr = {BASE_ADDR}`
- Enable descriptor interrupts (optional): `{ral_path}.dma_int_mask.desc_done = 1`

**Stimulus skeleton**:
1. Write descriptor to memory at `{DESC_ADDR}`
2. Set descriptor fields: src, dst, length, next_desc_ptr
3. Start DMA: `{ral_path}.dma_ctrl.start = 1`
4. Wait for completion (poll status or interrupt)
5. Verify data transfer correctness

**Expected behavior**:
- DMA reads descriptor from `{DESC_ADDR}`
- Transfers `{LENGTH}` bytes from `{SRC}` to `{DST}`
- Updates descriptor status
- Asserts interrupt if enabled

**Coverage targets**:
- Descriptor type bin
- Transfer length bins
- Descriptor chain length

## AXI Burst Template

**Feature**: AXI burst transfer (INCR, WRAP, FIXED)

**Config prerequisites**:
- Configure AXI slave: `{ral_path}.axi_ctrl.burst_enable = 1`
- Set burst type: `{ral_path}.axi_ctrl.burst_type = {BURST_TYPE}`
- Configure address alignment: `{ral_path}.axi_ctrl.addr_align = {ALIGN}`

**Stimulus skeleton**:
1. Issue AXI write with:
   - Address: `{ADDR}`
   - Burst type: `{BURST_TYPE}`
   - Burst length: `{BURST_LEN}`
   - Size: `{BURST_SIZE}`
2. Write data beats
3. Wait for BRESP
4. Verify data in memory

**Expected behavior**:
- AXI slave accepts burst
- Transfers `{BURST_LEN}` beats
- Handles address wrapping if WRAP type
- Returns OKAY response

**Coverage targets**:
- Burst type bins (INCR, WRAP, FIXED)
- Burst length bins (1, 2, 4, 8, 16)
- Size bins (byte, halfword, word)

## Interrupt Coalescing Template

**Feature**: Interrupt coalescing (multiple events → single interrupt)

**Config prerequisites**:
- Enable interrupt coalescing: `{ral_path}.int_ctrl.coal_enable = 1`
- Set coalescing threshold: `{ral_path}.int_ctrl.coal_threshold = {THRESHOLD}`
- Set coalescing timer: `{ral_path}.int_ctrl.coal_timer = {TIMER}`

**Stimulus skeleton**:
1. Generate `{N}` interrupt events (where `{N}` >= `{THRESHOLD}`)
2. Monitor interrupt output
3. Verify interrupt asserts after `{THRESHOLD}` events
4. Or verify interrupt asserts after `{TIMER}` timeout

**Expected behavior**:
- Events counted internally
- Interrupt asserts when count reaches threshold
- Or interrupt asserts when timer expires
- Interrupt status register reflects pending events

**Coverage targets**:
- Coalescing threshold bins
- Timer timeout bins
- Event count before interrupt

## FIFO Threshold Template

**Feature**: FIFO threshold interrupt (almost full/almost empty)

**Config prerequisites**:
- Configure FIFO threshold: `{ral_path}.fifo_ctrl.threshold = {THRESHOLD}`
- Enable threshold interrupt: `{ral_path}.fifo_ctrl.thresh_int_en = 1`

**Stimulus skeleton**:
1. Write `{THRESHOLD}` entries to FIFO
2. Verify threshold interrupt asserts
3. Read entries until below threshold
4. Verify interrupt deasserts

**Expected behavior**:
- FIFO fill level tracked
- Interrupt asserts when level >= threshold
- Interrupt deasserts when level < threshold

**Coverage targets**:
- Threshold value bins
- FIFO depth bins
- Threshold crossing (rising/falling)

## Power State Transition Template

**Feature**: Power state machine (active, sleep, deep sleep)

**Config prerequisites**:
- Enable power management: `{ral_path}.pwr_ctrl.pm_enable = 1`
- Configure state transition conditions: `{ral_path}.pwr_ctrl.sleep_condition = {COND}`

**Stimulus skeleton**:
1. Start in active state
2. Trigger sleep condition: `{COND}`
3. Verify transition to sleep state
4. Trigger wake event: `{WAKE_EVENT}`
5. Verify transition back to active

**Expected behavior**:
- State machine transitions correctly
- State-dependent logic disabled in sleep
- Wake event restores state

**Coverage targets**:
- State transition bins (active→sleep, sleep→active)
- Transition condition bins
- Wake event type bins

## Usage Guidelines

1. **Identify the feature** from gap detail (covergroup/coverpoint name)
2. **Select matching template** based on protocol/feature type
3. **Fill placeholders** using:
   - `spec_search` for feature requirements
   - `reg_find_fields_affecting_feature` for RAL paths
   - `tb_get_existing_tests_for_feature` for base test/sequence
4. **Adapt stimulus skeleton** to match project conventions
5. **Verify coverage targets** align with gap's coverpoint

## Template Extension

If no template matches the feature:
1. Use generic Missing Stimulus pattern from scenario_patterns.md
2. Document the new template for future reference
3. Ensure stimulus structure follows UVM best practices
