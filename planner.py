"""Derived numbers and the five area planners. Pure Python, no model calls, money in Decimal."""
import math
from decimal import Decimal

import config
from facts import View, norm, num
from validate import validate


def D(x):
    return Decimal(str(x if x is not None else 0)).quantize(Decimal("1"))


def ev(f):
    """Evidence for a decision: where it came from."""
    return {"msg": f["msg"], "sender": f["sender"], "date": f["date"], "quote": f["q"]} if f else None


def derive(v):
    d = {"assumptions": [], "missing": []}
    for k in ("students", "team_size", "staff", "duration_min", "budget_total"):
        d[k] = v.val(k)
    for k in ("judges_available", "max_teams_per_judge", "minutes_per_team", "honorarium"):
        d[k] = v.val(k, "judging")
    for k in ("students", "duration_min", "budget_total"):
        if d[k] is None:
            d["missing"].append(k)
    d["staff"] = d["staff"] or 0
    s, ts = d["students"], d["team_size"]
    d["teams"] = math.ceil(s / ts) if s and ts else None
    ja, mx = d["judges_available"], d["max_teams_per_judge"]
    if d["teams"] and mx:
        d["judges_needed"] = math.ceil(d["teams"] / mx)
    else:
        d["judges_needed"] = ja
    d["judges_used"] = min(x for x in (d["judges_needed"], ja) if x is not None) \
        if (d["judges_needed"] is not None or ja is not None) else None
    lates = [num(f["v"]) or 0 for f in v.all("late_min")]
    d["late_max"] = max(lates) if lates else 0
    if d["teams"] and d["judges_used"] and d["minutes_per_team"]:
        d["rounds"] = math.ceil(d["teams"] / d["judges_used"])
        d["judging_window"] = int(d["rounds"] * d["minutes_per_team"] + d["late_max"])
    else:
        d["rounds"], d["judging_window"] = None, None
    # everyone on site eats and needs a seat: students + staff + judges actually used
    d["headcount"] = int((s or 0) + d["staff"] + (d["judges_used"] or 0))
    return d


def venue_candidates(v, d):
    needs = [norm(f["v"]) for f in v.all("requires_feature")]
    opts = v.options("venue", {"capacity", "price", "feature", "lacks_feature", "unavailable"})
    ok, rejected = [], []
    for key, o in opts.items():
        if "capacity" not in o and "price" not in o:
            continue                                  # only a remark about a facility, not a venue offer
        cap = num(o["capacity"]["v"]) if "capacity" in o else None
        price = num(o["price"]["v"]) if "price" in o else None
        lacks = [norm(f["v"]) for f in o.get("lacks_feature", [])]
        feats = [norm(f["v"]) for f in o.get("feature", [])
                 if not any(norm(f["v"]) in x or x in norm(f["v"]) for x in lacks)]
        why = None
        if "unavailable" in o:
            why = "not available"
        elif cap is None or price is None:
            why = "capacity or price unknown"
        elif cap < d["headcount"]:
            why = f"seats {int(cap)} < headcount {d['headcount']}"
        else:
            lacking = [n for n in needs if not any(n in f or f in n for f in feats)]
            if lacking:
                why = f"lacks required: {', '.join(lacking)}"
        row = {"name": o["_name"], "capacity": cap, "price": price, "features": feats,
               "evidence": ev(o.get("capacity") or o.get("price"))}
        (rejected if why else ok).append({**row, "reason": why} if why else row)
    ok.sort(key=lambda r: r["price"])
    return ok, rejected, needs


