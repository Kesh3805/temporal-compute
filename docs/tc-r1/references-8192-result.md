# TC-R1 reference convergence at 8192 spp

**Source.** GitHub Actions run 40168799225, job `converge` (121101201133), artifact `tc-r1-references-converged` (id 12588934623, 45.8 MB). I read only the JSON members (`refs/convergence-8192.json` plus 30 `*.metrics.json` and 60 per-image `.json` records) through HTTP range requests on the zip. The `.npy` images were not downloaded. The converge log reports `{"converged": 5, "escalate": 25, "halt": 0}`, which matches the file (schema `tc-r1-reference-convergence-v1`, spp 8192, 30 pairs).

**Provenance checks.**
- All 60 images were rendered by the same binary (`binary_sha256 ca84d2ff...`) with 4 threads.
- Every record has empty `startup_failures`.
- The images come from run 40165734171 (23 streams) and run 40168799225 (37 streams).
- The per-image `elapsed_ns` matches the `"seconds"` line in the matrix job log. Spot check: uniform-01/f0 reference-a gives 758.8 s in both.

**Thresholds (registered).** A frame converges only if all three hold: max(rel MSE ab, ba) <= 1e-4, SSIM >= 0.995 and LPIPS <= 0.01. Otherwise it escalates to 16384 spp, then 32768 spp, then halts.

## Per-frame results (8192 spp)

| Frame | Family | max rel MSE | SSIM | LPIPS | Failed | Decision | t_a / t_b (s) |
|---|---|---|---|---|---|---|---|
| adaptive-01/f0 | adaptive-sampling-friendly | 6.34e-05 | 0.96164 | 0.03041 | SSIM, LPIPS | escalate | 625 / 621 |
| adaptive-01/f1 | adaptive-sampling-friendly | 4.62e-05 | 0.96063 | 0.02980 | SSIM, LPIPS | escalate | 443 / 438 |
| adaptive-01/f2 | adaptive-sampling-friendly | 4.44e-05 | 0.96142 | 0.02599 | SSIM, LPIPS | escalate | 432 / 901 |
| adaptive-02/f0 | adaptive-sampling-friendly | 4.63e-04 | 0.98844 | 0.00266 | MSE, SSIM | escalate | 743 / 371 |
| adaptive-02/f1 | adaptive-sampling-friendly | 4.78e-04 | 0.98787 | 0.00328 | MSE, SSIM | escalate | 744 / 519 |
| adaptive-02/f2 | adaptive-sampling-friendly | 4.64e-04 | 0.98795 | 0.00279 | MSE, SSIM | escalate | 515 / 518 |
| diffuse-01/f0 | simple-diffuse | 2.16e-04 | 0.99351 | 0.00034 | MSE, SSIM | escalate | 711 / 708 |
| diffuse-01/f1 | simple-diffuse | 2.18e-04 | 0.99345 | 0.00033 | MSE, SSIM | escalate | 351 / 338 |
| diffuse-01/f2 | simple-diffuse | 2.15e-04 | 0.99354 | 0.00032 | MSE, SSIM | escalate | 494 / 498 |
| diffuse-02/f0 | simple-diffuse | 2.16e-04 | 0.99362 | 0.00031 | MSE, SSIM | escalate | 653 / 605 |
| diffuse-02/f1 | simple-diffuse | 2.15e-04 | 0.99362 | 0.00034 | MSE, SSIM | escalate | 553 / 648 |
| diffuse-02/f2 | simple-diffuse | 2.14e-04 | 0.99368 | 0.00036 | MSE, SSIM | escalate | 651 / 344 |
| motion-01/f0 | motion-heavy | 4.92e-05 | 0.99548 | 0.00027 | none | **converged** | 582 / 416 |
| motion-01/f1 | motion-heavy | 4.10e-05 | 0.99589 | 0.00027 | none | **converged** | 389 / 578 |
| motion-01/f2 | motion-heavy | 4.55e-05 | 0.99538 | 0.00025 | none | **converged** | 840 / 581 |
| motion-02/f0 | motion-heavy | 2.73e-04 | 0.99124 | 0.00066 | MSE, SSIM | escalate | 719 / 717 |
| motion-02/f1 | motion-heavy | 2.64e-04 | 0.99126 | 0.00070 | MSE, SSIM | escalate | 496 / 491 |
| motion-02/f2 | motion-heavy | 2.59e-04 | 0.99026 | 0.00066 | MSE, SSIM | escalate | 516 / 740 |
| specular-01/f0 | highly-specular | 1.74e-02 | 0.87468 | 0.05146 | MSE, SSIM, LPIPS | escalate | 971 / 466 |
| specular-01/f1 | highly-specular | 1.66e-02 | 0.86648 | 0.05698 | MSE, SSIM, LPIPS | escalate | 481 / 760 |
| specular-01/f2 | highly-specular | 1.49e-02 | 0.87294 | 0.05326 | MSE, SSIM, LPIPS | escalate | 438 / 470 |
| specular-02/f0 | highly-specular | 8.56e-03 | 0.90809 | 0.04459 | MSE, SSIM, LPIPS | escalate | 1082 / 1084 |
| specular-02/f1 | highly-specular | 2.32e-02 | 0.91506 | 0.04061 | MSE, SSIM, LPIPS | escalate | 531 / 1083 |
| specular-02/f2 | highly-specular | 1.48e-02 | 0.90982 | 0.04255 | MSE, SSIM, LPIPS | escalate | 517 / 517 |
| uniform-01/f0 | uniformly-noisy | 2.41e-04 | 0.99661 | 0.00026 | MSE | escalate | 759 / 407 |
| uniform-01/f1 | uniformly-noisy | 2.39e-04 | 0.99664 | 0.00026 | MSE | escalate | 826 / 470 |
| uniform-01/f2 | uniformly-noisy | 2.41e-04 | 0.99660 | 0.00024 | MSE | escalate | 676 / 846 |
| uniform-02/f0 | uniformly-noisy | 7.65e-05 | 0.99616 | 0.00023 | none | **converged** | 608 / 614 |
| uniform-02/f1 | uniformly-noisy | 4.63e-05 | 0.99615 | 0.00025 | none | **converged** | 434 / 435 |
| uniform-02/f2 | uniformly-noisy | 1.07e-04 | 0.99620 | 0.00024 | MSE | escalate | 876 / 890 |

