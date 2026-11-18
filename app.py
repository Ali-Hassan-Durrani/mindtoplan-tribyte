"""Web viewer: streamlit run app.py. Uses the same process() function as plan.py."""
from pathlib import Path

import streamlit as st

import config
from llm import ConfigError, Trace
from pipeline import load_state, process, reset
from report import model_list_note, plan_text, rs, submission_text, trace_text
from ui import STATUS_CHIP, chip, css, e, kpi, table

st.set_page_config(page_title="MindToPlan", page_icon="🗓️", layout="wide")

PLAIN = {  # one-line plain explanation per check, for judges and users
    "correct figures": "Teams hold every student and food covers everyone on site.",
    "within budget": "Planned spending stays inside the approved budget.",
    "venue fits": "The chosen venue seats everyone and has every required facility.",
    "schedule valid": "Blocks add up exactly to the event length, with every required break.",
    "enough judges": "Enough judges to see every team without exceeding anyone's limit.",
    "all areas covered": "Venue, schedule, food, judging and budget all have a plan.",
}
ICON = {"PASS": "✅", "FAIL": "❌", "UNRESOLVED": "⚠️", "NOTED": "ℹ️"}
BLOCK_COLOR = {"hack": "#4f46e5", "judg": "#0891b2", "break": "#d97706", "prayer": "#d97706", "meal": "#16a34a",
               "lunch": "#16a34a", "open": "#7c3aed", "clos": "#7c3aed"}


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def run(text, source):
    try:
        with st.status("Processing messages…", expanded=True) as s:
            st.write("① Splitting messages and reading them with the model (1 call)")
            _, rep = process(text, source)
            st.write("② Planning the five areas in Python  ③ Validating every check")
            s.update(label=f"Done: {rep['calls']} model call(s), {rep['tokens']['total']} tokens, {rep['seconds']} s",
                     state="complete")
        st.session_state["last"] = rep
    except ConfigError as err:
        st.error(f"Config error: {err}")


def why(ev, label="Why?"):
    if ev and isinstance(ev, dict):
        with st.expander(f"🔎 {label}"):
            html(f"{chip(ev['msg'], 'acc')} <b>{e(ev['sender'])}</b> <span class='muted'>· {e(ev['date'] or 'no date')}</span>")
            html(f"<blockquote>“{e(ev['quote'])}”</blockquote>")


def key_numbers(p):
    """Numbers shown in the before→after diff."""
    if not p:
        return {}
    d, b = p["derived"], p["budget"]
    v, f = p["venue"]["chosen"], p["food"]
    return {"Total planned spend": rs(b["total"]), "Remaining budget": rs(b["remaining"]), "Budget": rs(b["budget"]),
            "Venue": f"{v['name']} ({rs(v['price'])})" if v else "-", "Food": f"{f['qty']} × {f['name']} = {rs(f['cost'])}" if f else "-",
            "Headcount": d["headcount"], "Teams": d["teams"], "Judges used": d["judges_used"],
            "Judging window": f"{p['schedule']['judging_min']} min", "Hacking time": f"{p['schedule']['hacking_min']} min",
            "Status": p["validation"]["status"]}


# ---------------- sidebar ----------------
if "dark" not in st.session_state:
    st.session_state["dark"] = False
state = load_state()
with st.sidebar:
    st.markdown("## 🗓️ MindToPlan")
    st.toggle("🌙 Dark mode", key="dark")
    st.caption(f"Model: `{config.MODEL_NAME or 'not set'}`  \n{model_list_note()}")
    st.markdown("**① Load the message pack**")
    up = st.file_uploader("Message pack or new messages (.txt)", type=["txt"], label_visibility="collapsed")
    if up and st.button("Process file", type="primary", width="stretch"):
        run(up.getvalue().decode("utf-8-sig"), up.name)
        st.rerun()
    if state and state.get("plan"):
        st.download_button("⬇ submission.txt (plan + full trace)", submission_text(state), "submission.txt",
                           type="primary", width="stretch")
    if st.button("↺ Reset (start over)", width="stretch"):
        reset()
        st.session_state.pop("last", None)
        st.rerun()
    st.caption("Official command: `python plan.py <messages.txt>`. This page runs the same function.")

html(css("dark" if st.session_state["dark"] else "light"))

