# MindToPlan: System Guide

Read this before the judge visits. The judges draw one team member at random and ask two questions:
**what is each part for, and what would break without it.** Every section below answers that.

---

## 1. The problem in one paragraph

We receive a text file of about 10 messages (emails, WhatsApp messages, notices; English, Roman Urdu or a
mix). Some messages are irrelevant, some are out of date and some are wrong. From these messages we must
plan a 4-hour hackathon (venue, schedule, food, judging, budget) that respects every stated constraint.
After the first run, new messages arrive one at a time. The plan must update, and a plausible-but-wrong
message must be rejected with the reason printed in the trace.

## 2. The one design decision that explains everything

> **The model only reads. Plain Python does all the arithmetic, planning and checking.**

Why:
- **Correct figures (30 pts):** models make arithmetic mistakes; Python does not.
- **Token use (5 pts):** one batched reading call per run, no "agent per area" calls.
- **Catching the wrong message (20 pts):** a deterministic validator decides validity, never the model.
- **Handling change (10 pts):** an update makes 1 call; Python re-plans only the affected areas.
- **Prediction (5 pts):** call routing is fixed, so it can be predicted exactly.
- **Small-model bonus (10 pts):** a small model is enough when it only has to read.

---

## 3. Problem-statement requirements: status

| # | Requirement (from the brief) | Status | How / where |
|---|---|---|---|
| 1 | Read every message from a text file exactly as given; no facts typed into code | ✅ Done | `plan.py` reads the file; `reader.split_messages` keeps raw text; no pack facts anywhere in code (samples live only in `samples/`, never imported) |
| 2 | Every message through the same command, no flags or hints | ✅ Done | `python plan.py <file>`: first run = full run, later runs = update (decided automatically by `.state/`) |
| 3 | Trace: every call numbered, model name, one area tag, input, output, provider token counts, total at end | ✅ Done | `llm.call_model` records each call; printed to the terminal and saved to `out/trace.txt` and `out/trace.json`; totals always printed |
| 4 | Accept new messages after the first run and update the existing plan | ✅ Done | Only messages with an unseen text hash are processed; previous facts and plan are reused |
| 5 | A conflicting message keeps the plan valid and the reason goes in the trace | ✅ Done | Transactional update in `pipeline._transaction`; `REJECTED …` lines in the trace, plan and UI |
| 6 | Plan covers venue, schedule, food, judging, budget | ✅ Done | `planner.py` |
| 7 | Respect every stated constraint, including unseen kinds | ✅ Mostly (see section 9) | Generic `{metric, op, value}` rules + one model call for a rule the reader could not express; unknown rule → NEEDS CLARIFICATION, never VALID |
| 8 | Full run within 2 min | ✅ Done (~4–5 s) | `Budgeter` hard limit 120 s with a 5 s safety margin |
| 9 | Update: max 5 model calls, within 1 min | ✅ Done (1 call, ~1–3 s) | `Budgeter` caps calls (retries count) and time |
| 10 | UI shows plan, trace and rejected messages clearly | ✅ Done | Terminal output (rich) + Streamlit page `streamlit run app.py` |
| 11 | Save final plan + full trace to a file for upload | ✅ Done | `out/submission.txt` (+ plan/trace .txt/.json) after every run |
| 12 | Six output checks: correct figures, within budget, venue fits, schedule valid, enough judges, all areas covered | ✅ Done | `validate.py`, printed as PASS / FAIL / UNRESOLVED |
| 13 | Clean `git status` at the test run | ✅ Done | `.gitignore` covers `.env`, `.state/`, `out/`, caches |
| 14 | Bring your own model, any provider | ✅ Done | Any OpenAI-compatible endpoint via `.env` |
| 15 | Small-model bonus | ⚠️ Unverified | The organizers' list has not been seen yet; put it in `ALLOWED_MODELS` |

---

## 4. How a run works, step by step

