#!/usr/bin/env python3
"""
LLM Council: a true multi-model council runner.

Each seat (thinking lens) is answered by a different model, the models rank each
other anonymously, and a chairman model writes the verdict. Works with any
OpenAI-compatible Chat Completions endpoint: OpenRouter, OpenAI, Groq, Together,
DeepSeek, Ollama, LM Studio, vLLM, and others.

Zero dependencies: Python 3.8+ standard library only.

Examples
--------
  # OpenRouter (one key, many vendors)
  export COUNCIL_API_KEY=sk-or-...
  python council.py "Should I launch a $97 workshop or a $497 course?" \
      --models openai/gpt-5 anthropic/claude-sonnet-5 google/gemini-2.5-pro

  # Local models via Ollama (no key needed)
  python council.py "Postgres or DynamoDB for this workload?" \
      --base-url http://localhost:11434/v1 --models llama3.1 qwen2.5 mistral

  # Try the pipeline offline, no API calls
  python council.py "Test question" --mock
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------- #
# Seats (keep in sync with references/advisors.md)
# --------------------------------------------------------------------------- #

SEATS = {
    "contrarian": (
        "The Contrarian",
        "You actively look for what's wrong, what's missing, and what will fail. "
        "Assume the idea has a fatal flaw and hunt for it: hidden costs, second-order "
        "effects, misaligned incentives, competitor responses, execution risk. You are "
        "not a pessimist; you're the friend who saves someone from a bad deal. If you "
        "truly can't find a serious flaw, say so, because that is a strong signal too.",
    ),
    "first_principles": (
        "The First Principles Thinker",
        "Ignore how the question is framed and ask what is actually being solved. Strip "
        "away inherited assumptions and conventions and rebuild the problem from "
        "fundamentals: goals, constraints, economics, human behavior. Often your most "
        "valuable output is 'you're asking the wrong question', followed by the right "
        "question and its answer.",
    ),
    "expansionist": (
        "The Expansionist",
        "Look for the upside everyone else is missing. What could be bigger? What "
        "adjacent opportunity is hiding? What is undervalued? What happens if this works "
        "far better than expected? Risk is someone else's job. Make sure the user "
        "doesn't think too small.",
    ),
    "outsider": (
        "The Outsider",
        "You have zero context about this person, their field, jargon, or history. "
        "Respond only to what's in front of you, as a smart stranger would. Flag anything "
        "confusing, insider-only, or whose value isn't obvious in five seconds. You catch "
        "the curse of knowledge.",
    ),
    "executor": (
        "The Executor",
        "You care only about whether this can get done and the fastest path to doing it. "
        "Ask 'what happens Monday morning?' Think about sequencing, time, money, skills, "
        "dependencies, and the cheapest experiment that proves or kills the idea. If there's "
        "no clear first step, say so.",
    ),
    "domain_expert": (
        "The Domain Expert",
        "You are the single most relevant senior practitioner (15+ years) for this exact "
        "question. Start by naming your specialty in one line. Bring field-specific "
        "benchmarks (as labeled approximate ranges), common failure modes, regulations, "
        "and what the best people in the field actually do. Never invent precise statistics.",
    ),
    "historian": (
        "The Historian",
        "You do reference-class forecasting. First ask what usually happens to people or "
        "companies who make this kind of move: the rough base rate, typical timeline, "
        "typical overrun. Cite analogues only when you're confident they're accurate. "
        "Then adjust from the base rate using this case's specifics, and say which way "
        "and why.",
    ),
}

MODES = {
    "quick": ["contrarian", "first_principles", "executor"],
    "standard": ["contrarian", "first_principles", "expansionist", "outsider", "executor"],
    "deep": ["contrarian", "first_principles", "expansionist", "outsider", "executor",
             "domain_expert", "historian"],
}

# --------------------------------------------------------------------------- #
# Prompts (keep in sync with references/prompts.md)
# --------------------------------------------------------------------------- #

ADVISOR_PROMPT = """You are {seat} on a decision council of {n} independent advisors.

