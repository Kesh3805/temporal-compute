SHARED EVIDENCE PACKET — exploratory study TC-IA1 (information-aware allocation)
Source: public repo github.com/Kesh3805/temporal-compute, branch research/tc-r1-execution-runner @ 445240e (2026-11-03). Facts below are from that repo; nothing here is a TC-R1 outcome.

DOMAIN
- Progressive Monte Carlo rendering: PBRT-v4 unidirectional path tracer, 256x256 frames, image split into 16x16-pixel regions (256 regions). All policies share one kernel/estimator; only allocation differs.
- Common 16-spp initialization for every region, then the policy repeatedly picks one region and renders one 4-spp batch there. Cost is charged in traced rays (primary + continuation + shadow + any probes); rays per sample vary by region.
- Quality metric: relative linear-radiance MSE vs an independent high-sample reference, log-averaged over ray checkpoints 2^20, 2^22, 2^24, 2^26 per frame. Also reported: worst 16x16-region relative MSE, SSIM, LPIPS, end-to-end time (controller overhead counted).

REGISTERED POLICIES IN THE FROZEN TC-R1 STUDY
1. Uniform.
2. Variance-guided: approximates n_r ∝ sigma_r (pick region with largest estimated error reduction per sample).
3. MC-UCB (Carpentier, Munos, Antos JMLR 2015), made scale-equivariant: index (sqrt(V_r) + 2*beta*S/sqrt(n_r)) / n_r, beta=1, S = sqrt(median_r V_r) frozen after init.
4. Controller: expected error reduction per charged ray (≈ Neyman allocation with unequal costs, n_r ∝ sigma_r/sqrt(c_r)) plus a noisy recent-improvement term.
- All adaptive policies share a defensive coverage floor: if any n_r < 0.5*mean(n), sample the least-covered region (bounds error at 2x uniform; Hesterberg 1995, Owen & Zhou 2000).

WHAT IS ALREADY KNOWN (analytic, pre-outcome)
- The controller differs from variance-guided mainly through cost-awareness. Theoretical ceiling of that lever: ~1–2% if rays/sample spread is narrow (2–5 rays), ~6% for lognormal spread sd 0.5 (the measured fixture had log sd 0.52), 9–22% for wide spreads. The preregistered PASS bar is >=10% relative-MSE reduction vs the strongest conventional method, so a PASS on the cost lever alone is not expected.
- Heavy tails dominate: specular/caustic and "adaptive" scenes needed >= 2^20 spp before two independent references agreed to relative MSE <= 1e-4. Rare high-contribution paths make per-region sample variance an unreliable, usually underestimated, signal at low n.
- Overhead matters: render cost is ~6 ms per 1024 samples per request on a hosted runner; controller/dispatch overhead counts against any policy.

CONSTRAINTS FOR THIS EXPLORATION
- TC-R1 is frozen: no use of its primary scenes, references or outcomes; no tuning against them. New ideas need their own preregistration.
- Zero budget: laptop (i5, 16 GB) + free GitHub Actions only. Start with analysis and small synthetic experiments (e.g. synthetic stratified heavy-tailed populations with per-stratum costs), rendering only if a hypothesis survives.
- Any probe/pilot sample used to decide must be charged to the policy's budget.
