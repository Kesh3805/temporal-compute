# Temporal Compute — central-idea recalibration brief (2026-11-21)

You are a skeptical senior research advisor. Zero budget (one laptop: i5-1135G7/16 GB, plus free GitHub Actions on a public repo). Research integrity rules: preregister before outcomes, no post-outcome tuning, report FAIL honestly. We want to STOP failing hypotheses by choosing better questions — not by lowering bars.

## The central idea (as currently stated)
"Temporal Compute controls how much computation a problem receives as its state evolves": a generic observe → estimate gain/cost/uncertainty → choose bounded unit of work → repeat/stop controller, scored by E[ΔValue]/E[Cost]. Claim to test: a reusable state/action/control abstraction buys enough over competent domain-specific adaptivity, after overhead.

## Track record
1. **Gen I (TC-S1), REFUTED.** Greedy temporal-utility scheduling of whole jobs lost 5.07% to EDF on an assumed Earth-observation corpus; all 5 gates failed. EDF captured 98.5% of oracle on derived 9-job problems.
2. **TC-R1 (path tracing, PBRT-v4)**, preregistered: marginal-value sample allocation vs uniform / adaptive / variance-guided / MC-UCB; PASS needs >=10% relative-MSE reduction vs strongest conventional, plus time, tail and perceptual guards. After review amendments the controller ≈ Neyman allocation with per-region ray costs (n ∝ σ/√c) — classical stratified sampling. Analytic ceiling of the cost lever: 1–2% (narrow ray-cost spread), ~6% at measured spread (log-sd 0.52), 9–22% only for very wide spread. References took 2^21 spp on specular scenes to converge (weeks of free CI). Execution freeze built and verified; the one comparative run is NOT launched. Expected outcome: FAIL or marginal.
3. **TC-R1E2**, fail to qualify (accounting coverage evidence incomplete); E3 then passed substrate qualification.
4. **TC-IA1 (synthetic), REFUTED:** value-of-information / robust-variance allocation does not beat plug-in cost-aware Neyman; even a clairvoyant greedy reactive oracle gains ~0. Allocation is already at the frontier.
5. **TC-IA2 (synthetic), CLOSED/mixed:** robust (biased) estimators help in some rare-spike regimes (13–18%) but are not non-inferior to the mean at high budgets.

Pattern: every time, the "smart controller" collapses into a known classical optimum (EDF, Neyman, stratified sampling) and the headroom over a competent baseline is small. We keep picking domains where decades of domain-specific adaptivity already harvested the gains.

## Questions for you
1. **Is the central idea itself wrong, or only its domains?** Steelman and then attack: "a generic marginal-value controller beats competent domain-specific adaptivity." Is there any theoretical reason to expect material (>10%) gains, or does it reduce to known results (Gittins/bandits, Neyman, rational metareasoning, anytime algorithms, Russell & Wefald)?
2. **Where is real, unharvested headroom?** Name concrete settings where (a) compute allocation decisions are currently made by fixed heuristics or uniform budgets, (b) marginal value of extra compute varies a lot across items and is observable mid-run, and (c) the baseline is NOT already an optimal classical allocator. Candidates to judge: LLM test-time compute (adaptive best-of-N / early stopping / per-query reasoning budgets), early-stopping in hyperparameter search, adaptive MCMC/ensemble stopping, progressive inference cascades, CI test selection, simulation-based inference. Prioritize what is feasible on a laptop + free CI with public data.
3. **Recalibrated claim.** Propose 2–3 alternative central claims (narrower or pivoted) with (i) prior evidence of headroom from published work — cite real papers with URLs, (ii) a cheap "headroom-first" go/no-go test computable from existing public data or logs BEFORE building any controller, (iii) the strongest baseline that must be beaten.
4. **Process change.** What rule should we adopt so we never again spend weeks on an experiment whose analytic ceiling is below its pass bar? (e.g., mandatory oracle-headroom gate.)
5. **TC-R1 itself:** launch the frozen run anyway (cheap now, honest FAIL is informative), or retire it unrun? Be decisive.

Be blunt, concise, and concrete. Distinguish what you know from what you guess. Verify any citation.