YOUR LENS:
{lens}

You answer independently. You cannot see the other advisors. Do NOT try to be
balanced. The council gets balance from the other seats. Lean fully into your lens.

THE QUESTION BROUGHT TO THE COUNCIL:
---
{brief}
---

Rules:
- Be specific to THIS situation. Generic advice counts as a failure.
- Use the numbers and details given. Do the math where it matters.
- Never invent facts, statistics, prices, studies, or quotes. State unknowns as explicit assumptions.
- No preamble. Don't restate the question.

Respond in EXACTLY this format, 150-300 words total:

**Position:** <one sentence>
**Confidence:** <0-100>%
**Argument:** <core reasoning from your lens>
**Weakest assumption:** <what, if wrong, breaks your position>
**Would change my mind:** <specific evidence that would flip you>"""

REVIEWER_PROMPT = """You are {seat}, now acting as a peer reviewer on a decision council.
Judge every response on MERIT, not on whether it matches your lens. But use your
lens to notice what others would miss.

THE QUESTION:
---
{brief}
---

Here are {n} anonymized advisor responses:

{responses}

Rubric: Specificity, Soundness (errors, fabrications, leaps?), Actionability, Insight.

Write, in under 250 words:
1. **Strongest:** which response and the specific reason.
2. **Biggest blind spot:** which response and exactly what it misses or gets wrong.
3. **Everyone missed:** what ALL responses failed to consider.

Then end with your full ranking, best to worst, in EXACTLY this format and nothing after it:

FINAL RANKING:
1. Response ?
2. Response ?
..."""

REBUTTAL_PROMPT = """You are {seat}. Earlier you gave this response to the council:
---
{own}
---

Anonymous peer reviewers said the following in their reviews (look for mentions of Response {letter}, which is yours):
---
{critiques}
---

The response the peers ranked highest overall was Response {top_letter}:
---
{top}
---

Decide honestly: HOLD or UPDATE your position. Changing your mind when you meet
a better argument is a strength. Caving to criticism that's weak is a failure.

Respond in under 150 words:
**Verdict:** HOLD or UPDATE
**Revised position:** <one sentence>
**Revised confidence:** <0-100>%
**Why:** <the specific argument that did or didn't move you>"""

CHAIRMAN_PROMPT = """You are the Chairman of an LLM Council. Turn the work of the advisors and
their peer reviews into a final verdict the user can act on.

THE QUESTION:
---
{brief}
---

ADVISOR RESPONSES (de-anonymized; model shown in brackets):
{advisors}

PEER REVIEWS (letter mapping: {mapping}):
{reviews}

PEER SCOREBOARD (average rank, lower = better):
{scoreboard}

REBUTTALS:
{rebuttals}

Rules:
- Lead with the bottom line.
- You MAY overrule the majority if the dissent's reasoning is stronger. Say so if you do.
- Never stop at "it depends". Name the crux AND say which way to go given what's known now.
- Calibrate: High = strong convergence plus sound evidence; Medium = live crux or key unknown; Low = hinges on facts nobody has.
- Classify: ONE-WAY DOOR (hard to reverse) or TWO-WAY DOOR (cheap to reverse).
- Don't invent facts. Label your own additions as the chairman's.

Produce EXACTLY this structure:

**Bottom line:** <one sentence>
**Confidence:** <High | Medium | Low>, <reason> · **Decision type:** <One-way door | Two-way door>

### Where the Council Agrees
### Where the Council Clashes
(name the CRUX of each clash)
### Blind Spots the Council Caught
### The Recommendation
### What Would Change This Verdict
(2-3 specific, observable tripwires)
### The One Thing to Do First
(ONE concrete action, doable this week)"""

RED_TEAM_PROMPT = """You are the Red Team. A council produced the draft verdict below. Your only job is to break it.

THE QUESTION:
---
{brief}
---

DRAFT VERDICT:
---
{draft}
---

In under 200 words:
1. **Strongest case against:** the best argument that the recommendation is wrong.
2. **Shakiest load-bearing claim:** the least-verified fact or assumption the verdict depends on.
3. **Better alternative (if any):** an option dismissed or never considered.
4. **Severity:** FATAL | SERIOUS | MINOR"""

