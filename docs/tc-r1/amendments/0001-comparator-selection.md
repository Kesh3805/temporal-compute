# TC-R1 pre-outcome amendment 0001: corpus-level conventional comparators

Date: 2026-10-06. Original registration `99ad341775ed3e60bd262134783eeb2244700e76` and tag `tc-r1-protocol-preregistered` are preserved unchanged. No TC-R1 comparative rendering outcomes exist. This clarifies comparator selection before TC-R1E; it does not change thresholds, scenes, budgets or primary outcomes.

The **primary conventional comparator** is one registered method with the smallest corpus-level mean log relative MSE, equal-weighted over the ten scenes/eight seeds and their three frames/four checkpoints as specified in the protocol. Exponentiating gives its geometric aggregate error. Select once from the full original corpus aggregate. Do not select a different method per scene, seed, frame or checkpoint, or concatenate winners into an oracle-like super-baseline.

The **time conventional comparator** is selected independently: one registered method with the smallest corpus-level restricted mean time to the joint quality target, under the common frozen time cap and censoring/evaluation rules. It may differ from the primary quality comparator, but its identity is fixed globally for that analysis. Never minimize time separately per render and pool those minima.

Tie order for both is uniform, conventional adaptive, variance-guided, then compatible renderer-native adaptive. Exact equal aggregate values tie; do not invent a tolerance after seeing results. Native eligibility must be settled and registered before execution.

Report the controller versus **every individual registered conventional method**, their aggregates, paired effects, intervals, wins/ties/losses, family results and comparator identities. The chosen identity comes from the original full-sample aggregate and is held fixed in its paired bootstrap analysis; do not reselect winners within bootstrap replicates. Required beneficial intervals against every baseline remain required.

The original per-checkpoint regional and perceptual guards remain mandatory for the preregistered PASS gate. Their per-case envelopes must be explicitly labeled guard envelopes rather than a measured conventional policy. They cannot become the primary or time comparator or a synthesized policy. Also report those guards against each individual method. No aggregate quality or time claim may use a per-case best-of-methods envelope.

TC-R1E must freeze executable synthetic selection/censoring fixtures demonstrating this distinction before comparative runs. The current amendment provides that selection logic and tests without any renderer/controller comparison.