has_plan = bool(state and state.get("plan"))
n_updates = len([u for u in (state or {}).get("updates", []) if u["mode"] == "update"])
step = 1 if not has_plan else (3 if n_updates else 2)
html('<div class="steps">' + "".join(
    f'<div class="step {"done" if i < step else "now" if i == step else ""}">{"✓" if i < step else i} {t}</div>'
    for i, t in ((1, "Load message pack"), (2, "Review the plan"), (3, "Add new messages"))) + "</div>")

if not has_plan:
    html('<div class="card"><div class="h">Welcome 👋</div>Upload the message pack in the sidebar, or run '
         '<code>python plan.py pack.txt</code>. The model reads the messages once; Python plans the venue, '
         'schedule, food, judging and budget and checks every rule.</div>')
    st.stop()

plan = state["plan"]
v = plan["validation"]
d, b = plan["derived"], plan["budget"]
checks = v["checks"]
fails = [c for c in checks if c["result"] == "FAIL"]
unres = [c for c in checks if c["result"] == "UNRESOLVED"]
last = st.session_state.get("last") or state["updates"][-1]

# ---------------- hero ----------------
if v["status"] == "VALID":
    sentence = f"All {len(checks)} checks pass: the plan fits the budget, the venue, the schedule and the judging rules."
elif v["status"] == "INVALID":
    sentence = f"{len(fails)} check(s) fail: " + "; ".join(f"{c['name']} — {c['detail']}" for c in fails)
else:
    sentence = "Information is missing or ambiguous: " + "; ".join(f"{c['name']} — {c['detail']}" for c in unres)
html(f'<div class="card hero"><span class="badge {v["status"].split()[0]}">{e(v["status"])}</span>'
     f'<div class="hero-text">{e(sentence)}</div></div>')

tabs = st.tabs(["📊 Overview", "🗂️ Plan", "✉️ Messages", "🧾 Trace", "➕ Update"])

# ---------------- overview ----------------
with tabs[0]:
    html('<div class="grid">'
         + kpi("Students", d["students"] or 0, f"teams of {int(d['team_size'] or 0)}", count=True)
         + kpi("Teams", d["teams"] or 0, "", count=True)
         + kpi("Headcount", d["headcount"], f"{int(d['students'] or 0)} students + {int(d['staff'])} staff + "
               f"{d['judges_used'] or 0} judges", count=True)
         + kpi("Budget", rs(b["budget"]))
         + kpi("Planned spend", rs(b["total"]), f"committed {rs(b['committed'])}")
         + kpi("Remaining", rs(b["remaining"]), "after all planned costs")
         + "</div>")
    if unres:
        html('<div class="card" style="border-left:5px solid var(--warn)"><div class="h">⚠️ Needs clarification</div>'
             + "".join(f"<div>• <b>{e(c['name'])}</b>: {e(c['detail'])}</div>" for c in unres) + "</div>")
    st.markdown("#### Checks")
    cols = st.columns(2)
    for i, c in enumerate(checks):
        plain = PLAIN.get(c["name"], "A requirement stated in the messages.")
        with cols[i % 2]:
            html(f'<div class="check {c["result"]}"><div style="font-size:1.3rem">{ICON.get(c["result"], "")}</div>'
                 f'<div><div class="t">{e(c["name"])} {chip(c["result"], {"PASS": "ok", "FAIL": "bad", "UNRESOLVED": "warn"}.get(c["result"], "info"))}</div>'
                 f'<div>{e(plain)}</div><div class="d">{e(c["detail"])}</div></div></div>')
    rejected = [i for i in state["items"] if i["status"] == "rejected"]
    if rejected:
        st.markdown("#### 🚫 Rejected messages")
        for i in rejected:
            html(f'<div class="card rej">{chip(i["msg"], "bad")} <b>{e(i["sender"])}</b>'
                 f'<div class="q">“{e(i["q"])}”</div><div class="muted">Reason: {e(i["reason"])}</div></div>')
    full_tokens = next((u["tokens"]["total"] for u in state["updates"] if u["mode"] == "full"), None)
    imp = last["impact"]
    changed, untouched = imp.get("changed") or [], imp.get("untouched") or []
    saving = ""
    if last["mode"] == "update" and full_tokens:
        pct = round(100 * (1 - last["tokens"]["total"] / full_tokens)) if full_tokens else 0
        saving = (f"<div class='muted'>Tokens this update: <b>{last['tokens']['total']:,}</b> vs full run "
                  f"{full_tokens:,} ({pct}% less than re-reading the whole pack).</div>")
    html(f'<div class="card"><div class="h">Last run: {e(last["update_id"])} ({e(last["mode"])})</div>'
         f'<div>Model calls: <b>{last["calls"]}</b> {"".join(chip(a, "acc") for a in last["call_areas"])} · '
         f'tokens <b>{last["tokens"]["total"]:,}</b> · {last["seconds"]} s</div>'
         f'<div style="margin-top:6px">Recalculated (Python): {"".join(chip(a, "warn") for a in changed) or chip("none")}'
         f' &nbsp; Untouched: {"".join(chip(a, "mute") for a in untouched) or chip("none")}</div>{saving}'
         + ("<div style='color:var(--warn)'>⚠️ Run incomplete (limit or model failure): last valid plan kept.</div>"
            if last["incomplete"] else "") + "</div>")
    if d["assumptions"]:
        st.caption("Assumptions (the pack is silent on these): " + "; ".join(d["assumptions"]))

