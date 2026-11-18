"""Deterministic checks. The model never decides validity.
Status: any FAIL -> INVALID; else any UNRESOLVED -> NEEDS CLARIFICATION; else VALID."""
import config
from facts import norm, num

OPS = {
    "eq": lambda a, b: a == b, "ne": lambda a, b: a != b,
    "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b, "gte": lambda a, b: a >= b,
    "within": lambda a, b: b[0] <= a <= b[1],
    "requires": lambda a, b: any(norm(b) in norm(x) for x in a),
    "excludes": lambda a, b: not any(norm(b) in norm(x) for x in a),
}
OP_ALIASES = {"equals": "eq", "not_equals": "ne", "less_than": "lt", "less_than_or_equal": "lte",
              "greater_than": "gt", "greater_than_or_equal": "gte", "within_interval": "within",
              "<": "lt", "<=": "lte", ">": "gt", ">=": "gte", "==": "eq", "!=": "ne"}


def metrics(plan):
    d, s, b = plan["derived"], plan["schedule"], plan["budget"]
    venue, food = plan["venue"]["chosen"], plan["food"]
    return {
        "headcount": d["headcount"], "students": d["students"], "teams": d["teams"], "staff": d["staff"],
        "judges_used": d["judges_used"], "judges_available": d["judges_available"],
        "teams_per_judge_max": max((len(t) for t in plan["judging"]["allocation"].values()), default=0),
        "judging_window_min": s["judging_min"], "hacking_min": s["hacking_min"], "meal_min": s["meal_min"],
        "event_min": s["total_min"], "start_min": s["start_min"], "end_min": s["end_min"],
        "venue_capacity": venue["capacity"] if venue else None, "venue_cost": venue["price"] if venue else None,
        "venue_features": venue["features"] if venue else [],
        "food_qty": food["qty"] if food else None, "food_cost": float(food["cost"]) if food else None,
        "food_price_per_head": food["pph"] if food else None,
        "honorarium_total": float(sum(l["amount"] for l in b["lines"] if "honorarium" in l["item"].lower())),
        "committed_cost": float(b["committed"]), "total_cost": float(b["total"]),
        "budget": float(b["budget"]) if b["budget"] is not None else None,
        "remaining_budget": float(b["remaining"]) if b["remaining"] is not None else None,
        "schedule_blocks": [x["name"] for x in s["blocks"]],
    }


METRIC_NAMES = {"headcount", "students", "teams", "staff", "judges_used", "judges_available", "teams_per_judge_max",
                "judging_window_min", "hacking_min", "meal_min", "event_min", "start_min", "end_min",
                "venue_capacity", "venue_cost", "venue_features", "food_qty", "food_cost", "food_price_per_head",
                "honorarium_total", "committed_cost", "total_cost", "budget", "remaining_budget", "schedule_blocks"}


def checkable(c):
    """Can the generic evaluator run this constraint record at all?"""
    return isinstance(c, dict) and c.get("m") in METRIC_NAMES and \
        OP_ALIASES.get(str(c.get("op")), str(c.get("op"))) in OPS


def eval_constraint(c, m):
    """Generic constraint record {m, op, v}. Returns (result, detail)."""
    if not isinstance(c, dict) or not c.get("m"):
        return "UNRESOLVED", "no machine-checkable form"
    op = OP_ALIASES.get(str(c.get("op")), str(c.get("op")))
    if c["m"] not in m or op not in OPS:
        return "UNRESOLVED", f"unknown metric/operator {c.get('m')}/{c.get('op')}"
    actual, target = m[c["m"]], c.get("v")
    if actual is None:
        return "UNRESOLVED", f"{c['m']} not known yet"
    if op not in ("requires", "excludes"):
        target = [num(x) for x in target] if op == "within" and isinstance(target, list) else num(target)
        if target is None or (isinstance(target, list) and None in target):
            return "UNRESOLVED", f"bad target {c.get('v')}"
    try:
        ok = OPS[op](actual, target)
    except (TypeError, IndexError):
        return "UNRESOLVED", f"cannot compare {c['m']}={actual} {op} {c.get('v')}"
    return ("PASS" if ok else "FAIL"), f"{c['m']}={actual} {op} {c.get('v')}"


