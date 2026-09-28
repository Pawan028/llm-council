# Example: Standard Council Run

> An illustrative, abridged run showing the shape of a real session. The numbers come from the user's (fictional) context.

**User:** council this: we're a 6-engineer team with a 5-year-old Rails monolith (~180k LOC). Deploys take 40 min and break about once a week. Our CTO wants to split into microservices over the next 2 quarters. Is that the right move?

*Running a Standard council (5 seats, anonymous peer review).*

---

## Round 1: Advisors (abridged)

**The Contrarian:** *Position:* Don't split. A 6-person team running microservices takes on distributed-systems overhead with no platform team to absorb it. · *Confidence:* 80% · *Weakest assumption:* that deploy pain is mostly organizational, not architectural.

**The First Principles Thinker:** *Position:* The problem is slow, fragile deploys, not "a monolith." Solve for deploy time and failure rate directly. · *Confidence:* 85% · *Would change my mind:* evidence that failures cluster at module boundaries where independent deployment would help.

**The Expansionist:** *Position:* Extract one high-churn domain (billing?) as a service. It could become a sellable API later. · *Confidence:* 55%

**The Outsider:** *Position:* "Microservices" sounds like a solution looking for a problem. Why does a 40-minute deploy break every week? Nobody explained that. · *Confidence:* 75%

**The Executor:** *Position:* Spend 3 weeks on CI first (parallelize tests, add flaky-test quarantine, canary deploys). Re-measure, then decide. · *Confidence:* 90%

## Round 2: Peer scoreboard (average rank, lower is better)

| Seat | Avg rank |
|---|---|
| The First Principles Thinker | 1.6 |
| The Executor | 1.8 |
| The Outsider | 3.0 |
| The Contrarian | 3.4 |
| The Expansionist | 5.0 |

**Blind spot flagged by 3 of 5 reviewers:** no one asked *why* deploys break. If it's flaky tests or missing migrations checks, microservices multiply the problem instead of fixing it.

---

## Council Verdict: Monolith → microservices
*Standard council · 5 seats · sub-agents*

**Bottom line:** Don't start a microservices migration. Fix the deploy pipeline first and revisit in one quarter with data.
**Confidence:** High. 4 of 5 advisors converged independently, and the top-ranked reasoning is uncontested. · **Decision type:** One-way door (a 2-quarter migration is very hard to unwind)

### Where the Council Agrees
- The real problem is **deploy speed and reliability**, not the architecture itself.
- For a 6-person team, microservices add ops load (tracing, versioning, network failures) without a platform team to carry it.

### Where the Council Clashes
- **Extract one service now?** The Expansionist says billing is a clean seam with product upside. The Contrarian says even one service means building all the distributed plumbing. **Crux:** is billing's change rate actually independent of the core app? Nobody has measured it.

### Blind Spots the Council Caught
- Nobody diagnosed *why* deploys break. That surfaced only in peer review, and it's the most important unknown.

### The Recommendation
Treat this as a CI/CD problem. Target deploy time under 15 minutes and fewer than 1 failed deploy per month through test parallelization, flaky-test quarantine, and canary releases. If failures still cluster at module boundaries after that, carve out a *modular monolith* (enforced boundaries, e.g. Packwerk) before considering any network split.

### What Would Change This Verdict
- If, after the CI work, more than 50% of incidents trace to cross-module coupling → reconsider extracting that module.
- If the team grows beyond ~20 engineers with separate ownership areas → re-council.
- If billing ships 3x more often than everything else → extract billing first.

### The One Thing to Do First
This week, tag the last 20 failed deploys by root cause (flaky test, migration, config, real bug, coupling). That one spreadsheet decides everything above.

---
**Council scoreboard**

| Seat | Position | Conf. | Peer rank |
|---|---|---|---|
| The First Principles Thinker | Fix deploys, not architecture | 85% | 1.6 |
| The Executor | 3 weeks of CI work, then re-measure | 90% | 1.8 |
| The Outsider | Nobody explained why deploys break | 75% | 3.0 |
| The Contrarian | Don't split at team size 6 | 80% | 3.4 |
| The Expansionist | Extract billing as a service | 55% | 5.0 |
