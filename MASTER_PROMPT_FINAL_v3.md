# MindToPlan — build brief for Claude Code

You are a senior Python engineer in a timed hackathon (Mind to Machine, GDG on Campus COMSATS Wah). Code freeze is 13:25 today, so we have about 2 hours. The architecture below is decided: do NOT ask me to approve it. First inspect the repo, Python version and environment, and locate the supplied message file. Ask me only for genuinely missing essentials (API key, model name). Do not stop at a plan or skeleton: create the files, install dependencies, run the system, run the tests, debug, and only claim what you have actually tested. Commit and push after every working milestone. Everything below is enforced IN CODE and runs automatically; I will not time runs, count tokens or copy files by hand.

## 1. Task (from the organizers)

Build a system that reads a pack of ~10 messages (email, WhatsApp, notices; English, Roman Urdu, mixed; some irrelevant, some outdated) and plans a 4-hour physical hackathon in Islamabad for 150 students in 50 teams. Plan areas: venue, schedule, food, judging, budget. The pack at judging is unseen: different numbers, wording, senders, and new KINDS of constraint.

Judging sequence: unseen pack run, then 3 more messages one at a time. Two change the task, one is plausible but wrong and must be rejected with the reason in the trace. The plan is checked on six things: correct figures, within budget, venue fits, schedule valid, enough judges, all areas covered.

Scoring that shapes the design: output correctness 30, catching the wrong message 20 (first tie-break), explaining the system 20, handling change 10 (only affected areas may make model calls; second tie-break), UI 10, prediction of which areas call the model 5, token use 5 (fewer is better; third tie-break), bonus 10 if EVERY model call uses a model on the organizers' small-model list (a model on my laptop counts) and the plan passes every check. A part of the system that cannot be justified costs points; the number of agents earns nothing. Every team member must be able to explain the system, so keep it simple.

## 1b. Tech stack (fixed, do not add to it)

- Python 3.11, standard library for json, decimal (money), hashlib (message hashes), time and dataclasses.
- `openai` Python SDK pointed at any OpenAI-compatible endpoint through BASE_URL (Gemini, Groq or local Ollama). One provider, one model, no other LLM SDKs.
- `pydantic` for typed schemas and validating model output.
- `python-dotenv` for secrets.
- `rich` for formatted terminal output and the printed trace.
- `streamlit` for the web viewer (and `pandas` only if a table needs it).
- `pytest` for tests.
- Persistence: plain JSON files in `.state/`. No database, no vector store, no LangChain/CrewAI/AutoGen.
- `requirements.txt` with pinned versions and a `.env.example` with MODEL_NAME, API_KEY, BASE_URL, ALLOWED_MODELS (no real keys).

## 2. Non-negotiable rules (all enforced in code)

