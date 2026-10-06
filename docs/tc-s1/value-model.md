# Value model

One utility point is neither dollars, probability of mission success nor ESA's priority scale. Points are experimental interval-scale units of relative useful mission output, with an assumed common zero and additive meaning across products. Merely ordinal rankings would not justify summing points or comparing percentage gains; TC-S1 explicitly assumes the stronger interval-scale interpretation. That assumption is uncertain and not externally validated.

Every class's base utility is drawn independently of execution cost and arrival. Class membership induces declared cost/value associations, but important work is not invariably cheap. Importance and urgency are independent concepts: disaster mapping is high-value/slow, cloud screening low-value/fast, wildfire high-value/fast, and routine compression lower-value/slow. Fixed priorities rank declared mission importance, not urgency. Within-class base values vary without changing static priority.

| Class | Purpose | Cost seconds | Base points | Curve | Deadline age seconds | Freshness age seconds | Priority |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| CLOUD_SCREEN | Useful/cloudy mask for an eligible tile | 1–3 | 8–20 | linear | 30–90 | 20–60 | 1 |
| WILDFIRE_ALERT | Candidate fire-scene alert product | 8–24 | 100–160 | exponential | 60–120 | 45–90 | 5 |
| VESSEL_DETECTION | Vessel awareness/classification product | 4–12 | 40–80 | step | 120–240 | 90–180 | 2 |
| MARINE_ANOMALY | Candidate pollution/anomaly product | 6–18 | 60–100 | exponential | 240–480 | 180–360 | 3 |
| IMAGE_COMPRESSION | Standalone reusable compressed image | 8–24 | 20–50 | constant | 600–900 | 600–1200 | 0 |
| DISASTER_MAPPING | Candidate emergency street/access map | 16–40 | 100–160 | linear | 300–600 | 240–600 | 4 |

All numerical fields are **D**, not mission facts. Class existence is grounded in the evidence dossier. Costs are relative normalization; values encode a fictional mission's importance; age budgets encode an assumed operational response cycle; priorities are a competent static approximation to that importance. Each range is an inclusive integer distribution. Each is uncertain: cost/intensity affect contention; base values affect cross-class tradeoffs; age/decay assumptions affect urgency; priorities omit within-class variation. Prespecified sensitivity sweeps address these concerns without changing the policies.

Wildfire exponential intervals are 10–20 seconds with retention 850,000–950,000 ppm per interval. Marine intervals are 30–60 seconds with retention 950,000–990,000 ppm. Vessel utility becomes `floor(0.7*base)` at age 30–60 seconds and `floor(0.2*base)` at age 90–120 seconds. Constant, linear, geometric fixed-point and step semantics are exactly [TC-0's documented semantics](../assumptions.md). Linear decay shares its endpoint with deadline; sensitivity cannot separate those two effects without changing the simulator, so we report the coupling explicitly.

Wildfire and disaster-mapping requests are declared critical. A critical success requires completion retaining at least half of base utility; this is an experimental response criterion, not a safety standard. Report both classes separately so successful mapping cannot conceal failed wildfire alerts. Utility retained, expired-unstarted jobs and zero-utility completions are separate outcomes. These are simulated job-level metrics, not incident-level alerts saved or lives protected.
