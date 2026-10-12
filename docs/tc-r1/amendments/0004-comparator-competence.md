# Proposed amendment 0004: scale-equivariant MC-UCB and a defensive floor

Status: **adopted by maintainer decision 2026-10-12, with symmetry option A, before
outcomes; effective only if the v2 offline validation passes.** Proposed and
adopted the same day. The original protocol `99ad341`, amendments
0001–0003, the [baseline contract](../../../research/tc-r1/baseline-contract.json),
the controller contract and all evidence, including the
[offline gate result](../offline-gate-result.md), remain unchanged. Binding draft:
[comparator-amendment-0004.json](../../../research/tc-r1/comparator-amendment-0004.json).
No primary rendering, reference or comparative outcome exists.

## Why an amendment, and what may justify it

The offline gate returned AMEND-BASELINE: MC-UCB failed its frozen competence
criteria and variance-guided failed the rare-spike guard. Under the gate's
contract, any change must be justified **independently of those numbers**. The
gate only identifies *which* properties to examine. Each change below rests on
a property the method should have regardless of any result, uses registered or
bound-derived constants rather than values fitted to the gate, and is
re-validated on **fresh** seeds with the **unchanged** criteria.

## Change 1: MC-UCB exploration in the observations' own scale

**Property.** Radiance units are arbitrary: multiplying a scene's emission by a
constant changes no allocation-relevant structure. A conventional allocator
should be scale-equivariant: scaling every observation by `c > 0` scales every
index by `c` and leaves every decision unchanged. Variance-guided already has
this property. MC-UCB's bonus `2β/sqrt(n)` with β in absolute radiance units
does not. In Carpentier, Munos and Antos (JMLR 2015) the bonus is a deviation
bound and carries the units of the observations; an absolute constant is a
units error of the adaptation, not a feature of the published method.

**Rule.** At the end of the common 16-spp initialization, compute once from the
**allocation** observations every policy already receives:

`S = sqrt(median_r V_r)`, the square root of the median over regions of the
registered RGB-mean within-pixel variance scalar.

The index becomes `(sqrt(V) + 2·β·S/sqrt(n)) / n` with **β = 1.0 unchanged**, now
dimensionless. `S` is frozen for the rest of the unit. The median is used because
a few rare-event regions cannot move it; it is not chosen to optimize any score.
If `S = 0` (every region shows zero variance), fall back to least coverage with
the existing geometry ties, as variance-guided already does.

`S` is a function of legal allocation-stream state only: no reference,
production value, future sample or controller output.

## Change 2: defensive coverage floor for adaptive conventional methods

**Property.** Greedy variance-proportional allocation can starve a region whose
pilot samples missed a rare, high-contribution event. That is the known failure
mode of adaptive and importance sampling. Defensive mixtures (Hesterberg,
Technometrics 1995; Owen and Zhou, JASA 2000) bound it by reserving a fixed
fraction of the uniform allocation, which caps worst-case variance relative to
uniform.

**Rule.** For MC-UCB and variance-guided, after initialization: if any region has
`n_r < α · mean_r(n_r)`, the next request goes to the least-covered such region
(geometry ties). Otherwise the method's own index chooses. **α = 0.5.**

**Why 0.5.** With `n_r ≥ α · n̄` for every region, each region's estimator
variance is at most `1/α` times its variance under uniform allocation of the
same total, so total error is at most `1/α = 2×` uniform's, up to one
4-spp batch of rounding. The value is chosen from that worst-case bound; it is
not fitted to the gate. Uniform is unchanged.

## Decision item: symmetry with the controller

Track B requires shared minimum-coverage mechanics across policies. The floor is
an allocation constraint, not a ranking signal. Two defensible choices:

- **A (recommended; adopted).** Apply the identical floor to the controller and both
  ablations as a shared coverage rule. This keeps one coverage semantics and
  stops a comparator from receiving a protection the controller lacks, or the
  reverse. It amends the frozen controller contract, before outcomes.
- **B.** Apply it to conventional methods only, keeping the controller contract
  frozen. The controller's own exploration step remains its only protection.

The scale normalization of Change 1 applies only to MC-UCB, the method whose
index is scale-dependent.

## Validation before adoption takes effect

A new offline contract, `tc-r1-offline-gate-v2`, committed before running:

- Same simulator, fields, scales, horizons, metric and **unchanged** criteria
  C1–C4 as v1.
- **Fresh seeds** 3, 4, 5 under a new derivation namespace
  `tc-r1-offline-gate-v2|field|seed`, so the amended methods are not judged on
  the draws that motivated them.
- Report amended and original methods side by side. Identifiability is re-run
  only if decision A is chosen.
- One execution.

Outcomes:

- **Amended MC-UCB COMPETENT:** the amendment takes effect for the execution
  freeze.
- **Not competent:** stop. Record that no competent strong conventional baseline
  exists under this design and return to a maintainer decision. No second
  parameter round may be run against the same criteria.

## Limits

Equivariance and the defensive bound are properties, not evidence of competence
on the corpus. The floor trades some smooth-field efficiency for worst-case
protection; that trade is accepted up front. Controller-side questions remain
separate decisions and are out of scope: the wall-clock cost predictor and the
noisy recent-improvement term. So are host, stopping/censoring, references and
the execution freeze. Issue #9 stays open.