def validate(plan, view):
    d, s, b = plan["derived"], plan["schedule"], plan["budget"]
    venue, food, j = plan["venue"]["chosen"], plan["food"], plan["judging"]
    checks = []

    def add(name, area, result, detail):
        checks.append({"name": name, "area": area, "result": result, "detail": detail})

    # 1. correct figures
    probs = []
    if d["teams"] and d["team_size"] and d["teams"] * d["team_size"] < d["students"]:
        probs.append("teams do not hold all students")
    if food and food["qty"] < d["headcount"]:
        probs.append(f"food for {food['qty']} but {d['headcount']} people must eat "
                     f"({d['students']} students + {d['staff']} staff + {d['judges_used']} judges)")
    if d["students"] is None:
        add("correct figures", "food", "UNRESOLVED", "student count unknown")
    elif not probs and food and food.get("diet_issues"):
        add("correct figures", "food", "UNRESOLVED", "; ".join(food["diet_issues"]))
    else:
        add("correct figures", "food", "FAIL" if probs else "PASS",
            "; ".join(probs) or f"headcount {d['headcount']}, teams {d['teams']}, food qty {food['qty'] if food else '-'}")
    # 2. within budget
    if b["budget"] is None:
        add("within budget", "budget", "UNRESOLVED", "no budget stated")
    else:
        res_ = b.get("reserve") or 0
        over = b["total"] + res_ > b["budget"]
        detail = (f"total Rs {b['total']:,}" + (f" + reserve Rs {res_:,}" if res_ else "")
                  + f" vs budget Rs {b['budget']:,} (remaining Rs {b['remaining']:,})")
        if not over and b.get("issues"):
            add("within budget", "budget", "UNRESOLVED", "; ".join(b["issues"]))
        else:
            add("within budget", "budget", "FAIL" if over else "PASS", detail)
    # 3. venue fits
    if not venue:
        why = "; ".join(f"{r['name']}: {r['reason']}" for r in plan["venue"]["rejected"]) or "no venue options"
        add("venue fits", "venue", "FAIL" if plan["venue"]["rejected"] else "UNRESOLVED", why)
    else:
        add("venue fits", "venue", "PASS" if venue["capacity"] >= d["headcount"] else "FAIL",
            f"{venue['name']} seats {int(venue['capacity'])} >= headcount {d['headcount']}")
    # 4. schedule valid
    sp = []
    if not s["target_min"]:
        add("schedule valid", "schedule", "UNRESOLVED", "event length unknown")
    else:
        if s["total_min"] != s["target_min"]:
            sp.append(f"blocks sum {s['total_min']} != {s['target_min']} min")
        if s["hacking_min"] < config.MIN_HACKING_MINUTES:
            sp.append(f"only {s['hacking_min']} min left for hacking")
        if d["judging_window"] and s["judging_min"] < d["judging_window"]:
            sp.append("judging block shorter than needed")
        names = [x["name"].lower() for x in s["blocks"]]
        for br in s["breaks"]:
            if br["hard"] and br["name"].lower() not in names:
                sp.append(f"missing required break {br['name']}")
        issues = s.get("issues") or {}
        sp += issues.get("fail", [])
        if not sp and issues.get("unresolved"):
            add("schedule valid", "schedule", "UNRESOLVED", "; ".join(issues["unresolved"]))
        else:
            add("schedule valid", "schedule", "FAIL" if sp else "PASS",
            "; ".join(sp) or f"{len(s['blocks'])} blocks = {s['total_min']} min; breaks: "
            + (", ".join(f"{x['name']} {x['min']}m" for x in s["breaks"]) or "none required"))
    # 5. enough judges
    if not d["judges_available"] or not d["teams"]:
        add("enough judges", "judging", "UNRESOLVED", "judge count or team count unknown")
    else:
        mx = d["max_teams_per_judge"]
        need = d["judges_needed"] or 0
        load = max((len(t) for t in j["allocation"].values()), default=0)
        ok = d["judges_available"] >= need and (not mx or load <= mx)
        add("enough judges", "judging", "PASS" if ok else "FAIL",
            f"need {need}, available {int(d['judges_available'])}, using {d['judges_used']}, "
            f"max load {load} teams" + (f" (limit {int(mx)})" if mx else ""))
    # 6. all areas covered
    gaps = [a for a, ok in (("venue", venue), ("schedule", s["blocks"]), ("food", food),
                            ("judging", j["allocation"]), ("budget", b["budget"] is not None)) if not ok]
    add("all areas covered", "budget", "UNRESOLVED" if gaps else "PASS",
        f"missing: {', '.join(gaps)}" if gaps else "venue, schedule, food, judging, budget")
    # stated hard rules (generic evaluator)
    m = metrics(plan)
    for f in view.all("rule"):
        res, detail = eval_constraint(f.get("c"), m)
        if not f["h"] and res == "UNRESOLVED":
            res = "NOTED"
        add(f"rule: {f['q'][:70]}", f["a"] if f["a"] in ("venue", "schedule", "food", "judging", "budget") else "budget",
            res, f"{detail} [{f['msg']}]")
    results = [c["result"] for c in checks]
    status = "INVALID" if "FAIL" in results else ("NEEDS CLARIFICATION" if "UNRESOLVED" in results else "VALID")
    return {"status": status, "checks": checks}
