# Phase 2 — Download Transport

## Status

**Deferred by design.** The current priority is real-device validation of the Resource-first Core path, not speculative transport optimization or Video simulation.

## Validated Core boundary

The active delivery path is:

```text
Resource
   ↓
available Telegram locations
   ↓
source selection / pre-transfer failover
   ↓
Telegram bytes
   ↓
HTTP download / Range response
```

Core streaming uses a bounded application chunk size and is independent of the optional Video plugin.

## When resumed

1. Build a repeatable benchmark matrix for source, offset, range size and proxy/direct mode.
2. Measure TTFB, sustained throughput, CPU, memory, retries and Telegram request behavior.
3. Determine whether source selection, Telegram transport or deployment connectivity is the actual bottleneck.
4. Only then consider bounded parallel retrieval or other transport changes.
5. Preserve Resource identity, HTTP Range semantics and pre-transfer failover behavior.

## Video

Video playback/cache simulation is not part of this phase. It remains an optional capability outside Core and outside the current real-device test plan.

## Non-goals

- No claim of bypassing Telegram service-side limits.
- No arbitrary high concurrency.
- No Video-specific download implementation in Core.