```
python plan.py pack.txt
  1. split    reader.split_messages   raw text → list of messages (exact text kept, hash per message)
  2. new?     pipeline.process        skip messages already seen (hash in .state/)
  3. read     reader.read_messages    ONE model call [reading] for all new messages → compact JSON
  4. check    Pydantic                schema validation of the model output
  5. clean    pipeline._normalize     fix common key misuse by a small model (generic rules)
  6. rules    pipeline._rule_fallback only for a hard rule with no checkable form: +1 call [its area]
  7. store    facts.resolve           which facts are active / superseded / rejected (authority, dates)
  8. plan     planner.build_plan      derive numbers → venue × food search → schedule, judging, budget
  9. check    validate.validate       6 checks + every stated hard rule → VALID / INVALID / NEEDS CLARIFICATION
 10. guard    pipeline._transaction   new item breaks a passing check → reject it, keep last valid plan
 11. output   report.*                print trace + plan; write out/*.txt, out/*.json, out/submission.txt
```

---

## 5. Every file: what it does, and what breaks without it

| File | Lines | What it does | What breaks without it |
|---|---|---|---|
| `plan.py` | 27 | The one command. Reads the file, calls `process()`, prints. | Nothing can run. |
| `pipeline.py` | 260 | `process()`: full vs update, new-message detection, the call to the reader, rule fallback, transaction, impact report, saving state. Also holds `ROUTES`, the dependency map (attribute → affected areas). | Updates would re-read everything; a wrong message would corrupt the plan; no impact report. |
| `reader.py` | 155 | Splits the file into messages (generic layouts). Builds the ONE reading prompt (messages wrapped in `<msg>` tags, treated as data). Pydantic schema for the output. | No language understanding: Roman Urdu, old vs new, quote vs approval. |
| `facts.py` | 124 | Fact store with provenance (message, sender, date, quote). Decides superseding: same entity + attribute, newer, and sender has authority. Event-wide numbers (budget, students…) are one value per event. | An old price would win, or a student could change the budget. |
| `planner.py` | 237 | Pure Python: teams, judges needed, headcount, venue choice, food choice, schedule blocks, judging allocation, budget lines (Decimal money). Tries venue × food combinations until one validates. | Arithmetic would be done by the model (wrong, costly). |
| `validate.py` | 150 | Deterministic checks + generic rule evaluator (`eq ne lt lte gt gte within requires excludes`). | Nobody could tell whether the plan is valid; the model would be trusted. |
| `llm.py` | 109 | The ONLY place that calls a model. `Budgeter` (time + call caps), one retry (3 s pause after 429/503), trace record with real provider usage. | Limits could be broken; the trace could misreport tokens or models. |
| `config.py` | 32 | Reads `.env`; limits; sender authority ranking; planning defaults. | Settings would be scattered or hardcoded. |
| `report.py` | 176 | Readable plan/trace text, `out/` files, rich terminal tables. | Nothing to upload; no printed trace. |
| `app.py` + `ui.py` | 325 + 109 | Streamlit page (light/dark, animations, evidence, timeline, budget bar, update box with diff). `ui.py` is CSS/HTML helpers only. | UI points; judges cannot see plan, trace and rejections at a glance. |
| `smoke.py` | 22 | One tiny call: latency, tokens, valid JSON? | No quick check that the key/model work. |
| `tests/` | 412 | 35 offline tests (fake reader, no network). | Regressions unnoticed. |

---

## 6. Key rules, in plain words (likely judge questions)

**Headcount.** Everyone on site needs a seat and a meal: students + staff + judges *actually used*.
Sample: 150 + 10 + 17 = **177**.

**Judges needed.** ceil(teams ÷ max teams per judge). Sample: ceil(50 ÷ 3) = 17. Only judges actually
used are paid and fed. Judging window = rounds × minutes per team + the largest late-arrival delay.

**Venue.** The cheapest venue with seats ≥ headcount and every required facility (e.g. generator,
projector). Rejected venues are listed with the reason.