REVISE_PROMPT = """You are the Chairman. Here is your draft verdict and a red-team attack on it.

DRAFT:
---
{draft}
---

RED TEAM:
---
{red}
---

Produce the FINAL verdict in the same structure. If severity is FATAL, rewrite the
recommendation. If SERIOUS, add the caveat or tripwire. If MINOR, keep the verdict
and add a final line: "Survived red team: <why>." Output only the final verdict."""

# --------------------------------------------------------------------------- #
# Model client
# --------------------------------------------------------------------------- #


class Client:
    def __init__(self, base_url: str, api_key: str, temperature: float, timeout: int,
                 mock: bool = False):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.key = api_key
        self.temperature = temperature
        self.timeout = timeout
        self.mock = mock

    def chat(self, model: str, prompt: str, retries: int = 2) -> str:
        if self.mock:
            return _mock_reply(model, prompt)
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json",
                   "HTTP-Referer": "https://github.com/Pawan028/llm-council",
                   "X-Title": "LLM Council"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                if isinstance(content, list):  # some providers return content parts
                    content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
                return (content or "").strip()
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:300]
                last_err = RuntimeError(f"HTTP {e.code} from {model}: {detail}")
                if e.code in (400, 401, 403, 404):
                    break  # won't fix itself on retry
            except Exception as e:  # network, timeout, bad JSON
                last_err = e
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"{model} failed: {last_err}")


def _mock_reply(model: str, prompt: str) -> str:
    rng = random.Random(hash((model, prompt[:200])))
    if prompt.startswith("You are the Red Team"):
        return "1. **Strongest case against:** mock.\n4. **Severity:** MINOR"
    if "**Verdict:** HOLD or UPDATE" in prompt:
        verdict = rng.choice(["HOLD", "UPDATE"])
        return f"**Verdict:** {verdict}\n**Revised position:** mock\n**Revised confidence:** 70%\n**Why:** mock"
    if "peer reviewer" in prompt[:120]:
        letters = sorted(set(re.findall(r"\*\*Response ([A-Z]):\*\*", prompt)))
        rng.shuffle(letters)
        ranking = "\n".join(f"{i}. Response {l}" for i, l in enumerate(letters, 1))
        return (f"1. **Strongest:** Response {letters[0]} is concrete.\n"
                f"2. **Biggest blind spot:** Response {letters[-1]} ignores cost.\n"
                f"3. **Everyone missed:** timing.\n\nFINAL RANKING:\n{ranking}")
    if prompt.startswith("You are the Chairman"):
        return ("**Bottom line:** (mock) Validate before building.\n"
                "**Confidence:** Medium, mock run · **Decision type:** Two-way door\n\n"
                "### Where the Council Agrees\n- mock\n### Where the Council Clashes\n- mock\n"
                "### Blind Spots the Council Caught\n- mock\n### The Recommendation\nmock\n"
                "### What Would Change This Verdict\n- mock\n### The One Thing to Do First\nmock")
    conf = rng.randint(55, 90)
    return (f"**Position:** (mock answer from {model})\n**Confidence:** {conf}%\n"
            "**Argument:** mock\n**Weakest assumption:** mock\n**Would change my mind:** mock")


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def log(msg: str, quiet: bool) -> None:
    if not quiet:
        print(msg, file=sys.stderr, flush=True)


def parse_ranking(text: str, valid: set[str]) -> list[str]:
    """Extract ordered letters after 'FINAL RANKING:'. Falls back to whole text."""
    idx = text.upper().rfind("FINAL RANKING")
    section = text[idx:] if idx != -1 else text
    seen: list[str] = []
    for letter in re.findall(r"Response\s+([A-Z])\b", section):
        if letter in valid and letter not in seen:
            seen.append(letter)
    return seen