# ---------------- plan ----------------
with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        ven = plan["venue"]["chosen"]
        html('<div class="card"><div class="h">🏛️ Venue</div>' + (
            f"<b>{e(ven['name'])}</b> — seats {int(ven['capacity'])}, {rs(ven['price'])}"
            + (f" {''.join(chip(x, 'ok') for x in ven['features'])}" if ven["features"] else "") if ven else "No venue")
            + (f"<div class='muted'>Required: {''.join(chip(x, 'acc') for x in plan['venue']['required_features'])}</div>"
               if plan["venue"]["required_features"] else "")
            + "".join(f"<div class='muted'>✗ {e(r['name'])}: {e(r['reason'])}</div>" for r in plan["venue"]["rejected"])
            + "".join(f"<div class='muted'>◦ alternative: {e(a['name'])} ({int(a['capacity'])} seats, {rs(a['price'])})</div>"
                      for a in plan["venue"]["alternatives"]) + "</div>")
        if ven:
            why(ven["evidence"], "Why this venue?")
    with c2:
        f = plan["food"]
        html('<div class="card"><div class="h">🍱 Food</div>' + (
            f"<b>{f['qty']} × {e(f['name'])}</b> @ {rs(f['pph'])} + delivery {rs(f['delivery'])} = <b>{rs(f['cost'])}</b>"
            f"<div class='muted'>People to feed: {f['people_to_feed']} = {int(d['students'] or 0)} students + "
            f"{int(d['staff'])} staff + {d['judges_used']} judges</div>"
            + "".join(f"<div class='muted'>◦ alternative: {e(a['name'])} @ {rs(a['pph'])}</div>" for a in f["alternatives"])
            if f else "No food plan") + "</div>")
        if f:
            why(f["evidence"], "Why this price?")
            if isinstance(f.get("qty_source"), dict):
                why(f["qty_source"], "Why this quantity?")

    s = plan["schedule"]
    segs = []
    for blk in s["blocks"]:
        col = next((c for k, c in BLOCK_COLOR.items() if k in blk["name"].lower()), "#64748b")
        segs.append(f'<div style="flex:{blk["min"]};background:{col}" title="{e(blk["time"])} {e(blk["name"])} '
                    f'({blk["min"]} min)">{e(blk["name"])} · {blk["min"]}m</div>')
    html('<div class="card"><div class="h">🕒 Schedule</div><div class="tl">' + "".join(segs) + "</div>"
         + table([{"time": x["time"], "block": x["name"], "minutes": x["min"],
                   "source": x["evidence"]["msg"] if x["evidence"] else "computed"} for x in s["blocks"]],
                 ["time", "block", "minutes", "source"]) + "</div>")
    for br in s["breaks"]:
        why(br["evidence"], f"Why the {br['name']}?")

    j = plan["judging"]
    html(f'<div class="card"><div class="h">⚖️ Judging</div>'
         f'<b>{j["judges_used"]}</b> of {j["judges_available"]} judges used (need {j["judges_needed"]}) · '
         f'max {j["max_teams_per_judge"]} teams each · {j["minutes_per_team"]} min/team · {j["rounds"]} rounds · '
         f'late offset {j["late_offset_min"]} min → judging window <b>{j["window_min"]} min</b></div>')
    with st.expander("Team allocation per judge"):
        html(table([{"judge": k, "teams": ", ".join(t)} for k, t in j["allocation"].items()], ["judge", "teams"]))
    jf = [i for i in state["items"] if i["status"] == "accepted" and i["k"] in
          ("judges_available", "max_teams_per_judge", "minutes_per_team", "honorarium", "late_min")]
    for i in jf:
        why({"msg": i["msg"], "sender": i["sender"], "date": i["date"], "quote": i["q"]}, f"Why {i['k'].replace('_', ' ')}?")

    cap = float(b["budget"] or 0)
    com = float(b["committed"])
    est = float(b["total"]) - com
    rem = max(cap - float(b["total"]), 0)
    tot = max(cap, float(b["total"])) or 1
    over = float(b["total"]) > cap
    html('<div class="card"><div class="h">💰 Budget</div>'
         f'<div class="bar"><div style="width:{100 * com / tot:.1f}%;background:var(--info)"></div>'
         f'<div style="width:{100 * est / tot:.1f}%;background:{"var(--bad)" if over else "var(--accent)"}"></div>'
         f'<div style="width:{100 * rem / tot:.1f}%;background:var(--ok);opacity:.55"></div></div>'
         f'<div class="legend" style="margin:6px 0 10px"><span><i style="background:var(--info)"></i>committed {rs(com)}</span>'
         f'<span><i style="background:var(--accent)"></i>planned {rs(est)}</span>'
         f'<span><i style="background:var(--ok);opacity:.55"></i>remaining {rs(b["remaining"])}</span></div>'
         + table([{"type": x["type"], "item": x["item"], "amount": rs(x["amount"]),
                   "source": x["evidence"]["msg"] if x["evidence"] else ""} for x in b["lines"]],
                 ["type", "item", "amount", "source"])
         + f"<div style='margin-top:8px'><b>Total {rs(b['total'])}</b> of {rs(b['budget'])} · remaining <b>{rs(b['remaining'])}</b></div>"
         + "".join(f"<div style='margin-top:6px'>{chip('optional · not included', 'info')} {e(o['item'])} {rs(o['amount'])} "
                   f"from {e(o['sender'])} ({e(o['msg'])}) — {'affordable' if o['affordable'] else 'NOT affordable'}</div>"
                   for o in b["optional"]) + "</div>")
    for x in b["lines"]:
        why(x["evidence"], f"Why {x['item']}?")

