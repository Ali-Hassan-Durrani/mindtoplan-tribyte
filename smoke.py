"""One tiny model call: latency, reported usage, and valid JSON on an invented Roman Urdu sample."""
import sys

import config
from llm import Budgeter, ConfigError, Trace, call_model

SYSTEM = 'Return JSON {"price": number, "unit": string} for the price in the message.'
USER = "Bhai chai ka cup ab Rs 90 ka hai, pehle 70 tha."

if __name__ == "__main__":
    trace = Trace()
    try:
        out = call_model(Budgeter("update"), trace, "reading", SYSTEM, USER, ["smoke"], "smoke", 60)
    except ConfigError as e:
        sys.exit(f"Config error: {e}")
    r = trace.records[-1]
    print(f"endpoint     : {config.BASE_URL}")
    print(f"model (API)  : {r['model']}")
    print(f"latency      : {r['duration_s']} s")
    print(f"tokens       : in={r['input_tokens']} out={r['output_tokens']} total={r['total_tokens']}")
    print(f"raw output   : {r['output']}")
    print(f"valid JSON   : {out is not None}  error={r['error']}")