def run_parallel(fn, items, workers: int):
    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        return list(ex.map(fn, items))


def run_council(question: str, models: list[str], chairman: str, mode: str,
                client: Client, quiet: bool = False) -> dict:
    seat_keys = MODES[mode]
    n = len(seat_keys)
    # Spread seats across models round-robin for model + lens diversity.
    seats = [{"key": k, "name": SEATS[k][0], "lens": SEATS[k][1],
              "model": models[i % len(models)]} for i, k in enumerate(seat_keys)]

    def safe_chat(model: str, prompt: str) -> str:
        try:
            return client.chat(model, prompt)
        except Exception as e:
            return f"[ERROR: {e}]"

    # ---- Round 1: independent answers
    log(f"Round 1: {n} advisors answering in parallel...", quiet)

    def advise(s):
        return safe_chat(s["model"], ADVISOR_PROMPT.format(
            seat=s["name"], n=n, lens=s["lens"], brief=question))

    for s, ans in zip(seats, run_parallel(advise, seats, n)):
        s["response"] = ans

    live = [s for s in seats if not s["response"].startswith("[ERROR")]
    if not live:
        raise SystemExit("All advisors failed. Check --base-url, API key and model names.\n"
                         + "\n".join(s["response"] for s in seats))

    result = {"question": question, "mode": mode, "chairman": chairman, "seats": seats,
              "reviews": [], "scoreboard": [], "mapping": {}, "rebuttals": [],
              "red_team": None}

    # ---- Round 2: anonymous peer ranking (standard / deep)
    if mode != "quick" and len(live) >= 2:
        log("Round 2: anonymous peer ranking...", quiet)
        shuffled = live[:]
        random.shuffle(shuffled)
        letters = [chr(ord("A") + i) for i in range(len(shuffled))]
        by_letter = dict(zip(letters, shuffled))
        result["mapping"] = {l: s["name"] for l, s in by_letter.items()}

        def review(args):
            i, s = args
            order = letters[i % len(letters):] + letters[:i % len(letters)]  # rotate order
            block = "\n\n".join(f"**Response {l}:**\n{by_letter[l]['response']}" for l in order)
            text = safe_chat(s["model"], REVIEWER_PROMPT.format(
                seat=s["name"], brief=question, n=len(letters), responses=block))
            return {"reviewer": s["name"], "model": s["model"], "text": text,
                    "ranking": parse_ranking(text, set(letters))}

        result["reviews"] = run_parallel(review, list(enumerate(live)), len(live))

        totals = {l: [] for l in letters}
        for r in result["reviews"]:
            for pos, l in enumerate(r["ranking"], 1):
                totals[l].append(pos)
        board = []
        for l, positions in totals.items():
            avg = sum(positions) / len(positions) if positions else float("nan")
            board.append({"letter": l, "seat": by_letter[l]["name"],
                          "model": by_letter[l]["model"], "avg_rank": avg,
                          "votes": len(positions)})
        board.sort(key=lambda b: (b["votes"] == 0, b["avg_rank"]))
        result["scoreboard"] = board
        for l, s in by_letter.items():
            s["letter"] = l

        # ---- Round 3: rebuttal (deep)
        if mode == "deep" and board and board[0]["votes"]:
            log("Round 3: rebuttals...", quiet)
            top = by_letter[board[0]["letter"]]
            all_reviews = "\n\n---\n\n".join(r["text"] for r in result["reviews"])

            def rebut(s):
                text = safe_chat(s["model"], REBUTTAL_PROMPT.format(
                    seat=s["name"], own=s["response"], letter=s["letter"],
                    critiques=all_reviews, top_letter=top["letter"], top=top["response"]))
                return {"seat": s["name"], "text": text}

            result["rebuttals"] = run_parallel(rebut, live, len(live))

    # ---- Chairman
    log("Chairman: synthesizing verdict...", quiet)
    advisors_txt = "\n\n".join(f"**{s['name']}** [{s['model']}]:\n{s['response']}" for s in seats)
    reviews_txt = "\n\n".join(f"**Reviewer: {r['reviewer']}**\n{r['text']}"
                              for r in result["reviews"]) or "none (quick mode)"
    board_txt = "\n".join(f"- {b['seat']}: {b['avg_rank']:.2f}" for b in result["scoreboard"]
                          if b["votes"]) or "none"
    rebuttals_txt = "\n\n".join(f"**{r['seat']}:**\n{r['text']}" for r in result["rebuttals"]) or "none"
    mapping_txt = ", ".join(f"{l} = {name}" for l, name in result["mapping"].items()) or "n/a"

    verdict = safe_chat(chairman, CHAIRMAN_PROMPT.format(
        brief=question, advisors=advisors_txt, mapping=mapping_txt, reviews=reviews_txt,
        scoreboard=board_txt, rebuttals=rebuttals_txt))

    # ---- Red team (deep)
    if mode == "deep" and not verdict.startswith("[ERROR"):
        log("Red team: attacking the draft verdict...", quiet)
        red_model = next((m for m in models if m != chairman), chairman)
        red = safe_chat(red_model, RED_TEAM_PROMPT.format(brief=question, draft=verdict))
        result["red_team"] = {"model": red_model, "text": red}
        if not red.startswith("[ERROR"):
            revised = safe_chat(chairman, REVISE_PROMPT.format(draft=verdict, red=red))
            if not revised.startswith("[ERROR"):
                verdict = revised

    result["verdict"] = verdict
    return result


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _position(resp: str) -> str:
    m = re.search(r"\*\*Position:\*\*\s*(.+)", resp)
    return (m.group(1).strip() if m else resp.strip().splitlines()[0] if resp.strip() else "")[:90]


