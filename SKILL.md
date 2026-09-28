---
name: llm-council
description: "Convene a council of independent AI advisors to pressure-test a real decision. Each advisor thinks through a different lens, they anonymously rank and critique each other, and a chairman delivers a clear verdict with confidence, dissent, tripwires, and one first step. Based on Karpathy's LLM Council. Works with sub-agents, with multiple different models, or inside a single chat. MANDATORY TRIGGERS: 'council this', 'run the council', 'war room this', 'pressure-test this', 'stress-test this', 'debate this', 'quick council', 'deep council'. STRONG TRIGGERS (only with a real decision or tradeoff): 'should I X or Y', 'which option', 'what would you do', 'is this the right move', 'validate this', 'get multiple perspectives', 'I can't decide', 'I'm torn between'. Do NOT trigger on factual lookups, simple yes/no questions, creation tasks ('write me a tweet'), processing tasks ('summarize this'), or casual 'should I' questions with no real stakes."
---

# LLM Council

Ask one AI a question and you get one answer. It might be great. It might be mid. You can't tell, because you only saw one perspective.

The council fixes that. Your question goes to several independent advisors who each think from a different angle. They answer **without seeing each other**. Then they **rank and critique each other anonymously**. Then a **chairman** turns it all into a verdict: where they agree, where they clash, what they missed, what to do, and what would prove the verdict wrong.

This follows Andrej Karpathy's LLM Council (answer → anonymous peer ranking → chairman synthesis) and adds three things: thinking lenses on top of model diversity, a rebuttal round, and a red team that attacks the chairman's draft.

---

## 0. Should this be a council at all?

Run the council when **being wrong is expensive and the answer isn't obvious**.

| Council it | Don't council it |
|---|---|
| "$97 workshop or $497 course?" | "What's the capital of France?" (just answer) |
| "Which of these 3 positioning angles is strongest?" | "Write me a tweet" (creation, not judgment) |
| "Pivot from agency to SaaS. Am I crazy?" | "Summarize this article" (processing) |
| "Here's my landing page. What's weak?" | "Should I use markdown here?" (no stakes) |
| "Postgres or DynamoDB for this workload?" | "How do I reverse a list in Python?" (one right answer) |

If the request doesn't qualify, answer it directly and don't mention the council. If the user explicitly asks for the council anyway, run **Quick** mode.

---

## 1. Pick the depth

| Mode | When | Seats | Rounds | Calls* |
|---|---|---|---|---|
| **Quick** | "quick council", low-medium stakes, fast gut-check | 3 (Contrarian, First Principles, Executor) | Answers → Chairman | 4 |
| **Standard** *(default)* | Most real decisions | 5 core seats | Answers → Peer ranking → Chairman | 11 |
| **Deep / War Room** | "deep council", "war room", irreversible or high-stakes calls | 5 core + 2 specialist seats | Answers → Peer ranking → Rebuttal → Chairman draft → Red team → Final verdict | 23 |

\*Calls = sub-agent or model calls. Tell the user which mode you're running in one short line, then run it without asking for permission.

---

## 2. Pick the execution tier (works on any LLM)

Use the strongest tier your environment supports:

- **Tier A: Parallel sub-agents** (Claude Code, Claude Agent SDK, any agent host with a sub-agent / Task tool). Every advisor is a separate sub-agent with a fresh context, so independence is real. **Spawn all advisors of a round in ONE message** so they run in parallel. If the host lets you pick a model per sub-agent, spread the seats across different models for real model diversity.
- **Tier B: True multi-model council.** If the user wants different vendors (GPT, Claude, Gemini, Llama, local models…) or you have a shell and an API key, run `scripts/council.py` from this skill's folder. It hits any OpenAI-compatible endpoint (OpenRouter, OpenAI, Groq, Together, Ollama, LM Studio, vLLM). See the README for setup.
- **Tier C: Sealed-rounds protocol** (ChatGPT, Gemini, Claude.ai chat, Copilot, any single-context LLM). Simulate the council in one context with the discipline rules in §7. It's weaker than A or B because one mind plays every seat, but it's still far better than a single answer.

Never skip the council because sub-agents aren't available. Drop down a tier.

---

## 3. The seats

Full lens descriptions (paste them verbatim into prompts) are in `references/advisors.md`. Summary:

**Core five:** these are thinking styles, not job titles.
1. **The Contrarian** assumes there's a fatal flaw and hunts for it. Not a pessimist: they're the friend who saves you from the bad deal.
2. **The First Principles Thinker** asks what we're actually solving. Strips assumptions, rebuilds from the ground up, and will say "you're asking the wrong question."
3. **The Expansionist** hunts for hidden upside, adjacent opportunities, and what happens if this works better than expected.
4. **The Outsider** has zero context about you or your field and catches the curse of knowledge: jargon, unclear value, things only insiders find obvious.
5. **The Executor** asks "what do you do Monday morning?" Cares about feasibility, sequencing, cost, and the fastest path to proof.

