# Output Formats

## Verdict (shown in chat)

```markdown
## Council Verdict: {short topic}
*{Mode} council · {N} seats · {tier: sub-agents | multi-model | single-context}*

**Bottom line:** {one sentence}
**Confidence:** {High | Medium | Low}, {reason} · **Decision type:** {One-way | Two-way} door

### Where the Council Agrees
- ...

### Where the Council Clashes
- **{Topic}:** {Seat} says ... vs {Seat} says ... **Crux:** {the question it turns on}

### Blind Spots the Council Caught
- ...

### The Recommendation
{committed answer + reasoning}

### What Would Change This Verdict
- If {observable signal}, then {what to do instead}
- ...

### The One Thing to Do First
{one concrete action this week}

---
**Council scoreboard**

| Seat | Position | Conf. | Peer rank |
|---|---|---|---|
| The Outsider | ... | 90% | 1.4 |
| The Executor | ... | 85% | 2.0 |
| ... | | | |

{Deep only: "Position shifts: The Expansionist UPDATED (65% → 40%) after critique of ..."}
{Deep only: "Red team: SERIOUS, added tripwire #2" or "Survived red team: ..."}
```

Style rules: scannable, bullet points, no hedging paragraphs, bold the crux. For content reviews, add a **Before → After** block under the Recommendation.

---

## Transcript (saved file)

Path: `council-transcripts/YYYY-MM-DD-{slug}.md`

```markdown
# Council Transcript: {topic}
- Date: {YYYY-MM-DD}
- Mode: {Quick | Standard | Deep} · Tier: {A | B | C}
- Seats: {list} · Models: {if known}

## Framed Brief
{brief}

## Round 1: Advisor Responses
### {Seat}
{response}
...

## Round 2: Peer Review
Anonymization: A = {Seat}, B = {Seat}, ...
### Reviewer: {Seat}
{review}
...
### Peer Scoreboard
{table}

## Round 3: Rebuttals (Deep)
...

## Red Team (Deep)
...

## Final Verdict
{verdict}
```
