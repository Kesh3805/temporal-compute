# ADR-0003: Integer microseconds and utility

Status: accepted.

Use `u64` microseconds for time/duration and `u64` utility points. Check total bounds and time addition. Use `u128` intermediate multiplication for linear decay, fixed-point exponential and density comparisons. This avoids floating-point policy decisions and nondeterministic math libraries at the cost of explicit quantization. Ratios and averages use floating point only after execution.