def food_options(v):
    opts = v.options("food", {"price_per_head", "delivery_fee", "tier", "order_qty"})
    # a delivery fee not tied to a priced option applies to every option (caterer-wide charge)
    general = [num(o["delivery_fee"]["v"]) for o in opts.values()
               if "delivery_fee" in o and "price_per_head" not in o]
    general_fee = max(general) if general else 0
    out = []
    for key, o in opts.items():
        if "price_per_head" not in o:
            continue
        tier = norm(o["tier"]["v"]) if "tier" in o else ""
        out.append({"name": o["_name"], "pph": num(o["price_per_head"]["v"]),
                    "delivery": num(o["delivery_fee"]["v"]) if "delivery_fee" in o else general_fee,
                    "tier": tier, "evidence": ev(o["price_per_head"])})
    # preference: the standard option first, then cheaper ones (fallback when budget fails)
    # untagged options: fuller (pricier) meal first; build_plan falls back to cheaper ones if the budget fails
    rank = lambda r: 0 if "standard" in r["tier"] or "standard" in norm(r["name"]) else \
        {"": 1, "premium": 2, "basic": 3}.get(r["tier"], 1)
    out.sort(key=lambda r: (rank(r), r["pph"] if rank(r) != 1 else -r["pph"]))
    return out


def schedule_plan(v, d):
    total = int(d["duration_min"] or 0)
    named = {norm(f["e"]): (f["e"], int(num(f["v"]) or 0), f) for f in v.all("activity_min")}

    def pick(word, label, default):
        for k, (name, m, f) in named.items():
            if word in k:
                named.pop(k)
                return name, m, f
        d["assumptions"].append(f"{label} {default} min (not stated in messages; planning default)")
        return label, default, None

    opening = pick("open", "opening", config.DEFAULT_MINUTES["opening"])
    meal = pick("lunch", "lunch", 0) if any("lunch" in k for k in named) \
        else pick("meal", "meal break", config.DEFAULT_MINUTES["meal"])
    closing = pick("clos", "closing", config.DEFAULT_MINUTES["closing"])
    judging_m = d["judging_window"] or 0
    for k in [k for k in named if "judg" in k]:
        judging_m = max(judging_m, named.pop(k)[1])
    breaks = [(f["e"], int(num(f["v"]) or 0), f) for f in v.all("break_min")]
    others = list(named.values())
    fixed = opening[1] + meal[1] + closing[1] + judging_m + sum(b[1] for b in breaks) + sum(o[1] for o in others)
    hacking = total - fixed
    h1 = hacking // 2 if hacking > 0 else 0
    h2 = hacking - h1 if hacking > 0 else 0
    seq = [("Opening", opening[1], opening[2]), ("Hacking (part 1)", h1, None)]
    seq += [(b[0].capitalize(), b[1], b[2]) for b in breaks]
    seq += [(meal[0].capitalize(), meal[1], meal[2])]
    seq += [(o[0].capitalize(), o[1], o[2]) for o in others]
    seq += [("Hacking (part 2)", h2, None), ("Judging", judging_m, None), ("Closing", closing[1], closing[2])]
    st = v.get("start_time")
    start = 0
    if st:
        try:
            hh, mm = str(st["v"]).split(":")[:2]
            start = int(hh) * 60 + int(mm[:2])
        except ValueError:
            st = None
    blocks, t = [], start
    for name, m, f in seq:
        if m <= 0:
            continue
        blocks.append({"name": name, "start": t, "end": t + m, "min": m, "evidence": ev(f)})
        t += m
    fmt = (lambda x: f"{x // 60:02d}:{x % 60:02d}") if st else (lambda x: f"T+{x // 60}:{x % 60:02d}")
    for b in blocks:
        b["time"] = f"{fmt(b['start'])}-{fmt(b['end'])}"
    return {"blocks": blocks, "total_min": t - start, "target_min": total, "hacking_min": max(hacking, 0),
            "meal_min": meal[1], "judging_min": judging_m, "start_min": start, "end_min": t,
            "breaks": [{"name": b[0], "min": b[1], "hard": b[2]["h"], "evidence": ev(b[2])} for b in breaks]}


def judging_plan(d):
    teams, used, mx = d["teams"] or 0, d["judges_used"] or 0, d["max_teams_per_judge"]
    alloc = {}
    for i in range(teams):
        j = (i % used) + 1 if used else None
        if j:
            alloc.setdefault(f"Judge {j}", []).append(f"Team {i + 1}")
    return {"judges_available": d["judges_available"], "judges_needed": d["judges_needed"],
            "judges_used": used, "max_teams_per_judge": mx, "minutes_per_team": d["minutes_per_team"],
            "rounds": d["rounds"], "late_offset_min": d["late_max"], "window_min": d["judging_window"],
            "allocation": alloc}


