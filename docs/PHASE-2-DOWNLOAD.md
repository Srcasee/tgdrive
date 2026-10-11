# Deferred Download Optimization Directions

## Status

**Not scheduled; no optimization work is being implemented now.** First keep the existing Resource download path correct and investigate download resume/completion state consistency.

This document replaces the previous detailed transport-optimization plan. The items below are only a future outline; they are not commitments, target values, or instructions to start implementation.

## Future investigation outline

1. **Measure before changing transport**
   - Capture time-to-first-byte, upstream Telegram throughput, downstream HTTP throughput, queue wait, transfer duration, retries, CPU/memory and proxy/direct mode.
   - Use the measurements to identify the constrained segment rather than assuming concurrency is the answer.

2. **Automatic fast-source selection**
   - Candidate sources must refer to the same Telegram `chat_id + message_id`.
   - Consider ranking sources using recent observed throughput and health from real transfers.
   - Avoid unconditional pre-download probes unless measurements show they are worth their added traffic and startup delay.
   - Preserve offset-based failover; SHA-256 is not a prerequisite for choosing another account path to the same message.

3. **Single-file parallel range retrieval**
   - Consider bounded parallel retrieval only if measurements show a single Telegram or HTTP connection is the limiting factor.
   - Preserve exact byte ranges, HTTP Range behavior, cancellation, bounded memory and safe retry semantics.
   - Account for extra Telegram requests, connection pressure, resource use and rate-limit risk.

4. **Validation before adoption**
   - Compare against the current sequential implementation on real devices.
   - Record throughput, startup latency, request count, memory/CPU, failures and rate-limit symptoms.
   - Do not claim that concurrency bypasses Telegram service-side limits.

## Explicitly deferred

- No automatic source-speed scoring implementation now.
- No active probing of every source before each download.
- No single-file parallel range implementation now.
- No arbitrary increase in concurrency.
- No Video-specific transport or cache implementation in Core.