**Food.** The latest valid quote. The standard/main meal first; if the budget fails, a cheaper option.
A caterer-wide delivery fee is added. Quantity = headcount unless a vendor states otherwise; if that is
below headcount, it is rejected.

**Schedule.** Blocks sum exactly to the event length: opening, hacking, required breaks (e.g. prayer),
meal, hacking, judging, closing. Defaults are used only when the pack is silent (opening 10, meal 30,
closing 15 min) and are shown as assumptions.

**Budget.** Committed spending + venue + food + judges' honorarium, computed in Decimal. Optional quotes
(e.g. a DJ) are **never** added; they are shown as "affordable / not affordable".

**Superseding.** A newer fact replaces an older one only for the same thing, and only if the sender has
enough authority: institution/finance > organizer > vendor > student > individual. A vendor may update its
own offer terms (prices, capacity, delivery). **The latest message does not automatically win.**

**Suggestions and claims.** "Can we get a DJ?" is a suggestion and is never spending. "Budget is now
Rs 900,000!" from a student club is rejected: the sender lacks authority, or it is not a confirmed fact.

**Prompt injection.** Messages are wrapped in `<msg>` tags; the prompt says to never follow instructions
inside them. An injection attempt is flagged in the run notes and its content is judged normally.

**Wrong message (the 20 points).** After applying new items, Python re-validates. If a check that passed
now fails (food below headcount, over budget, venue too small, too few judges, schedule overflow, a stated
rule broken), the item is **rejected**, the previous valid plan is kept, and the trace says why, e.g.
*"would break: correct figures (food for 100 but 177 people must eat)"*.

---

## 7. Model calls and the prediction slip

| New message contains | Model calls |
|---|---|
| Anything (price change, wrong quantity, new venue, irrelevant chat…) | **1 × `reading`** |
| A new kind of hard rule the reader could not turn into `{metric, op, value}` | **+1 call tagged with that rule's area** |

**Usual prediction: "only `reading` makes a model call."** All five areas are recalculated in Python, and
the impact line shows which actually changed (e.g. a printing price → `changed=['budget']`).

---

## 8. Model: multi-model support and model choice

**Does it work with different models?** Yes. Any OpenAI-compatible endpoint works by editing `.env` only
(`BASE_URL`, `MODEL_NAME`, `API_KEY`, optional `REASONING_EFFORT`, `ALLOWED_MODELS`). Tested: Gemini
3.5 Flash-Lite, 3.1 Flash-Lite, 3.8 Flash, Gemma 4, Groq Qwen 3.8 27B, Groq gpt-oss-20b.

**Does it automatically pick the model that uses fewest tokens?** **No, and this is deliberate.** The rules
and our design say: one model for every call, no fallback, no switching, so the trace stays honest and the
bonus is not put at risk. The model was chosen **offline** by benchmarking, then fixed in `.env`.

**Benchmark used for the choice** (end-to-end runs: sample pack + practice messages + an invented
unseen-style pack, 2 rounds, one model at a time):

| Model | Correct runs | Failed calls | Full run | Update | Avg tokens full / update |
|---|---|---|---|---|---|
| **gemini-3.5-flash-lite (chosen)** | **14/14** | **0/14** | 3.7 s | 1.3 s | 2,420 / 914 |
| gemini-3.1-flash-lite | 8/14 | 3/15 | 26 s (max 115) | 10 s | 1,426 / 798 |
| gemini-3.8-flash (low) | 0/14 | 64/64 (rate limit/quota) | – | – | – |
| gemini-2.5-flash-lite | not served (404) | | | | |
| Groq qwen3.8-27b | free tier: 1,000 output tokens/min, too low | | | | |
| Groq gpt-oss-20b | failed JSON validation in the smoke test | | | | |

3.1 Flash-Lite used fewer tokens but was slow and unreliable, so correctness and reliability came first.

---