def _confidence(resp: str) -> str:
    m = re.search(r"\*\*Confidence:\*\*\s*(\d{1,3})\s*%", resp)
    return f"{m.group(1)}%" if m else "?"


def render_verdict(r: dict, topic: str) -> str:
    rank = {b["seat"]: b["avg_rank"] for b in r["scoreboard"] if b["votes"]}
    rows = sorted(r["seats"], key=lambda s: rank.get(s["name"], 99))
    lines = [f"## Council Verdict: {topic}",
             f"*{r['mode'].title()} council · {len(r['seats'])} seats · multi-model · "
             f"chairman: {r['chairman']}*", "", r["verdict"], "", "---",
             "**Council scoreboard**", "",
             "| Seat | Model | Position | Conf. | Peer rank |", "|---|---|---|---|---|"]
    for s in rows:
        pr = f"{rank[s['name']]:.2f}" if s["name"] in rank else "-"
        pos = _position(s["response"]).replace("|", "/")
        lines.append(f"| {s['name']} | `{s['model']}` | {pos} | {_confidence(s['response'])} | {pr} |")
    if r["rebuttals"]:
        shifts = [x["seat"] for x in r["rebuttals"] if re.search(r"Verdict:\*\*\s*UPDATE", x["text"])]
        lines += ["", f"**Position shifts after rebuttal:** {', '.join(shifts) or 'none, all held'}"]
    return "\n".join(lines)


def render_transcript(r: dict, topic: str) -> str:
    out = [f"# Council Transcript: {topic}",
           f"- Date: {dt.date.today().isoformat()}",
           f"- Mode: {r['mode']} · Tier: B (multi-model) · Chairman: {r['chairman']}", "",
           "## Framed Brief", r["question"], "", "## Round 1: Advisor Responses"]
    for s in r["seats"]:
        out += [f"### {s['name']} [{s['model']}]", s["response"], ""]
    if r["reviews"]:
        out += ["## Round 2: Peer Review",
                "Anonymization: " + ", ".join(f"{l} = {n}" for l, n in r["mapping"].items()), ""]
        for rv in r["reviews"]:
            out += [f"### Reviewer: {rv['reviewer']} [{rv['model']}]", rv["text"], ""]
        out += ["### Peer Scoreboard"] + [
            f"- {b['seat']}: {b['avg_rank']:.2f} ({b['votes']} votes)" for b in r["scoreboard"]] + [""]
    if r["rebuttals"]:
        out += ["## Round 3: Rebuttals"] + sum(([f"### {x['seat']}", x["text"], ""]
                                               for x in r["rebuttals"]), [])
    if r["red_team"]:
        out += [f"## Red Team [{r['red_team']['model']}]", r["red_team"]["text"], ""]
    out += ["## Final Verdict", render_verdict(r, topic)]
    return "\n".join(out)


