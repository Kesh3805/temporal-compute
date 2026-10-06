# TC-R1 evidence and prior-work boundary

Reviewed 2026-10-06. No TC-R1 rendering outcomes have been collected. References establish existing methods and measurement limits; none demonstrates a Temporal Compute advantage.

| Primary source | What it supports | Implication for TC-R1 |
| --- | --- | --- |
| [PBRT, fourth edition: path tracing](https://pbr-book.org/4ed/Light_Transport_I_Surface_Reflection/Path_Tracing) and [efficiency](https://pbr-book.org/4ed/Monte_Carlo_Integration/Improving_Efficiency) | Monte Carlo light transport, estimator construction and variance/cost tradeoffs | Shared integrator and sampling semantics; rays, samples and time are distinct resources |
| [Rousselle, Knaus, Zwicker, Adaptive Sampling and Reconstruction using Greedy Error Minimization, 2011](https://www.cs.umd.edu/~zwicker/publications.html) | Existing adaptive allocation/error-minimization research | Marginal-error allocation is prior art, not an invention established by naming it TC |
| [Tamstorf and Jensen, Adaptive Sampling and Bias Estimation in Path Tracing, 1997](https://cseweb.ucsd.edu/~henrik/papers/adaptive_sampling/) | Adaptive sample selection/stopping can introduce bias | Independent reference streams and explicit estimator/bias review are required; state-aware allocation alone is not correctness |
| [Russell: rational metareasoning](https://people.eecs.berkeley.edu/~russell/research-bo.html) | Computation selected by expected value of improving a decision | No novelty claim for the generic marginal-value equation; overhead and delayed information matter |
| [Wang et al.: SSIM reference page](https://www.ece.uwaterloo.ca/~z70wang/research/ssim/) | Structural image-quality measurement, with defined implementation/scaling choices | Pin the image transform, range, window and implementation; do not label SSIM exact correctness |
| [Zhang et al.: LPIPS project/paper](https://richzhang.github.io/PerceptualSimilarity/) | Learned perceptual similarity and provided model/code | Pin model weights, software and preprocessing; count evaluation cost and do not train on the test scenes |

The 2011 paper was located through the authors' publication page; its PDF was not retrieved successfully in this session. This registration makes no claim to reproduce that paper's complete algorithm. An independently validated conventional adaptive implementation is required before execution, and any named paper-reproduction claim requires reading and matching the actual method.

Scene-family choices, seed count, numerical benefit thresholds and error tolerances in the protocol are **experimental design choices**, not measured renderer performance or perceptual acceptance standards. No existing rendered image, dataset, runtime measurement, kernel revision or GPU model is invented here.