The ab and ba relative MSEs agree to about 4 significant figures in every frame.

## Counts per family

| Family | Converged | Escalate | Halt |
|---|---|---|---|
| uniformly-noisy | 2 | 4 | 0 |
| motion-heavy | 3 | 3 | 0 |
| simple-diffuse | 0 | 6 | 0 |
| adaptive-sampling-friendly | 0 | 6 | 0 |
| highly-specular | 0 | 6 | 0 |
| **Total** | **5** | **25** | **0** |

Families are taken from `research/tc-r1/corpus/manifest.json`. Convergence is decided per scene, not per family. The three frames of each scene behave almost identically. The exception is uniform-02/f2 at 1.07e-4, which misses the MSE threshold by 7%.

## Which criterion drives non-convergence (25 escalated frames)

**Failure counts.**
- MSE fails in 22 frames.
- SSIM fails in 21 frames.
- LPIPS fails in 9 frames: adaptive-01 and both specular scenes.
- In 4 frames MSE is the only failure: uniform-01 x3 and uniform-02/f2.
- In 3 frames MSE passes but SSIM and LPIPS fail: adaptive-01 x3.

**Binding criterion.** This is the criterion that is furthest past its threshold. For SSIM the overshoot is measured as (1 - SSIM) / 0.005.
- **Relative MSE binds in 22 of 25 frames.**
  - diffuse: about 2.15x.
  - motion-02: 2.6-2.7x.
  - uniform-01: 2.4x.
  - uniform-02/f2: 1.07x.
  - adaptive-02: 4.6-4.8x.
  - specular: 86-232x.
- **SSIM binds in 3 frames (adaptive-01).** 1 - SSIM is about 0.039, which is 7.7-7.9x its threshold. LPIPS is 2.6-3.0x its threshold there, and MSE already passes.

## Per-stream render time (8192 spp, 4 threads, GitHub-hosted runners)