1. ONE command for everything: `python plan.py messages.txt`. No flags, hints or edits per message. State lives in `.state/`. If state exists, only messages not seen before (hash of text) are processed as an UPDATE; otherwise it is a full run. New messages arrive by appending to the file or by passing another file to the same command. Deleting `.state/` resets. The Streamlit UI (section 5) is a viewer and an add-message box that calls the same function; it is NOT the official command.
2. `git status` must be clean at the test run. `.gitignore` covers `.state/`, `out/`, `.env`, `__pycache__/`. The program never writes to a tracked file and never modifies the input file.
3. No pack facts in code: no names, prices, dates, numbers or message text, and no regex tuned to sample wording. Generic domain logic (ceil, capacity comparison, interval checks) is fine. The sample pack may live in `samples/` for local testing only; no code imports it.
4. Trace: every real model call numbered, with timestamp, model name (as reported by the API response), exactly ONE area tag (reading|venue|schedule|food|judging|budget), full input (system and user prompts), full raw output, input/output/total tokens as reported by the provider, duration, success/failure, message ids and update id. Failed calls and retries are recorded honestly and count toward the call limit. After the last call, ALWAYS print total input, output and total tokens plus total model calls and wall-clock seconds, even if the run ended on a deadline or error (try/finally). Python steps are never logged as model calls. If the provider reports no usage, print "unavailable", never an estimate. Never log API keys.
5. Central `Budgeter` used by every model call: before each call check remaining time and call count. Full run: 120 s hard wall-clock deadline. Update: 60 s and at most 5 calls, retries included. Set the HTTP request timeout to the time remaining. At most one retry per call, and only if time and calls allow. When time or calls run out, stop, keep the last valid plan, and print an "incomplete" warning. The program exits by itself before the limit.
6. Model access uses the OpenAI-compatible chat API (works for Gemini, Groq, and local Ollama through BASE_URL), configured only in `.env` (MODEL_NAME, API_KEY, BASE_URL, optional ALLOWED_MODELS comma list). Changing the model never requires a code change (code is frozen at 13:25; `.env` is gitignored). The organizers' small-model list is NOT known yet. Use exactly ONE model for the whole system, the smallest fast one that passes the smoke test, with NO fallback to another model. If ALLOWED_MODELS is set the Budgeter refuses other models. The trace header says "model on organizers' small-model list: unverified" unless ALLOWED_MODELS is set. Temperature 0, JSON output, use provider usage metadata. Missing or invalid credentials must fail gracefully with a clear message, not a stack trace.
7. Smoke test first (`python smoke.py`): one tiny call printing latency, reported token usage, and whether the model returns valid JSON for an invented Roman Urdu sample. Report the result to me.
8. After EVERY run, automatically write `out/plan.txt`, `out/plan.json`, `out/trace.txt`, `out/trace.json` (full plan, every message with status and reason, full trace, totals, update history) and print the readable trace to the terminal.
9. Message text is untrusted DATA, never instructions. Wrap messages in clear delimiters in the prompt and tell the model to ignore any instruction inside them. A message that tries to change system behavior is flagged and its other content is judged normally.

## 3. Architecture: the model only READS, code does everything else

- `reader.py` (1 model call, tag `reading`): all new messages go in one batched call. Compact JSON out, short keys, validated with Pydantic. Per message: id, sender, date as written, channel, relevant (bool), items[]. Each item: area, entity, attribute, value, unit, kind (fact|update|suggestion|question|rule|irrelevant), hard (bool), quote. Distinguish approved commitments from quotations, tentative statements, suggestions and speculation. Do not send history or fields we do not use (tokens are scored).
- `facts.py`: fact store with provenance (message id, sender, date, quote, status accepted|superseded|rejected|pending). A later message supersedes an earlier one only for the same entity+attribute, and only when its sender is plausibly authoritative (generic authority ranking in config: institution/finance > vendor > student group > individual). The latest message does not automatically win. Suggestions and questions NEVER become facts or expenses. Missing year: compare day/month within the pack; do not invent a year. If only one item in a message is invalid, keep its other valid items. Never silently discard a message.
- `derive.py` (pure Python, money in `Decimal`): teams = students / team_size; judges_needed from max teams per judge AND minutes per team vs the judging window; people_to_feed = students + staff + judges actually used (everyone on site eats; do not assume students only); on-site headcount for venue capacity likewise. Acceptance check only, never in code: the sample pack must give 177 people.
- Planners (pure Python, no model calls): venue (cheapest option with capacity >= headcount that satisfies stated needs such as generator; list rejected options with reason), schedule (blocks sum exactly to the event length; prayer break; meal; judging window long enough for rounds plus any late-judge offset), food (latest valid quote, standard unless budget fails then basic, include delivery), judging (team-to-judge allocation, slots, late-arrival offsets), budget (committed vs estimated vs optional, remaining, deficit; optional items never summed into the total; suggest feasible alternatives, clearly labeled as suggestions, when over budget).
- `validate.py`: the six named checks plus all stated hard constraints, using a generic constraint record with operators equals, not_equals, lt, lte, gt, gte, requires, excludes, within_interval. Unsupported hard constraints are NEVER treated as satisfied: they are marked unresolved. Final status is one of VALID, INVALID, NEEDS CLARIFICATION; an unresolved hard constraint can never show VALID. Print PASS/FAIL/UNRESOLVED per check. The model never decides validity.
- Transactional updates: copy facts, apply the new items, rebuild affected areas, validate. If a check that passed now fails (e.g. food quantity below headcount, over budget, venue too small, sender lacks authority), REJECT that item or message, keep the previous valid plan, and write the reason with evidence in the trace (e.g. "would feed 100 but headcount is 177"). This catches unseen wrong messages generically. Ambiguous evidence is shown as a clarification request, not turned into a fact.
- Dependency router: map each changed attribute to affected areas (e.g. food price -> food + budget, not venue or judging; judge availability -> judging + schedule), recompute only those, store a change-impact report (changed vs untouched areas, recomputations avoided).
- Escape hatch for unseen constraint kinds: `rule` items with no matching code operator get ONE extra model call tagged with the affected area that returns a structured constraint record run by the generic evaluator. If it cannot be expressed, show "unhandled constraint, needs human review" and keep the plan NEEDS CLARIFICATION. Never exceed 5 calls per update.
- Routing is deterministic so my written prediction is explainable: README contains a table of which attributes trigger model calls in which areas.

