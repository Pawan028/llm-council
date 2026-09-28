# Changelog

## 2.0.0 (2026-09-28)

A complete rebuild of the original LLM Council skill.

### Added
- **Three modes:** Quick (3 seats), Standard (5 seats + peer ranking), Deep / War Room (7 seats + rebuttal + red team).
- **Three execution tiers:** parallel sub-agents, true multi-model (`scripts/council.py`), and a sealed-rounds protocol for single-context LLMs.
- **Structured advisor output:** Position · Confidence · Argument · Weakest assumption · Would change my mind.
- **Karpathy-style full ranking** with order rotation per reviewer and an aggregated peer scoreboard.
- **Specialist seats:** Domain Expert, Stakeholder, Historian, Pre-Mortem.
- **Rebuttal round** (HOLD / UPDATE) and a **red team** that attacks the draft verdict.
- **Verdict upgrades:** bottom line first, calibrated confidence, one-way/two-way door, tripwires ("What Would Change This Verdict").
- Anti-sycophancy, anti-fabrication, and professional-referral rules.
- Adapters for ChatGPT, Gemini, Codex, Gemini CLI, Copilot, Cursor, Windsurf, Aider, and any chatbot.
- `council.py`: zero-dependency multi-model runner for any OpenAI-compatible API (OpenRouter, OpenAI, Ollama…), with `--mock` dry runs.

### Fixed
- Removed the contradiction between "no HTML report" and "the visual report matters". Markdown in chat is the default, and file or HTML reports are opt-in.
- Transcripts now go to `council-transcripts/` instead of an arbitrary `active/` folder.

## 1.0.0
- Original skill: 5 advisors → anonymous peer review → chairman synthesis.