def budget_plan(v, d, venue, food):
    lines = []
    for f in v.all("expense"):
        lines.append({"item": f["e"], "amount": D(num(f["v"])), "type": "committed", "evidence": ev(f)})
    if venue:
        lines.append({"item": f"Venue: {venue['name']}", "amount": D(venue["price"]), "type": "estimated",
                      "evidence": venue["evidence"]})
    if food:
        lines.append({"item": f"Food: {food['qty']} x {food['name']}", "amount": D(food["cost"]),
                      "type": "estimated", "evidence": food["evidence"]})
    if d["honorarium"] and d["judges_used"]:
        lines.append({"item": f"Judge honorarium: {d['judges_used']} x Rs {int(d['honorarium']):,}",
                      "amount": D(d["honorarium"]) * d["judges_used"], "type": "estimated",
                      "evidence": ev(v.get("honorarium", "judging"))})
    total = sum((l["amount"] for l in lines), Decimal(0))
    cap = D(d["budget_total"]) if d["budget_total"] is not None else None
    remaining = cap - total if cap is not None else None
    optional = []
    for f in v.optional:
        amt = D(num(f["v"]))
        optional.append({"item": f["e"], "amount": amt, "sender": f["sender"], "msg": f["msg"],
                         "affordable": remaining is not None and amt <= remaining,
                         "note": "optional quote, NOT included in total"})
    return {"lines": lines, "committed": sum((l["amount"] for l in lines if l["type"] == "committed"), Decimal(0)),
            "total": total, "budget": cap, "remaining": remaining, "optional": optional}


def build_plan(items):
    """Search venue x food choices (preference order) and return the first plan that validates,
    or the best invalid one with its failing checks."""
    v = View(items)
    v.optional = [f for f in items if f.get("status") == "optional" and num(f["v"]) is not None]
    d = derive(v)
    venues_ok, venues_rej, needs = venue_candidates(v, d)
    foods = food_options(v)
    qty_f = v.get("order_qty", "food")
    attempts, first = [], None
    for food in foods or [None]:
        for venue in venues_ok or [None]:
            plan = assemble(v, d, venue, venues_ok, venues_rej, needs, food, qty_f)
            res = validate(plan, v)
            plan["validation"] = res
            first = first or plan
            attempts.append(plan)
            if res["status"] == "VALID":
                return plan
    # nothing valid: prefer a plan with fewest failures
    return min(attempts, key=lambda p: sum(c["result"] == "FAIL" for c in p["validation"]["checks"])) if attempts else first


def assemble(v, d, venue, venues_ok, venues_rej, needs, food, qty_f):
    dd = dict(d, assumptions=list(d["assumptions"]))
    food_sec = None
    if food:
        qty = int(num(qty_f["v"])) if qty_f else dd["headcount"]
        food_sec = {**food, "qty": qty, "cost": D(qty * food["pph"] + (food["delivery"] or 0)),
                    "people_to_feed": dd["headcount"], "qty_source": ev(qty_f) if qty_f else "computed: headcount",
                    "alternatives": [{"name": f["name"], "pph": f["pph"]} for f in food_options(v) if f["name"] != food["name"]]}
    sched = schedule_plan(v, dd)
    return {
        "summary": {k: dd[k] for k in ("students", "team_size", "teams", "staff", "headcount", "duration_min",
                                        "budget_total", "judges_used")},
        "derived": dd,
        "venue": {"chosen": venue, "required_features": needs,
                  "alternatives": [x for x in venues_ok if venue and x["name"] != venue["name"]],
                  "rejected": venues_rej},
        "schedule": sched,
        "food": food_sec,
        "judging": judging_plan(dd),
        "budget": budget_plan(v, dd, venue, food_sec),
    }