# ---------------- messages ----------------
with tabs[2]:
    c1, c2 = st.columns([2, 1])
    q = c1.text_input("🔍 Search messages")
    sf = c2.multiselect("Status", sorted({m["status"] for m in state["messages"]}))
    html("".join(chip(f"{s_}: {sum(m['status'] == s_ for m in state['messages'])}", STATUS_CHIP.get(s_, "mute"))
                 for s_ in sorted({m["status"] for m in state["messages"]})))
    for m in state["messages"]:
        if (q and q.lower() not in m["text"].lower()) or (sf and m["status"] not in sf):
            continue
        html(f'<div class="card">{chip(m["id"], "acc")} {chip(m["status"], STATUS_CHIP.get(m["status"], "mute"))} '
             f'<b>{e(m["sender"] or "?")}</b> <span class="muted">{e(m["date"])}</span>'
             f'<div style="white-space:pre-wrap;margin-top:6px">{e(m["text"])}</div>'
             + (f'<div class="muted" style="margin-top:6px">↳ {e(m["reason"])}</div>' if m["reason"] else "") + "</div>")
        items = [i for i in state["items"] if i["msg"] == m["id"]]
        if items:
            with st.expander(f"Facts read from {m['id']} ({len(items)})"):
                html(table([{"area": i["a"], "entity": i["e"], "key": i["k"], "value": i["v"], "kind": i["t"],
                             "status": chip(i["status"], STATUS_CHIP.get(i["status"], "mute")),
                             "quote": i["q"], "reason": i["reason"]} for i in items],
                           ["area", "entity", "key", "value", "kind", "status", "quote", "reason"]))