| Group | Streams | min s | median s | max s | sum s |
|---|---|---|---|---|---|
| all | 60 | 338 | 579 | 1084 | 36,730 |
| adaptive-sampling-friendly | 12 | 370 | 518 | 901 | 6,869 |
| highly-specular | 12 | 438 | 523 | 1084 | 8,399 |
| motion-heavy | 12 | 388 | 579 | 839 | 7,065 |
| simple-diffuse | 12 | 338 | 578 | 710 | 6,554 |
| uniformly-noisy | 12 | 407 | 644 | 889 | 7,841 |
| escalated frames only | 50 | 338 | 578 | 1084 | 31,253 |

Times are wall clock from `elapsed_ns`. The two streams of one frame often differ by up to 2x, for example adaptive-02/f0 at 743 s vs 371 s, and specular-02/f1 at 531 s vs 1083 s. That points to runner-speed variance rather than scene cost. Family differences are smaller than this noise.

## Projections

**Render time.** This assumes time scales linearly with spp, at the same runner mix.

| spp | Per-stream median | Per-stream max | Streams | Total compute |
|---|---|---|---|---|
| 16384 | ~1,160 s (19 min) | ~2,170 s (36 min) | 50 (25 escalated frames) | ~62,500 s (~17.4 h) |
| 32768 | ~2,320 s (39 min) | ~4,340 s (72 min) | 48 (24 frames, see below) | ~118,000 s (~32.8 h) |

The 32768 total is 4x the 8192 times of those 24 frames. Even the slowest stream at 32768 (~72 min) stays well under a 6 h job limit.

**Convergence.**

*Assumption (explicit).* Relative MSE between two independent streams halves with each doubling of spp. That is, per-pixel variance goes as 1/spp for unbiased estimators. The projected MSE is 1/2 at 16384 and 1/4 at 32768. Applied by analogy:
- 1 - SSIM also halves per doubling.
- For LPIPS, two cases are shown: it halves per doubling (optimistic), or it falls by 1/sqrt(2) per doubling, i.e. it tracks noise amplitude (pessimistic).

Heavy-tailed noise such as specular fireflies may converge more slowly than this.

| Frames | Projected at 16384 | Projected at 32768 | Outcome |
|---|---|---|---|
| uniform-02/f2 | MSE 5.4e-5 | - | converges at 16384 |
| uniform-01 x3 | MSE 1.19-1.21e-4 (fail, ~20% over) | MSE 6.0e-5 | converges at 32768 |
| diffuse-01, diffuse-02 x6 | MSE ~1.08e-4 (fail, ~8% over); SSIM 0.9967 | MSE ~5.4e-5 | converges at 32768 |
| motion-02 x3 | MSE 1.29-1.36e-4 (fail); SSIM 0.9951-0.9956 | MSE 6.5-6.8e-5 | converges at 32768 |
| adaptive-02 x3 | MSE 2.31-2.39e-4 | MSE 1.16-1.19e-4 (16-19% over); SSIM ~0.997 and LPIPS pass | **at risk of halting** (needs ~39-40k spp by MSE) |
| adaptive-01 x3 | SSIM ~0.981 | SSIM 0.990-0.9904 (fail); LPIPS 0.0065-0.0076 if halving, 0.013-0.015 if 1/sqrt(2) | **halt projected** (SSIM needs ~65k spp) |
| specular-01 x3, specular-02 x3 | MSE 4.3e-3 to 1.2e-2 | MSE 2.1e-3 to 5.8e-3; SSIM 0.967-0.979; LPIPS 0.010-0.014 even if halving | **halt projected**, all three criteria fail; MSE needs ~6-8 more doublings beyond 8192 (about 0.7-1.9M spp) |

**Summary under the stated assumption.**
- 1 frame converges at 16384.
- 12 frames converge at 32768.
- 12 frames are projected to halt at 32768: specular-01 x3, specular-02 x3, adaptive-01 x3 and adaptive-02 x3.
  - adaptive-02 is the borderline case: about 16-19% over the MSE threshold.
  - The specular and adaptive-01 halts are not borderline.

Final tally: 5 + 1 + 12 = 18 converged, 12 halted.

**Caveat on the projection.** It is extrapolated from one spp level. The 16384 run (commit d79d265) will give a second point to test whether MSE actually halves, especially for the specular scenes.
