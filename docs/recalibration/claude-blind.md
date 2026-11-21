# Claude's blind position (written before reading ChatGPT/Gemini replies, 2026-11-21)

1. **The central idea, as stated, is close to unfalsifiable-then-trivial.** "Allocate compute by marginal value" is
   the definition of rational metareasoning (Russell & Wefald 1991). When the value model is accurate it reduces to
   the domain's known optimum (EDF, Neyman, Gittins); when it's inaccurate it loses. A *generic* controller can only
   win materially where the incumbent is **not** a value-aware allocator. The idea isn't wrong; our domain choices
   kept placing it against incumbents that already are one.
2. **Necessary conditions for >10% headroom:** (a) large heterogeneity in the marginal value of compute across items,
   (b) that heterogeneity is predictable from cheap, early, observable signals, (c) the incumbent ignores it (uniform
   or fixed budgets), (d) value curves have diminishing or saturating returns so stopping early frees real budget.
   Path tracing fails (c); EO scheduling failed (a)/(b).
3. **Best-fitting pivot: LLM test-time compute allocation** (per-query adaptive sampling / early stopping of
   self-consistency votes). Incumbent is often fixed N per query; per-query difficulty varies enormously; vote
   agreement is a cheap mid-run signal. Crucially, **headroom can be measured offline from public logged samples**
   (many benchmarks release N samples per question) — oracle allocation vs uniform at matched sample counts, no
   controller built. Risk: literature is crowded (adaptive-consistency, early-stopping self-consistency), so the
   strong baseline is those methods, not uniform.
4. **Process rule:** no experiment proceeds unless an *oracle-headroom gate* — the best allocation computable with
   hindsight on cheap existing data — exceeds the pass bar by a margin (e.g., oracle gain ≥ 2× bar vs the strongest
   baseline). TC-R1 would have been stopped on 2026-10-25 by its own ceiling analysis.
5. **TC-R1:** launch it. Everything is frozen and paid for; cost is free CI hours; an honest preregistered FAIL
   closes the path-tracing question cleanly and is publishable as a negative result. Do not invest anything further
   in it beyond reporting.