# ---------------- trace ----------------
with tabs[3]:
    t = Trace(state["trace"]).totals()
    upd = [u for u in state["updates"] if u["mode"] == "update"]
    html('<div class="grid">' + kpi("Model calls", t["calls"], "all runs", count=True)
         + kpi("Input tokens", f"{t['input']:,}") + kpi("Output tokens", f"{t['output']:,}")
         + kpi("Total tokens", f"{t['total']:,}", "as reported by the provider")
         + kpi("Area calls avoided", 5 * len(state["updates"]) - sum(1 for r in state["trace"] if r["area"] != "reading"),
               "planning runs in Python, not the model", count=True) + "</div>")
    if t["unavailable"]:
        st.warning(f"{t['unavailable']} call(s) with provider usage unavailable (shown as 'unavailable', never estimated)")
    st.caption(model_list_note())
    for r in reversed(state["trace"]):
        tok = (f"in {r['input_tokens']:,} · out {r['output_tokens']:,} · total {r['total_tokens']:,}"
               if r["total_tokens"] is not None else "tokens unavailable")
        html(f'<div class="card" style="padding:10px 14px">{chip("#" + str(r["n"]), "acc")} {chip(r["area"], "info")} '
             f'{chip("OK" if r["ok"] else "FAILED", "ok" if r["ok"] else "bad")} <b>{e(r["model"])}</b> '
             f'<span class="muted">· {e(r["update_id"])} · msgs {e(", ".join(r["message_ids"]))} · {tok} · {r["duration_s"]} s</span>'
             + (f'<div style="color:var(--bad)">{e(r["error"])}</div>' if r["error"] else "") + "</div>")
        with st.expander(f"Full input / output of call #{r['n']}"):
            st.text("SYSTEM:\n" + r["input"]["system"])
            st.text("USER:\n" + r["input"]["user"])
            st.text("OUTPUT:\n" + (r["output"] or "(none)"))
    st.markdown("#### Update history")
    html(table([{"run": u["update_id"], "mode": u["mode"], "new": ", ".join(u["new_messages"]), "calls": u["calls"],
                 "areas called": ", ".join(u["call_areas"]), "tokens": u["tokens"]["total"], "s": u["seconds"],
                 "changed": ", ".join(u["impact"].get("changed") or []), "rejected": len(u["rejected"])}
                for u in state["updates"]],
               ["run", "mode", "new", "calls", "areas called", "tokens", "s", "changed", "rejected"]))
    cols = st.columns(5)
    cols[0].download_button("plan.txt", plan_text(state), "plan.txt", width="stretch")
    cols[1].download_button("trace.txt", trace_text(state), "trace.txt", width="stretch")
    cols[2].download_button("submission.txt", submission_text(state), "submission.txt", width="stretch")
    for col, name in zip(cols[3:], ("plan.json", "trace.json")):
        p = Path(config.OUT_DIR) / name
        if p.exists():
            col.download_button(name, p.read_bytes(), name, width="stretch")

# ---------------- update ----------------
with tabs[4]:
    st.markdown("**③ Add new message(s)** — separate messages with a blank line. They go through exactly the same "
                "pipeline as the pack: 1 reading call, then Python re-plans only the affected areas.")
    new = st.text_area("New message(s)", height=140, placeholder="e.g. Finance here. The printing bill came in at …")
    if st.button("Process update", type="primary", disabled=not new.strip()):
        run(new, "ui")
        st.rerun()
    if last["mode"] == "update":
        before, after = key_numbers(state.get("previous_plan")), key_numbers(plan)
        rows = [(k, before.get(k), after[k]) for k in after if before.get(k) != after[k]]
        html(f'<div class="card"><div class="h">What changed in {e(last["update_id"])}</div>'
             + (f"<div class='muted'>New messages: {e(', '.join(last['new_messages']) or 'none')}</div>")
             + ('<div class="diff" style="margin-top:8px">' + "".join(
                 f"<div>{e(k)}</div><div class='muted' style='text-decoration:line-through'>{e(a)}</div><div>→</div>"
                 f"<div class='new'>{e(bv)}</div>" for k, a, bv in rows) + "</div>"
                if rows else "<div style='margin-top:8px'>No plan figures changed"
                + (" — the message was rejected and the previous valid plan was kept." if last["rejected"] else ".")
                + "</div>")
             + f'<div style="margin-top:8px">Recalculated: {"".join(chip(a, "warn") for a in last["impact"].get("changed") or []) or chip("none")}'
             f' Untouched: {"".join(chip(a, "mute") for a in last["impact"].get("untouched") or [])}</div>'
             + "".join(f'<div class="card rej" style="margin-top:8px">{chip("REJECTED", "bad")} “{e(x["quote"])}”'
                       f'<div class="muted">{e(x["reason"])}</div></div>' for x in last["rejected"]) + "</div>")
