"""Web viewer: streamlit run app.py. Uses the same process() function as plan.py."""
from pathlib import Path

import pandas as pd
import streamlit as st

import config
from llm import ConfigError, Trace
from pipeline import load_state, process, reset
from report import model_list_note, plan_text, rs, trace_text

st.set_page_config(page_title="MindToPlan", layout="wide")
COLORS = {"VALID": "#1a7f37", "INVALID": "#cf222e", "NEEDS CLARIFICATION": "#bf8700"}


def run(text, source):
    try:
        with st.spinner("Processing messages..."):
            _, rep = process(text, source)
        st.session_state["last"] = rep
    except ConfigError as e:
        st.error(f"Config error: {e}")


def why(ev, label="why?"):
    if ev:
        with st.expander(label):
            st.markdown(f"**{ev['msg']}** · {ev['sender']} · {ev['date'] or 'no date'}")
            st.markdown(f"> {ev['quote']}")


state = load_state()

with st.sidebar:
    st.title("MindToPlan")
    st.caption(f"Model: `{config.MODEL_NAME or 'not set'}`  \n{model_list_note()}")
    up = st.file_uploader("Message pack / new messages (.txt)", type=["txt"])
    if up and st.button("Process file", type="primary"):
        run(up.getvalue().decode("utf-8-sig"), up.name)
        st.rerun()
    if st.button("Reset state (start over)"):
        reset()
        st.session_state.pop("last", None)
        st.rerun()
    st.caption("Official command: `python plan.py <messages.txt>`. This page calls the same function.")

if not state or not state.get("plan"):
    st.info("No plan yet. Upload the message pack in the sidebar (or run `python plan.py <file>`).")
    st.stop()

plan = state["plan"]
v = plan["validation"]
d, b = plan["derived"], plan["budget"]
tabs = st.tabs(["Overview", "Plan", "Messages & conflicts", "Trace", "Update"])

with tabs[0]:
    st.markdown(f"<div style='padding:12px 18px;border-radius:8px;background:{COLORS[v['status']]};color:white;"
                f"font-size:1.4rem;font-weight:600'>PLAN STATUS: {v['status']}</div>", unsafe_allow_html=True)
    c = st.columns(6)
    c[0].metric("Students", d["students"])
    c[1].metric("Teams", d["teams"])
    c[2].metric("Headcount", d["headcount"], help="students + staff + judges used")
    c[3].metric("Budget", rs(b["budget"]))
    c[4].metric("Planned spend", rs(b["total"]))
    c[5].metric("Remaining", rs(b["remaining"]))
    st.subheader("Checks")
    icon = {"PASS": "✅", "FAIL": "❌", "UNRESOLVED": "⚠️", "NOTED": "ℹ️"}
    st.dataframe(pd.DataFrame([{"": icon.get(x["result"], ""), "check": x["name"], "result": x["result"],
                                "area": x["area"], "detail": x["detail"]} for x in v["checks"]]),
                 hide_index=True, width="stretch")
    if d["assumptions"]:
        st.caption("Assumptions (pack silent): " + "; ".join(d["assumptions"]))
    last = st.session_state.get("last") or state["updates"][-1]
    st.subheader(f"Last run: {last['update_id']} ({last['mode']})")
    k = st.columns(4)
    k[0].metric("Model calls", last["calls"])
    k[1].metric("Tokens", last["tokens"]["total"])
    k[2].metric("Seconds", last["seconds"])
    k[3].metric("Areas recalculated", len(last["impact"].get("changed") or []))
    st.write(f"Changed: {last['impact'].get('changed')} · Untouched: {last['impact'].get('untouched')}")
    for x in last["rejected"]:
        st.error(f"Rejected {x['id']}: \"{x['quote']}\" — {x['reason']}")
    if last["incomplete"]:
        st.warning("Run incomplete (time/call limit or model failure). Last valid plan kept.")

