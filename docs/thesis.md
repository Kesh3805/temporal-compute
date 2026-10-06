# Thesis

## Research history and current direction

The Generation I incremental thesis is **retired pending contrary evidence**. TC-S1 rejected its registered claim for the fixed greedy policies on the frozen assumed EO corpus. This does not prove all scheduling algorithms lose or all time-dependent value models are useless. The [TC-S1 record](tc-s1/results.md) and original thesis text below are preserved as history.

Generation II asks a materially different question: how should a process receive additional computation as intermediate results change what is known? See the [new research statement](generation-ii.md) and independent [TC-R1 preregistration](tc-r1/preregistration.md). Adaptive progressive computation is a proposed research direction; the repository currently implements only Generation I.

## Generation I thesis (historical text)

The value of computation depends on when its result becomes available. Correctness, throughput and deadline compliance alone can fail to capture mission value. TC-0 represents a task's value as `U(task, completion_time)` and compares policies that explicitly consult that function against policies that consult only arrival order, static priority or deadline.

The runtime vision includes quality, invested compute, expected runtime and uncertainty, dependencies, contact opportunities, restart/checkpoint cost and resources. TC-0 implements only arrival, known execution cost, deadline, priority, utility and input freshness. It tests the abstraction before adding those further mechanisms.

The first question is whether a simple temporal scheduler delivers greater mission utility under constrained compute. Absolute completion utility and completion utility per unit cost are distinct heuristics. Neither anticipates future arrivals, deliberately idles, backtracks or searches schedules. Both can lose to EDF and both can starve lower-scoring work under a sustained stream.

TC-0 can establish that explicit temporal utility is executable, deterministic and measurable, and identify conditions where policies differ. It cannot establish optimality, real-world performance, spacecraft safety, superiority across workload distributions or the correctness of mission-specific utility estimates. A win on hand-built fixtures is motivation to collect independent workloads, not proof of the full thesis.
