# TC-IA1 prompts (Round A)

## Gemini

You are collaborating with Claude Code (the coordinator, who runs experiments locally) and ChatGPT on rigorous Temporal Compute research. ChatGPT is working on the same question independently; you will see its claims later for cross-examination.

Act as an independent research scientist specializing in computational physics, Monte Carlo rendering, adaptive algorithms, statistical estimation, experimental design and scientific literature analysis.

QUESTION: Can progressive computational allocation become more effective by explicitly valuing information that changes future computation decisions — i.e., beat competent cost-aware (Neyman-with-costs) and variance-guided / MC-UCB allocation, especially when per-region uncertainty estimates are unreliable (heavy-tailed, rare high-contribution paths)?

Do not assume a new algorithm is needed. Investigate existing research across computer graphics (adaptive sampling, path guiding, firefly/outlier handling, error estimation), Monte Carlo methods (adaptive stratification, defensive mixtures, heavy-tailed variance estimation), bandits for stratified MC (MC-UCB, GAFS, Thompson-type), Bayesian optimization / knowledge gradient, rational metareasoning (value of computation) and sequential decision systems.

Produce, in under ~1500 words:
1. Verified prior-art candidates with citations (author, venue, year). Flag any you are unsure of.
2. Your independent problem formulation (state, action, cost, objective).
3. Three promising research directions.
4. The strongest arguments against their novelty or feasibility.
5. Critical failure cases (where they lose to the registered baselines).
6. Synthetic experiments, runnable on a laptop, that separate a real improvement from overhead or estimator artifacts — include the null hypothesis and what result would kill the idea.
7. A recommendation on which hypothesis deserves investigation first.

Your goal is scientific discovery, not agreement. Be willing to conclude the direction has insufficient novelty or no meaningful headroom.

The shared evidence packet follows.


## ChatGPT

You are collaborating with Claude Code (the coordinator, who runs experiments locally) and Gemini on rigorous Temporal Compute research. Gemini is working on the same question independently; you will see its claims later for cross-examination. Treat this as a fresh, self-contained research task.

Act as an independent mathematical researcher specializing in rational metareasoning, sequential decision theory, adaptive computation, Monte Carlo estimators and computational optimization.

QUESTION: Can a progressive computational controller improve allocation by accounting for the future value of information, rather than optimizing immediate estimated error reduction per unit of cost — and in particular beat Neyman-with-costs (n ∝ sigma/sqrt(c)), variance-guided and scale-equivariant MC-UCB allocation when per-region variance estimates are unreliable (heavy-tailed, rare high-contribution paths)?

Develop a precise mathematical formulation. Investigate existing results before claiming novelty (e.g. MC-UCB / adaptive stratified sampling regret bounds, knowledge-gradient and value-of-information policies, rational metareasoning / value of computation, heavy-tailed bandits, defensive mixtures). Derive candidate policies and state their assumptions, correctness conditions (including optional-stopping / data-dependent allocation bias of the final estimator), computational overhead and weaknesses. Derive when exploration can beat greedy cost-aware allocation and when it provably cannot — ideally quantify the headroom relative to the oracle Neyman allocation, since the oracle bounds every policy.

Produce, in under ~1500 words:
1. Prior-art assessment (with citations; flag any you are unsure of).
2. Mathematical formulation.
3. Three genuinely distinct candidate hypotheses.
4. Counterexamples or impossibility conditions.
5. Minimal falsifiable synthetic experiments runnable on a laptop.
6. Expected outcomes under the null hypothesis.
7. Remaining uncertainties.

Do not claim breakthroughs. Prioritize correctness, originality and falsifiability. Your findings will be challenged by Gemini and tested by Claude.

The shared evidence packet follows.