def slugify(text: str, n: int = 50) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:n].strip("-") or "council"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # model output is often non-ASCII (Windows consoles)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    env = os.environ.get
    p = argparse.ArgumentParser(
        description="Run a multi-model LLM Council on a decision.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("question", nargs="?", help="The decision or question (or use --question-file).")
    p.add_argument("--question-file", help="Read the question/brief from a file.")
    p.add_argument("--context", nargs="*", default=[], help="Extra context files to include.")
    p.add_argument("--mode", choices=list(MODES), default=env("COUNCIL_MODE", "standard"))
    p.add_argument("--models", nargs="+",
                   default=[m.strip() for m in env("COUNCIL_MODELS", "").split(",") if m.strip()],
                   help="Council member models (seats are spread across them). Env: COUNCIL_MODELS")
    p.add_argument("--chairman", default=env("COUNCIL_CHAIRMAN"),
                   help="Chairman model (default: first --models entry). Env: COUNCIL_CHAIRMAN")
    p.add_argument("--base-url", default=env("COUNCIL_BASE_URL", "https://openrouter.ai/api/v1"),
                   help="OpenAI-compatible base URL. Env: COUNCIL_BASE_URL")
    p.add_argument("--api-key-env", default=None,
                   help="Name of the env var holding the key (default: COUNCIL_API_KEY, "
                        "then OPENROUTER_API_KEY, then OPENAI_API_KEY).")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--timeout", type=int, default=180, help="Per-call timeout in seconds.")
    p.add_argument("--out", default="council-transcripts",
                   help="Directory for the transcript ('' to disable).")
    p.add_argument("--json", action="store_true", help="Print the raw result as JSON.")
    p.add_argument("--mock", action="store_true", help="Offline dry run with fake model replies.")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args(argv)

    if a.question_file:
        question = Path(a.question_file).read_text(encoding="utf-8")
    elif a.question:
        question = a.question
    elif not sys.stdin.isatty():
        question = sys.stdin.read()
    else:
        p.error("provide a question, --question-file, or pipe text on stdin")
    question = question.strip()
    for f in a.context:
        question += f"\n\nCONTEXT FROM {Path(f).name}:\n{Path(f).read_text(encoding='utf-8')[:20000]}"

    if a.mock and not a.models:
        a.models = ["mock/model-a", "mock/model-b", "mock/model-c"]
    if not a.models:
        p.error("no models given. Use --models m1 m2 m3 or set COUNCIL_MODELS=m1,m2,m3")
    chairman = a.chairman or a.models[0]

    if a.api_key_env:
        key = env(a.api_key_env, "")
    else:
        key = env("COUNCIL_API_KEY") or env("OPENROUTER_API_KEY") or env("OPENAI_API_KEY") or ""
    local = any(h in a.base_url for h in ("localhost", "127.0.0.1", "[::1]"))
    if not key and not local and not a.mock:
        p.error("no API key found. Set COUNCIL_API_KEY (or OPENROUTER_API_KEY / OPENAI_API_KEY).")

    client = Client(a.base_url, key, a.temperature, a.timeout, mock=a.mock)
    result = run_council(question, a.models, chairman, a.mode, client, quiet=a.quiet)

    topic = question.splitlines()[0][:70]
    if a.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(render_verdict(result, topic))

    if a.out:
        out_dir = Path(a.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{dt.date.today().isoformat()}-{slugify(topic)}.md"
        path.write_text(render_transcript(result, topic), encoding="utf-8")
        log(f"\nTranscript saved: {path}", a.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
