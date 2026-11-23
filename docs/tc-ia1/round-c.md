# TC-IA1 Round C — final interpretations (2026-11-03)

Both models received the E1 table and the floor decomposition and were asked for interpretation only.
ChatGPT's first Round C reply failed in the UI ("couldn't load", nothing on the backend); one retry produced it.

## Gemini

- Accepts the reading "completely"; calls the floor-matched oracle decomposition decisive.
- Proposes a "conditional realized-error oracle" defined with V̂_r,init — the run's own pilot variance.
  **Coordinator note:** that is the plug-in rule itself, not a bound. Claude implemented a genuine
  current-state oracle instead (E2).
- Next question: shift from allocator optimization to **estimator optimization** — can biased robust
  estimators (Catoni M-estimators, firefly re-weighting, truncated shrinkage) beat the unweighted mean under
  heavy tails by more than allocation tuning ever could?

## ChatGPT

- Accepts closure; qualifications: spatial covariance changes effective sample size, log-averaged MSE is a
  different objective from expected variance, 12 scenes × 2 seeds supports the registered kill decision, not
  universal impossibility.
- Correct adaptive benchmark: R*_adaptive(B) = inf over admissible (budget-feasible, non-anticipating,
  same kernel/estimator/charging) policies of E[L], with L equal to the registered metric including
  checkpoint aggregation; a clairvoyant version conditions on latent scene parameters but never on future
  samples. A hindsight oracle that sees future outcomes is inadmissible. Neither bound is generally computable.
- Next question: **can Temporal Compute exploit predictable spatial covariance or reusable path information to
  reduce error per charged ray** (unbiased shared-sample estimators, control variates, correlated sampling),
  rather than merely redistribute independent samples?

## Convergence

Independently, both models move from *where to sample* to *what the estimator does with the samples*.
They differ on bias: Gemini accepts biased robust estimators; ChatGPT prefers unbiased covariance-exploiting
ones. That difference is testable and is the natural axis of the next study.
