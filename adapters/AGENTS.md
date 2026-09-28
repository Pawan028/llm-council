# LLM Council (agent instructions)

> Drop this file (or append its contents) into your project's `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.windsurfrules`, or `CONVENTIONS.md` (Aider). Works with OpenAI Codex CLI, Gemini CLI, GitHub Copilot, Windsurf, Aider, OpenCode, Amp, Cline, Roo, and any agent that reads project instructions.
> If the full skill folder is available, read `llm-council/SKILL.md` and `llm-council/references/*` instead: they're the complete version.

## When to use

When the user says "council this", "run the council", "war room this", "pressure-test this", "stress-test this", "debate this", "quick council", or "deep council", or brings a real decision with stakes and tradeoffs ("should I X or Y", "which option", "I'm torn between"), run the LLM Council. Don't use it for factual lookups, creation or processing tasks, or trivial choices.

## How

1. **Gather context (≤30s):** skim README / AGENTS.md / docs / files the user referenced for the 2-4 facts that make advice specific.
2. **Frame** a neutral brief: options, context and numbers, stakes, unknowns-as-assumptions. If it's too vague, ask one clarifying question.
3. **Round 1: independent advisors.** If you can spawn sub-agents or tasks, spawn one per seat **in parallel**, each with a fresh context. If you can't, write each advisor *sealed* (never revise an earlier one after writing a later one).
   Seats: **Contrarian** (hunt the fatal flaw) · **First Principles** (what are we really solving?) · **Expansionist** (hidden upside) · **Outsider** (zero context, flags confusion) · **Executor** (what happens Monday morning?).
   Each returns: `Position · Confidence % · Argument · Weakest assumption · Would change my mind` (150-300 words).
4. **Round 2: anonymous peer ranking.** Shuffle into Response A-E, rotate the order per reviewer, and have each seat review all of them on specificity, soundness, actionability, and insight. Each ends with `FINAL RANKING: 1. Response ? …` plus the biggest blind spot and what everyone missed. Average the ranks into a scoreboard.
5. **Chairman:** de-anonymize and write: Bottom line · Confidence (High/Med/Low) · One-way or two-way door · Agrees · Clashes (with the crux) · Blind spots · Recommendation (may overrule the majority) · What would change this verdict (tripwires) · The one thing to do first · Scoreboard.
6. **Deep mode** adds a Domain Expert and a Pre-Mortem seat, a rebuttal round (HOLD/UPDATE), and a red team that attacks the draft verdict before it's finalized.
7. **Multi-model:** if a shell and an API key are available and the user wants model diversity, run `python llm-council/scripts/council.py "<brief>" --models <m1> <m2> <m3>`.

## Rules

No fabricated facts (label assumptions). No sycophancy. No "it depends" without a direction. Name the crux of each disagreement. Give one first step, not ten. For medical, legal, tax, or safety topics, name the professional to consult.
