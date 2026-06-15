# DMA Subsystem Functional Specification

## 1. DMA Subsystem Overview

The DMA subsystem provides high-performance data transfer between memory regions
without CPU intervention. The subsystem consists of a DMA controller core with
descriptor parsing, AXI master interface, interrupt control, and power management.

Key features:
- Up to 4 independent DMA channels
- Support for normal, linked-list, and scatter-gather descriptor modes
- AXI4-compliant master interface with configurable burst types
- Interrupt coalescing for reduced CPU overhead
- Clock gating and retention mode for power management

Address map is defined in the register file. The top-level instance is
`tb_top.u_dut.u_dma_subsys.u_dma`.

## 2. Descriptor Format

Normal descriptors define a single contiguous transfer with the following fields:
- Source address (32 bits, word-aligned)
- Destination address (32 bits, word-aligned)
- Transfer size in bytes (16 bits, max 4096)
- Control flags: interrupt-on-completion, end-of-chain

The descriptor is fetched from memory when a channel is enabled and the descriptor
queue is not full. The parser validates address alignment before initiating the transfer.

## 3. Linked-List Descriptor Mode

Linked-list mode allows chaining multiple descriptors via a next-pointer field.
Enabled by setting `DMA_CFG.LL_MODE_EN` in the configuration register.

When `ll_mode_en` is asserted, the parser transitions to `PARSE_LINKED` state
after completing the current descriptor. The next descriptor address is read
from the descriptor's next-pointer field, enabling arbitrary chains of transfers.

Chain termination occurs when the end-of-chain flag is set or when a null
next-pointer (0x00000000) is encountered.

## 4. Scatter-Gather Descriptor Mode

Scatter-gather mode supports non-contiguous memory regions by processing a table
of address/length pairs. Enabled by setting `DMA_CFG.SG_MODE_EN`.

The scatter-gather table contains up to 256 entries, each specifying a source
address, destination address, and transfer length. The parser iterates through
the table, issuing one transfer per entry.

## 5. Descriptor Chaining

Descriptor chaining allows back-to-back descriptor processing without CPU
intervention. A chain of 3+ descriptors exercises the full pipeline depth of
the DMA controller.

When chaining is active, the descriptor parser fetches the next descriptor
while the current transfer is still in progress, achieving pipelined operation.
The monitor records timestamps for performance measurement.

## 6. Address Alignment Rules

Source and destination addresses must be aligned to the transfer size granularity.
For word transfers, addresses must be 4-byte aligned. Misaligned addresses
trigger an alignment error and generate an error interrupt if unmasked.

The `addr_misaligned` signal in the descriptor parser asserts when a misaligned
address is detected. The error is logged in the interrupt status register.

## 7. Interrupt System

The DMA controller supports three interrupt types:
- **Completion interrupt**: Generated when a transfer completes successfully
- **Error interrupt**: Generated on bus error, alignment error, or descriptor fetch error
- **Coalescing interrupt**: Generated when count threshold or timeout is reached

Interrupt coalescing reduces CPU overhead by batching multiple completion events.
The coalescing engine counts completions and/or waits for a configurable timeout
before asserting the interrupt output.

Masked interrupts remain pending in the status register but do not propagate
to the `irq_out` pin. When unmasked, pending interrupts are immediately forwarded.

## 8. Error Handling

Error conditions detected by the DMA controller:
- **Bus error**: AXI slave returns error response during read/write
- **Descriptor fetch error**: Cannot read descriptor from memory
- **Alignment error**: Source or destination address is misaligned
- **Timeout**: Transfer does not complete within the watchdog period

Each error condition generates an error interrupt if the corresponding mask
bit is clear. The error type is recorded in the status register for software
diagnosis.

## 9. Power Management

The DMA subsystem supports two power-saving features:
- **Clock gating**: Automatically gates the clock to idle channels. Enabled
  by `DMA_POWER.CLOCK_GATE_EN`. The `idle_detect` signal identifies channels
  that have been idle for more than 16 cycles.
- **Retention mode**: Preserves register state during power-down. Enabled by
  `DMA_POWER.RET_EN`. This feature is only available in silicon revision B
  and later. Earlier revisions ignore the retention enable bit.

## 10. AXI Burst Configuration

The AXI master interface supports three burst types:
- **INCR**: Incrementing burst, default mode
- **WRAP**: Wrapping burst at power-of-2 boundaries, enabled by `DMA_BURST_CTRL.WRAP_EN`
- **FIXED**: Fixed-address burst for FIFO access

Maximum burst length is configurable via `DMA_BURST_CTRL.MAX_LEN` (1-256 beats).
The burst controller automatically splits transfers that exceed the configured
maximum burst length.

## 11. Performance Characteristics

Peak throughput is achieved with back-to-back descriptor fetches when the
pipeline is full. The monitor module records fetch timestamps for performance
analysis. Key metrics:
- Descriptor fetch latency (from request to parse complete)
- Transfer throughput (bytes per cycle at sustained rate)
- Interrupt latency (from event to `irq_out` assertion)
