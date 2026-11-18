# MindToPlan

Reads a pack of event messages (email, WhatsApp, notices; English and Roman Urdu) and plans a hackathon:
venue, schedule, food, judging, budget. **The model only reads. Python does all arithmetic, planning and validation.**

## Run

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows (source .venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
copy .env.example .env                              # then put your key in .env
python smoke.py                                     # 1 tiny call: latency, tokens, JSON ok?

python plan.py pack.txt          # first run = FULL run (no .state/ yet)
python plan.py new_message.txt   # every later run = UPDATE (only messages not seen before)
streamlit run app.py             # web viewer + add-message box (same function as plan.py)
```

- Same command for every input. New messages can be a new file, or appended to the pack file (already-seen
  messages are skipped by text hash).
- Delete `.state/` to start over.
- After every run: `out/submission.txt` (plan + full trace, the file to upload), `out/plan.txt`, `out/plan.json`,
  `out/trace.txt`, `out/trace.json`; the trace is printed too.
- Model is set only in `.env`, never in code, so it can change after code freeze:

| Variable | Meaning |
|---|---|
| `BASE_URL` | OpenAI-compatible endpoint (Gemini, Groq, local Ollama) |
| `MODEL_NAME` | the one model used for every call (no fallback model) |
| `API_KEY` | key for that endpoint (never committed: `.env` is gitignored) |
| `REASONING_EFFORT` | optional, only for "thinking" models (`none`/`low`); leave empty otherwise |
| `ALLOWED_MODELS` | optional comma list = organizers' small-model list; any other model is refused and the trace header says "yes" instead of "unverified" |

### Model choice

We use **`gemini-3.5-flash-lite`** (Gemini OpenAI-compatible endpoint, `REASONING_EFFORT` empty): a small,
non-thinking model, which fits the small-model bonus and keeps tokens low. Chosen by a benchmark run one model
at a time: the sample pack + both practice messages + a Roman Urdu generator update, and an invented unseen
pack (new constraint kinds, stale price, injection, irrelevant message) + a price correction + a false
budget claim, twice each:

| Model | Correct runs | Failed calls | Full run | Update | Tokens full / update |
|---|---|---|---|---|---|
| **gemini-3.5-flash-lite** | **14/14** | **0/14** | 3.7 s avg (max 4.8) | 1.3 s avg (max 2.0) | ~2,400 / ~900 |
| gemini-3.1-flash-lite | 8/14* | 3/15 | 26 s avg (max 115) | 10 s avg (max 55) | ~1,400 / ~800 |
| gemini-3.8-flash (`low`) | slower (17 s full), hidden thinking tokens, 503 "overloaded" errors in testing | | | | |
| gemini-2.5-flash-lite | no longer served (404) | | | | |
| Groq qwen3.8-27b | free tier caps output at 1,000 tokens/min: too low for a full run | | | | |

\*partly disturbed by rate limits from a parallel test on the same key. If the organizers' small-model list
excludes our model, change `MODEL_NAME` in `.env` (no code change) and run `python smoke.py`.
Free-tier keys are rate limited: run one command at a time, as in the judged test.

## Judged test run (checklist)

1. `git status` → clean; `git log -1` → matches the submitted hash.
2. Check `.env`: model, key, `ALLOWED_MODELS` from the organizers' list. Optional: `python smoke.py`.
3. Reset: `Remove-Item -Recurse -Force .state, out` (PowerShell) or `rm -rf .state out`.
4. Save the unseen pack as e.g. `pack.txt` → `python plan.py pack.txt`. Check the line
   "Messages detected in this input: N new" matches the number of messages in the pack.
5. Each new message → save to its own file (`m1.txt`, `m2.txt`, `m3.txt`) → `python plan.py m1.txt`, etc.
6. Prediction slip: **only `reading` makes a model call** (1 call per update), unless the message adds a new
   kind of rule the reader cannot express; then **+1 call tagged with that rule's area**. Impact line shows
   which areas were recalculated (Python, no calls).
7. Upload `out/submission.txt` (plan + full trace). Optional UI: `streamlit run app.py`.

## Pack layouts the splitter handles

Blank-line separated messages (with optional "Message 3" / "[3]" header lines), numbered lines without blank
lines (`1.`, `[2]`, `#3`, `Message 4`), repeated `From:` headers, WhatsApp-export timestamps, `Name: text`
chat lines, and markdown tables (one message per row). A numbered list inside one email stays one message.
Tests in `tests/test_split.py`.

## How it works

```
pack.txt ─► split (code) ─► reader: ONE model call [reading] ─► items (Pydantic-validated)
        ─► facts: provenance, supersede by entity+attribute+authority
        ─► planner (Python): derive numbers ─► venue / schedule / food / judging / budget
        ─► validate (Python): 6 checks + stated hard rules ─► VALID / INVALID / NEEDS CLARIFICATION
        ─► transaction: an item that breaks a passing check is REJECTED, previous valid plan kept
        ─► out/ files + printed trace
```

| File | What it does | What breaks without it |
|---|---|---|
| `plan.py` | The one command. Reads the file, calls `process()`, prints. | No way to run. |
| `pipeline.py` | `process()`: full vs update, new-message detection by hash, rule escape hatch, transaction, impact report, state. | Updates would re-read everything; wrong messages would corrupt the plan. |
| `reader.py` | Splits the file into messages (generic structure only). ONE batched model call turns all new messages into compact items. Messages are wrapped in `<msg>` tags and treated as data (injection flagged). | No language understanding (Roman Urdu, stale vs new, quote vs approval). |
| `facts.py` | Fact store. Later fact replaces earlier only for the same area+entity+attribute and only if the sender has authority (institution/finance > organizer > vendor > student > individual; vendors own their own offer terms). Suggestions/quotes never become spending. | Old prices would win, or a student could change the budget. |
| `planner.py` | Pure Python. Teams = ceil(students/team size); judges needed = ceil(teams/max per judge); headcount = students + staff + judges used; cheapest venue that fits and has required features; standard meal unless budget fails; schedule blocks sum exactly to the event length; Decimal money. Searches venue × food choices until a plan validates. | Arithmetic would be done by the model (wrong, costly). |
| `validate.py` | Deterministic checks: correct figures, within budget, venue fits, schedule valid, enough judges, all areas covered, plus every stated hard rule via a generic `{metric, op, value}` evaluator (eq, ne, lt, lte, gt, gte, within, requires, excludes). Unknown rule → UNRESOLVED, never VALID. | Nobody would know whether the plan is valid; the model would be trusted. |
| `llm.py` | The only model access. `Budgeter`: full run 120 s, update 60 s and max 5 calls (retries count), stops early with "incomplete". Records every call: model name from the API response, area tag, full input/output, provider token usage ("unavailable" if missing, never estimated). | Limits could be exceeded; trace could misreport. |
| `report.py` | Readable plan/trace text, `out/` files, rich terminal output. | No saved files to upload. |
| `app.py`, `ui.py` | Streamlit viewer (light/dark toggle): status hero + 3-step guide, check cards, plan cards with "Why?" evidence for every decision, schedule timeline, budget bar, message chips, trace call cards, update box with before→after diff. `ui.py` holds only CSS/HTML helpers. | UI points; judges could not see plan, trace and rejections at a glance. |

## Which areas make model calls (for the prediction slip)

| New message contains | Model calls | Areas recalculated in Python |
|---|---|---|
| Any new message | **1 × `reading`** (always exactly one batched call) | depends on attributes below |
| A requirement the reader can express as a `{metric, op, value}` rule | none extra | the rule's area |
| A **new kind of hard rule the reader could not express** | **+1 call tagged with that rule's area** (venue/schedule/food/judging/budget) | that area |
| Food price / delivery / meal tier / order quantity | none extra | food, budget |
| Venue capacity / price / feature / availability / required facility | none extra | venue, budget |
| Break or activity duration, event length, start time | none extra | schedule |
| Judge count / max teams per judge | none extra | judging, venue, food, budget, schedule (headcount changes) |
| Honorarium | none extra | judging, budget |
| Minutes per team / late judge | none extra | judging, schedule |
| Committed expense / optional quote | none extra | budget |
| Students / team size | none extra | all five |
| Irrelevant message | 1 × `reading` only | none |

So the usual prediction is: **only `reading` makes a model call.** The impact report (`changed` vs `untouched`)
shows which areas actually changed.

## Rejecting a wrong message

The plan is rebuilt with the new items. If a check that passed now fails (food below headcount, over budget,
venue too small, too few judges, schedule overflow, a stated rule broken), or the sender lacks authority,
the offending item is rejected, the last valid plan is kept, and the reason with evidence goes to the trace
and plan (e.g. *"would break: correct figures (food for 100 but 177 people must eat)"*).

## Tests

```bash
python -m pytest -q
```
Pure-Python tests (no network) use invented facts that differ from the sample pack: different event size,
over-budget fallback, too few judges, required facility, a new rule kind (end time), unresolvable rule,
authority, vendor price update, optional quotes, splitting, price update touches only food+budget, wrong
quantity rejected, infeasible update keeps the previous plan, new mandatory break, irrelevant and
prompt-injection messages, call cap and deadline, missing credentials, failed calls recorded, trace totals.

`samples/` holds the sample pack and test messages for local runs only; no code imports them.

## Limits / assumptions

- When the pack is silent, opening (10 min), meal (30 min) and closing (15 min) use planning defaults, shown as
  assumptions in the plan. Minimum hacking time 30 min.
- Everyone on site eats and needs a seat: students + staff + judges actually used.
- A late judge's delay is added to the judging window.
