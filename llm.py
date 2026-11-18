"""The only place that talks to a model. Every call goes through the Budgeter and lands in the trace."""
import json
import time
from datetime import datetime

import config

AREAS = ("reading", "venue", "schedule", "food", "judging", "budget")


class ConfigError(Exception):
    pass


class BudgetExhausted(Exception):
    pass


class Budgeter:
    """Wall-clock deadline and call cap for one run (full or update). Retries count as calls."""

    def __init__(self, mode):
        self.mode = mode
        self.start = time.monotonic()
        self.limit = config.FULL_RUN_SECONDS if mode == "full" else config.UPDATE_SECONDS
        self.max_calls = config.FULL_RUN_MAX_CALLS if mode == "full" else config.UPDATE_MAX_CALLS
        self.calls = 0
        self.incomplete = False

    def elapsed(self):
        return time.monotonic() - self.start

    def remaining(self):
        return self.limit - config.SAFETY_SECONDS - self.elapsed()

    def can_call(self):
        return self.calls < self.max_calls and self.remaining() > 2


class Trace:
    def __init__(self, records=None):
        self.records = records or []

    def totals(self, records=None):
        recs = self.records if records is None else records
        t = {"calls": len(recs), "input": 0, "output": 0, "total": 0, "unavailable": 0}
        for r in recs:
            if r["total_tokens"] is None:
                t["unavailable"] += 1
                continue
            t["input"] += r["input_tokens"] or 0
            t["output"] += r["output_tokens"] or 0
            t["total"] += r["total_tokens"]
        return t


def _client(timeout):
    if not (config.API_KEY and config.BASE_URL and config.MODEL_NAME):
        raise ConfigError("Missing model settings: set BASE_URL, MODEL_NAME and API_KEY in .env "
                          "(see .env.example).")
    if config.ALLOWED_MODELS and config.MODEL_NAME not in config.ALLOWED_MODELS:
        raise ConfigError(f"MODEL_NAME {config.MODEL_NAME!r} is not in ALLOWED_MODELS.")
    from openai import OpenAI
    return OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL, timeout=timeout, max_retries=0)


def call_model(budgeter, trace, area, system, user, message_ids, update_id, max_tokens=2000):
    """One logical call, at most one retry. Returns parsed JSON dict or None. Never raises for API errors."""
    assert area in AREAS
    for attempt in (1, 2):
        if not budgeter.can_call():
            budgeter.incomplete = True
            return None
        budgeter.calls += 1
        rec = {"n": len(trace.records) + 1, "timestamp": datetime.now().isoformat(timespec="seconds"),
               "model": config.MODEL_NAME, "area": area, "update_id": update_id,
               "message_ids": message_ids, "attempt": attempt,
               "input": {"system": system, "user": user}, "output": "",
               "input_tokens": None, "output_tokens": None, "total_tokens": None,
               "duration_s": 0.0, "ok": False, "error": None}
        t0 = time.monotonic()
        try:
            client = _client(timeout=max(budgeter.remaining(), 1))
            extra = {"reasoning_effort": config.REASONING_EFFORT} if config.REASONING_EFFORT else {}
            resp = client.chat.completions.create(**extra,
                model=config.MODEL_NAME, temperature=0, max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            rec["model"] = resp.model or config.MODEL_NAME
            rec["output"] = resp.choices[0].message.content or ""
            if resp.usage:
                rec["input_tokens"] = resp.usage.prompt_tokens
                rec["output_tokens"] = resp.usage.completion_tokens
                rec["total_tokens"] = resp.usage.total_tokens
            parsed = json.loads(rec["output"])
            rec["ok"] = True
            return parsed
        except ConfigError:
            budgeter.calls -= 1   # no request was sent, so no call happened
            raise
        except Exception as e:  # API error, timeout or invalid JSON: record honestly
            rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        finally:
            rec["duration_s"] = round(time.monotonic() - t0, 2)
            if rec["ok"] or rec["error"]:
                trace.records.append(rec)
    return None
