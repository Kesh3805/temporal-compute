# Claude — blind hypotheses (written 2026-11-03 before reading ChatGPT or Gemini)

Setting: stratified MC with known stratum weights w_r, per-sample cost c_r, unknown sigma_r.
Final MSE (independent strata, unbiased per-stratum means) = sum_r w_r^2 sigma_r^2 / n_r.
Oracle under budget B = sum n_r c_r: n_r ∝ w_r sigma_r / sqrt(c_r); MSE* = (sum_r w_r sigma_r sqrt(c_r))^2 / B.
Every policy is bounded below by MSE* (in expectation, for allocations independent of the sample values used in the estimate; adaptive reuse adds bias terms of lower order).

C1 (headroom test, decisive). The headroom for ANY information-aware policy over MC-UCB is
  MSE(MC-UCB)/MSE* - 1. MC-UCB's regret is O~(n^{-3/2}) relative to MSE* ~ n^{-1}, so headroom vanishes
  asymptotically; it can only exist pre-asymptotically, where rare events in some strata are still
  unobserved. Measure the gap oracle vs baselines on synthetic heavy-tailed strata across budgets.
  If the gap is < 10% wherever the registered budgets sit, no allocation idea can clear a 10% bar.

C2 (tail-aware variance belief). Plug-in sample variance underestimates sigma for heavy-tailed strata at
  small n (it is usually small until the first rare event lands). Pooling the tail shape across strata
  (empirical-Bayes / hierarchical prior on the "rare-event rate x magnitude") gives a posterior mean of
  sigma^2 that is larger for under-sampled strata and allocates more to them. Prior art: variance shrinkage
  (e.g. limma-style moderated variances), defensive mixtures. Novelty expected low; value is empirical.

C3 (metric artifact). The registered metric averages log relative MSE. For heavy tails, E[MSE] is
  dominated by rare draws, while E[log MSE] tracks typical behavior. A policy that explores to protect
  expected MSE can lose on mean log-MSE, and a policy that ignores rare events can win on it.
  Any information-aware claim must be evaluated on both, or it may be a metric artifact.