with tabs[1]:
    ven = plan["venue"]["chosen"]
    st.header("Venue")
    if ven:
        st.success(f"**{ven['name']}** — seats {int(ven['capacity'])}, {rs(ven['price'])}"
                   + (f", features: {', '.join(ven['features'])}" if ven["features"] else ""))
        why(ven["evidence"])
    for r in plan["venue"]["rejected"]:
        st.write(f"✗ {r['name']}: {r['reason']}")
    for a in plan["venue"]["alternatives"]:
        st.write(f"◦ alternative: {a['name']} ({int(a['capacity'])} seats, {rs(a['price'])})")

    st.header("Schedule")
    st.dataframe(pd.DataFrame([{"time": x["time"], "block": x["name"], "minutes": x["min"],
                                "source": x["evidence"]["msg"] if x["evidence"] else "computed"}
                               for x in plan["schedule"]["blocks"]]), hide_index=True, width="stretch")
    for br in plan["schedule"]["breaks"]:
        why(br["evidence"], f"why {br['name']}?")

    st.header("Food")
    f = plan["food"]
    if f:
        st.success(f"**{f['qty']} × {f['name']}** @ {rs(f['pph'])} + delivery {rs(f['delivery'])} = **{rs(f['cost'])}**")
        st.write(f"People to feed: {f['people_to_feed']} = {d['students']} students + {d['staff']} staff + "
                 f"{d['judges_used']} judges")
        why(f["evidence"])

    st.header("Judging")
    j = plan["judging"]
    st.write(f"{j['judges_used']} of {j['judges_available']} judges used (need {j['judges_needed']}), "
             f"max {j['max_teams_per_judge']} teams each, {j['minutes_per_team']} min/team, {j['rounds']} rounds, "
             f"late offset {j['late_offset_min']} min → judging window {j['window_min']} min")
    st.dataframe(pd.DataFrame([{"judge": k2, "teams": ", ".join(t)} for k2, t in j["allocation"].items()]),
                 hide_index=True, width="stretch")

    st.header("Budget")
    st.dataframe(pd.DataFrame([{"type": x["type"], "item": x["item"], "amount": rs(x["amount"]),
                                "source": x["evidence"]["msg"] if x["evidence"] else ""} for x in b["lines"]]),
                 hide_index=True, width="stretch")
    st.write(f"**Total {rs(b['total'])}** of {rs(b['budget'])} · remaining **{rs(b['remaining'])}**")
    for o in b["optional"]:
        st.info(f"Optional (not in total): {o['item']} {rs(o['amount'])} from {o['sender']} ({o['msg']}) — "
                + ("affordable" if o["affordable"] else "NOT affordable"))
    st.download_button("Download plan.txt", plan_text(state), "plan.txt")

with tabs[2]:
    q = st.text_input("Search messages")
    sf = st.multiselect("Status", sorted({m["status"] for m in state["messages"]}))
    for m in state["messages"]:
        if (q and q.lower() not in m["text"].lower()) or (sf and m["status"] not in sf):
            continue
        badge = {"accepted": "🟢", "rejected": "🔴", "superseded": "⚪", "partly accepted": "🟠"}.get(m["status"], "🔵")
        with st.expander(f"{badge} {m['id']} [{m['status']}] {m['sender']} {m['date']}"):
            st.code(m["text"], language=None)
            if m["reason"]:
                st.write(f"**Reason:** {m['reason']}")
            items = [i for i in state["items"] if i["msg"] == m["id"]]
            if items:
                st.dataframe(pd.DataFrame([{"area": i["a"], "entity": i["e"], "key": i["k"], "value": str(i["v"]),
                                            "kind": i["t"], "hard": i["h"], "status": i["status"],
                                            "reason": i["reason"], "quote": i["q"]} for i in items]),
                             hide_index=True, width="stretch")
    st.subheader("Rejected and superseded facts")
    conf = [i for i in state["items"] if i["status"] in ("rejected", "superseded")]
    if conf:
        st.dataframe(pd.DataFrame([{"id": i["id"], "status": i["status"], "sender": i["sender"], "quote": i["q"],
                                    "reason": i["reason"]} for i in conf]), hide_index=True, width="stretch")
    else:
        st.write("None.")

with tabs[3]:
    t = Trace(state["trace"]).totals()
    c = st.columns(4)
    c[0].metric("Model calls", t["calls"])
    c[1].metric("Input tokens", t["input"])
    c[2].metric("Output tokens", t["output"])
    c[3].metric("Total tokens", t["total"])
    if t["unavailable"]:
        st.warning(f"{t['unavailable']} calls with provider usage unavailable")
    st.caption(model_list_note())
    st.dataframe(pd.DataFrame([{"#": r["n"], "update": r["update_id"], "area": r["area"], "model": r["model"],
                                "in": r["input_tokens"], "out": r["output_tokens"], "total": r["total_tokens"],
                                "s": r["duration_s"], "ok": r["ok"], "error": r["error"]} for r in state["trace"]]),
                 hide_index=True, width="stretch")
    for r in state["trace"]:
        with st.expander(f"#{r['n']} [{r['area']}] {r['model']} — {r['total_tokens']} tokens"):
            st.text("SYSTEM:\n" + r["input"]["system"])
            st.text("USER:\n" + r["input"]["user"])
            st.text("OUTPUT:\n" + (r["output"] or "(none)"))
    st.subheader("Update history")
    st.dataframe(pd.DataFrame([{"update": u["update_id"], "mode": u["mode"], "new": ", ".join(u["new_messages"]),
                                "calls": u["calls"], "areas called": ", ".join(u["call_areas"]),
                                "tokens": u["tokens"]["total"], "s": u["seconds"],
                                "changed": ", ".join(u["impact"].get("changed") or []),
                                "untouched": ", ".join(u["impact"].get("untouched") or []),
                                "rejected": len(u["rejected"])} for u in state["updates"]]),
                 hide_index=True, width="stretch")
    st.download_button("Download trace.txt", trace_text(state), "trace.txt")
    for name in ("plan.json", "trace.json"):
        p = Path(config.OUT_DIR) / name
        if p.exists():
            st.download_button(f"Download {name}", p.read_bytes(), name)

with tabs[4]:
    st.write("Paste one or more new messages (separate messages with a blank line). "
             "They go through exactly the same pipeline as the pack.")
    new = st.text_area("New message(s)", height=150)
    if st.button("Process update", type="primary", disabled=not new.strip()):
        run(new, "ui")
        st.rerun()