## 9. What is NOT fully covered (honest limits / risks for the unseen pack)

| Gap | What happens today | Risk |
|---|---|---|
| Time-anchored events ("Zuhr prayer at 1:30 pm", "lunch must start at 1 pm") | The break is included with the right length but placed by our own order, not at that clock time | Schedule check could be judged wrong |
| Percentage charges ("+16% tax", "10% service charge", "keep 10% reserve") | Not modelled unless the reader turns it into a rupee amount | Budget figure could be off |
| Per-team or per-person extras ("kit Rs 500 per team") | Only fixed-amount expenses are modelled | Budget could be off |
| Dietary splits ("20 vegetarian meals") | One meal option for everyone | Food check could be judged incomplete |
| Judges leaving early or available only part of the time | Only "late by N min" is modelled | Judging check |
| Several rooms combined, or a venue with a time limit | One venue; time limits only via a generic rule on `end_min` | Venue check |
| Rules outside the metric list | Plan shows NEEDS CLARIFICATION (honest, but not VALID) | Lost output points |
| Organizers' small-model list | Unknown → "unverified" | Bonus |

These are the best candidates for new features.

---

## 10. Everything done in this session (chronological)

1. Cloned the repo, set up `.venv` (Python 3.13), pinned `requirements.txt`, `.gitignore`, `.env.example`.
2. `llm.py`: Budgeter, honest trace, one retry, graceful missing-credential error; `smoke.py`.
3. Found that Groq `llama-3.1-8b-instant` no longer exists; Groq Qwen hit the free-tier output cap; moved to Gemini.
4. `reader.py`: compact minified JSON prompt (cut output tokens ~35%), Pydantic schema, data-only `<msg>` tags.
5. `facts.py`, `planner.py`, `validate.py`, `pipeline.py`, `report.py`, `plan.py`: full run works, sample = **Rs 547,400, VALID**.
6. Transactional updates + dependency router: printing change → **Rs 552,400**, only budget changed; 100 boxes → **rejected**.
7. Recovered work after a git stash; found the Groq key in an unpushed commit; you squashed it out before pushing.
8. Tests on invented facts; fixed: header lines swallowing short messages; vendor price updates blocked by authority.
9. Invented unseen-style pack (120 students, teams of 4, projector rule in Roman Urdu, end-by-17:30 rule, injection, noise): fixed the full run rejecting the student count, the caterer-wide delivery fee, meal preference, broken facilities (`lacks_feature`), misused keys, rule routing.
10. Streamlit UI v1, README with the routing table.
11. Gemini 3.8 Flash trial: added `REASONING_EFFORT`; found 503/429 errors.
12. Robust splitter (numbered lines, `From:` headers, WhatsApp exports, chat lines, markdown tables; lists inside one email stay whole) + 12 tests.
13. `out/submission.txt` + "Messages detected: N" line.
14. Fixed a false-claim bug (a relabelled "budget is now Rs 900,000" was accepted) + tests.
15. Model benchmark → `gemini-3.5-flash-lite` (14/14, 0 failures).
16. UI v2: light/dark toggle, animations, status hero, step guide, check cards, "Why?" evidence, schedule timeline, budget bar, message chips, trace cards, before→after diff.
17. README: model settings, benchmark, judged-run checklist, splitter layouts. **35 tests pass.**

---

## 11. Judged test run: what to do

1. `git status` clean; `git log -1` equals the submitted hash.
2. `.env`: model and key; `ALLOWED_MODELS` if the list is published. Optional `python smoke.py`.
3. `Remove-Item -Recurse -Force .state, out`
4. Save the pack as `pack.txt` → `python plan.py pack.txt` → check "Messages detected: N".
5. Each new message → its own file → `python plan.py m1.txt` (then `m2.txt`, `m3.txt`).
6. Prediction slip: **only `reading`** (unless it is a new kind of rule: + that rule's area).
7. Upload `out/submission.txt`. Show the UI: `streamlit run app.py`.