**Built-in tensions:** Contrarian vs Expansionist (downside vs upside). First Principles vs Executor (rethink vs just do it). The Outsider stays in the middle and keeps everyone honest.

**Specialist seats (Deep mode only, choose 2 that fit the question):**
- **The Domain Expert** is a named senior practitioner matched to the question ("a B2B SaaS pricing consultant", "a staff SRE who's run Postgres at scale", "an immigration attorney"). Brings field-specific knowledge and base rates.
- **The Stakeholder** is the person most affected who isn't in the room: the customer, the end user, the employee, the spouse, the investor.
- **The Historian** does reference-class forecasting: "What usually happens to people who make this move? What's the base rate?"
- **The Pre-Mortem** says "It's 12 months later and this failed. Here's the most likely story of why."

---

## 4. The protocol

### Step 1: Gather context (≤30 seconds, silent)

The question is usually the tip of the iceberg. Before framing, quickly look for the 2-4 files that would make the advice specific instead of generic:
- `CLAUDE.md` / `AGENTS.md` / `README.md` in the project root
- any `memory/` or `docs/` folder (audience, business stage, constraints, past decisions)
- files the user referenced or attached
- earlier council transcripts in `council-transcripts/` (don't re-council settled ground; build on it)
- anything obviously related to the question (pricing → revenue data, architecture → the relevant code or config)

Use Glob/Grep/Read or whatever file tools you have. If there are no files (e.g., a plain chat), skip this step.

### Step 2: Frame the question

Write one **neutral** brief that every seat receives:
1. **The decision:** the options on the table, stated plainly.
2. **Context:** facts from the user's message and from the workspace, including numbers, stage, audience, constraints, and past results.
3. **Stakes:** why this matters, what's at risk, the time horizon.
4. **Unknowns:** facts that are missing and that advisors must treat as assumptions.

Don't add your opinion and don't steer. If the question is too vague to frame ("council this: my business"), ask **one** clarifying question, then proceed. Keep the framed brief for the transcript.

### Step 3: Round 1, independent answers (parallel)

Send each seat the **Advisor prompt** from `references/prompts.md`. Every advisor returns the same structure:

> **Position** (one sentence) · **Confidence** (0-100%) · **Argument** · **Weakest assumption** · **Would change my mind**

That structure is what lets the chairman compare positions, find cruxes, and write tripwires. 150-300 words per advisor. Advisors must not see each other in this round.

### Step 4: Round 2, anonymous peer ranking (parallel; Standard and Deep)

This is Karpathy's core insight, and it's what makes a council more than "ask five times."

1. **Anonymize.** Shuffle the advisors randomly and label them Response A, B, C… Keep the mapping private.
2. **Rotate order per reviewer.** Every reviewer gets the same letters in a different order (reviewer 1 sees A-B-C-D-E, reviewer 2 sees B-C-D-E-A, and so on). That cancels positional bias.
3. **One reviewer per seat.** Each reviewer judges on merit but uses their own lens to spot what others would miss. Use the **Reviewer prompt**.
4. **Each reviewer ranks ALL responses** (best → worst) using the rubric *specificity, soundness, actionability, insight*, names the biggest blind spot, and names what **every** response missed.
5. **Aggregate.** Parse each `FINAL RANKING`, average the rank positions per response, and sort. That is the **peer scoreboard**. Also note which blind spots came up from more than one reviewer.

### Step 5: Round 3, rebuttal (Deep only, parallel)

Give each original advisor the critiques aimed at their response plus the top-ranked rival response (still anonymized). Use the **Rebuttal prompt**. Each one either **holds** (and says why) or **updates** (and says what changed). Position shifts are a strong signal: an advisor who changes their mind under peer pressure has found something real. A chorus that holds firm under attack is also a signal.

### Step 6: Chairman synthesis

The chairman gets everything **de-anonymized**: the brief, every advisor response, every review, the peer scoreboard, and any rebuttals. Use the **Chairman prompt**. The chairman:
- leads with the bottom line, not the process
- **can overrule the majority** when the dissenter's reasoning is stronger, and says why
- never answers "it depends" without then saying *what* it depends on and *which way to go now*
- calibrates confidence honestly (strong agreement plus good evidence → High; a live crux or a missing critical fact → Medium or Low)
- labels the decision a **one-way door** (hard to reverse, so slow down) or a **two-way door** (cheap to reverse, so bias to action)
- writes **tripwires**: the specific signals that would mean the verdict is wrong

In Tier A, run the chairman as a sub-agent. You (the orchestrator) may also act as chairman if context allows.

### Step 7: Red team (Deep only)

One more agent gets the brief and the chairman's draft verdict (not the whole transcript) and attacks it with the **Red-team prompt**: the strongest case that the recommendation is wrong, plus any fact it relies on that is shaky. The chairman then revises: it either fixes the verdict or adds a "Survived red team because…" line.

### Step 8: Deliver the verdict

Present the verdict **in chat as markdown** using the template in `references/output-format.md`. Bottom line first, scannable, bullet points, with the peer scoreboard at the end. Don't dump the full transcript unless asked. Only produce an HTML or file report if the user asks for one.

### Step 9: Save the transcript (when it's worth it)

Save when the user asks, or automatically in Deep mode when you have file access. Write to `council-transcripts/YYYY-MM-DD-<slug>.md` with: framed brief, all advisor responses, the anonymization mapping, reviews, scoreboard, rebuttals, and the final verdict.

---

## 5. Non-negotiable rules

1. **Independence first.** Round-1 advisors never see each other. In Tier A, spawn them in parallel, never in sequence.
2. **Always anonymize peer review.** Reviewers who know who said what defer to styles instead of judging arguments.
3. **No fabrication.** Advisors and the chairman must not invent statistics, prices, studies, or quotes. Unknowns are stated as assumptions (e.g., "Assuming ~2% conversion…"). If a verdict hinges on a checkable fact, the first step should often be to check it.
4. **No sycophancy.** The user's enthusiasm is not evidence. If the idea is bad, the council says so plainly and kindly. Users who just want validation will hear things they don't want to hear. That's the point.
5. **No mush.** "Consider both sides" is not a recommendation. The chairman commits.
6. **Disagreement is data.** Don't smooth over clashes. Name the crux: the single factual or values question the disagreement turns on.
7. **One first step.** Not a list of ten. One concrete action, doable this week, ideally one that cheaply de-risks the biggest unknown.
8. **Stay in scope.** For medical, legal, tax, or safety-critical decisions, the council can structure the thinking, but the verdict must name the licensed professional to consult and treat that consultation as a real step.
9. **Respect the user's time.** Quick mode for quick questions. Don't run Deep on a $50 decision.

---

## 6. Handling follow-ups

- **"Dig into X"**: re-convene only the relevant seats (e.g., Contrarian + Domain Expert) on the narrower question, with the previous verdict as context.
- **"I disagree because Y"**: treat Y as new context. Re-run the Chairman (and the Contrarian, if Y is a factual claim) and say explicitly whether Y changes the verdict. Don't cave just because the user pushed back.
- **"Council these 3 options"**: frame it as a multi-option decision. Advisors pick a winner and rank the rest, and the chairman gives a clear winner and runner-up.
- **Content review** ("here's my landing page, what's weak?"): advisors give specific line-level problems, and the chairman gives the top 3 fixes with **before → after** rewrites.

---

## 7. Tier C: the sealed-rounds protocol (single-context LLMs)

When you must play every seat yourself, compensate with discipline:

1. **Seal each advisor.** Write the advisors one at a time. While writing one, reason only from that lens. Never go back and edit an earlier advisor after writing a later one.
2. **Force divergence.** Before writing the advisors, silently list the 2-3 most likely "default" answers. At least one advisor must argue against the default you find most tempting.
3. **Commit before reviewing.** Write all Round-1 positions and confidences in full before any review.
4. **Review adversarially.** For each response, write its strongest point and its single worst flaw, then rank. Give the letters a scrambled order that isn't the order you wrote them in.
5. **Chair last, and cold.** Re-read only the positions, cruxes, and reviews, then write the verdict. Assume the user will act on it tomorrow.
6. **Be honest about the mode.** Add one line to the verdict: *"Council run in single-context mode. For stronger independence, run it with sub-agents or multiple models."*

The single-prompt version of this protocol, ready to paste into any chatbot, is in `adapters/universal-prompt.md`.

---

## 8. Example (abridged)

**User:** "Council this: I'm thinking of building a $297 course on Claude Code for beginners. My audience is mostly non-technical solopreneurs."

- **Contrarian** (Position: don't build it yet · 80%): the market is flooded, $297 competes with free YouTube, non-technical buyers mean a heavy support load and refunds.
- **First Principles** (Position: wrong question · 70%): is the goal revenue, authority, or a customer base for high-ticket offers? A course is the slowest path to revenue.
- **Expansionist** (Position: go bigger · 65%): beginner AI for solopreneurs is underserved, and this could be a $997 program with community.
- **Outsider** (Position: I don't get it · 90%): "Claude Code" means nothing to me. Sell the outcome, not the tool.
- **Executor** (Position: validate first · 85%): run a $97 live workshop for 50 people before spending 6 weeks building.

**Peer scoreboard:** Outsider 1.4 · Executor 2.0 · Contrarian 2.8 · First Principles 3.6 · Expansionist 4.2
**Blind spot caught in review:** everyone except the Outsider assumed the buyer knows what Claude Code is.

**Verdict:** Bottom line: don't build the course yet. Validate the outcome, not the tool. Confidence: High (4/5 converged, top-ranked insight is uncontested). Two-way door.
**Tripwire:** if fewer than 20 of ~1,000 people who see the offer buy a $97 workshop, the course won't sell either.
**First step:** this week, announce a $97 live workshop called *"Automate your first business task with AI"* with no tool name in the title, and cap it at 50 seats.