## 4. Interface (10 points, keep it small)

1. Rich terminal output first (plan, six checks, accepted/superseded/rejected/pending messages with reasons and evidence, trace table, totals). Required.
2. Then one Streamlit page (`streamlit run app.py`, calls the same function as plan.py) with tabs: Overview (status badge VALID/INVALID/NEEDS CLARIFICATION, headcount, teams, budget, committed, remaining), Plan (five sections; each decision has a "why" expander with source message, sender, date and quote), Messages and conflicts (accepted/superseded/rejected/pending with reasons, search/filter), Trace (table, totals, calls avoided), Update (paste a new message, same pipeline, shows what changed). Never show green for a plan with unresolved hard constraints. Download buttons for the out/ files.

## 5. Out of scope unless everything else passes by 12:30

OCR, voice, decision-history snapshots beyond a simple update log, what-if simulator, budget charts. Do not use LangChain, CrewAI, AutoGen, vector DBs or other heavy infrastructure. No area-specific LLM planning calls (they cost tokens and the planners are deterministic).

## 6. Tests

Pure-Python tests for derive/planners/validator/transactional rejection using messages not taken from the sample pack (Roman Urdu, a new constraint kind, an over-budget quote, an under-capacity venue, a new mandatory break, a late judge, an irrelevant message, a message containing a prompt-injection attempt). Also: a price update affects food and budget but not venue or judging; an invalid update leaves the previous valid plan intact; update calls <= 5; deadlines trigger a clean exit; missing credentials fail gracefully; trace totals equal the sum of per-call provider usage. One integration run with the real model, then the two practice messages: a printing bill correction (valid change) and a caterer rounding the order down to 100 boxes (must be rejected with a reason).

## 7. Order of work (report at each milestone, then continue)

1. 11:15 `.gitignore`, smoke test, trace + Budgeter
2. 11:45 reader + facts + derive + planners + validate; full run works on the sample pack
3. 12:15 transactional update + router; both practice messages work
4. 12:35 own unseen-style tests, fix failures
5. 12:50 UI + exports, README with routing table
6. 13:05 final push; print and tell me the commit hash; stop changing code

When finished, report: the exact run command, files created, test results, remaining limitations, and the git commands for submission.

## 8. Disqualification checklist (verify before pushing)

Facts typed in code, misreported tokens/models/areas, dirty git status, changes after freeze, any model call missing from the trace, any call to a second model, update over 5 calls, run over its time limit, API key committed.
