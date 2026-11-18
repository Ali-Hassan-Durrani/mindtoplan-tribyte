from decimal import Decimal

from conftest import base_pack, item
from facts import parse_date, resolve
from planner import build_plan
from reader import split_messages
from validate import eval_constraint


def plan_of(items):
    resolve(items)
    return build_plan(items)


def test_derived_figures_and_choices():
    p = plan_of(base_pack())
    d = p["derived"]
    assert d["teams"] == 23 and d["judges_used"] == 6
    assert d["headcount"] == 90 + 6 + 6                       # students + staff + judges used
    assert p["venue"]["chosen"]["name"] == "Auditorium"        # Lab 1 seats 100 < 102
    assert any("100 < headcount 102" in r["reason"] for r in p["venue"]["rejected"])
    assert p["food"]["name"] == "regular meal" and p["food"]["qty"] == 102
    assert p["budget"]["total"] == Decimal(60000 + 200000 + 102 * 900 + 3000 + 6 * 4000)
    assert p["validation"]["status"] == "VALID"


def test_schedule_sums_to_event_and_keeps_break():
    s = plan_of(base_pack())["schedule"]
    assert s["total_min"] == 180
    assert "Tea break" in [b["name"] for b in s["blocks"]]
    assert s["judging_min"] == 40                              # ceil(23/6)=4 rounds x 10 min


def test_late_judge_extends_judging_window():
    items = base_pack() + [item("judging", "late_min", 15, e="one judge", sender="A judge", role="individual")]
    assert plan_of(items)["schedule"]["judging_min"] == 55


def test_over_budget_falls_back_to_cheaper_food():
    items = base_pack()
    for i in items:
        if i["k"] == "budget_total":
            i["v"] = 340000
    p = plan_of(items)
    assert p["food"]["name"] == "snack pack" and p["validation"]["status"] == "VALID"


def test_too_few_judges_is_invalid():
    items = base_pack()
    for i in items:
        if i["k"] == "judges_available":
            i["v"] = 4
    p = plan_of(items)
    assert p["validation"]["status"] == "INVALID"


def test_required_feature_changes_venue():
    items = base_pack() + [
        item("venue", "capacity", 150, e="Hall Z", sender="Campus Venues", role="vendor"),
        item("venue", "price", 90000, e="Hall Z", sender="Campus Venues", role="vendor"),
        item("venue", "feature", "wheelchair ramp", e="Auditorium", sender="Campus Venues", role="vendor"),
        item("venue", "requires_feature", "wheelchair ramp", e="need", h=True)]
    p = plan_of(items)
    assert p["venue"]["chosen"]["name"] == "Auditorium"
    assert any("lacks required" in r["reason"] for r in p["venue"]["rejected"])


def test_generic_rule_new_kind():
    # an unseen kind of constraint: event must end by 17:00
    items = base_pack() + [item("event", "start_time", "14:30"),
                           item("schedule", "rule", None, t="rule", h=True, q="must finish by 5pm",
                                c={"m": "end_min", "op": "lte", "v": 17 * 60})]
    p = plan_of(items)
    rule = [c for c in p["validation"]["checks"] if c["name"].startswith("rule")][0]
    assert rule["result"] == "FAIL" and p["validation"]["status"] == "INVALID"


def test_unhandled_hard_rule_never_valid():
    items = base_pack() + [item("venue", "rule", None, t="rule", h=True, q="no pets near the stage")]
    p = plan_of(items)
    assert p["validation"]["status"] == "NEEDS CLARIFICATION"


def test_eval_constraint_ops():
    m = {"headcount": 100, "venue_features": ["generator", "ac"]}
    assert eval_constraint({"m": "headcount", "op": "lte", "v": 120}, m)[0] == "PASS"
    assert eval_constraint({"m": "headcount", "op": "within", "v": [10, 50]}, m)[0] == "FAIL"
    assert eval_constraint({"m": "venue_features", "op": "requires", "v": "generator"}, m)[0] == "PASS"
    assert eval_constraint({"m": "venue_features", "op": "excludes", "v": "ac"}, m)[0] == "FAIL"
    assert eval_constraint({"m": "mystery", "op": "eq", "v": 1}, m)[0] == "UNRESOLVED"


def test_superseding_needs_authority():
    items = base_pack() + [item("event", "budget_total", 2000000, t="update", sender="Coding club",
                                role="student", msg="T2", order=999)]
    resolve(items)
    bad = items[-1]
    assert bad["status"] == "rejected" and "lacks authority" in bad["reason"]
    assert build_plan(items)["derived"]["budget_total"] == 900000


def test_vendor_can_update_own_price_and_suggestion_not_spent():
    items = base_pack() + [
        item("food", "price_per_head", 950, e="regular meal", t="update", sender="Biryani Point", role="vendor",
             order=999),
        item("budget", "optional_cost", 70000, e="photo booth", t="suggestion", sender="Coding club",
             role="student")]
    p = plan_of(items)
    assert p["food"]["pph"] == 950
    assert p["budget"]["optional"][0]["item"] == "photo booth"
    assert all("photo" not in line["item"] for line in p["budget"]["lines"])


def test_parse_date_and_split():
    assert parse_date("3 Dec") == (12, 3) and parse_date("Jan 15") == (1, 15) and parse_date("") is None
    text = "Msg 1\n\nhello there.\n\n---\nHall A closed\n\n\nThird one!"
    assert split_messages(text) == ["Msg 1\nhello there.", "Hall A closed", "Third one!"]


def test_global_fact_cannot_be_changed_by_relabelling():
    # a student claim labelled with a different area/entity must still hit the authority check
    items = base_pack() + [item("budget", "budget_total", 2500000, e="event", t="update", sender="Coding club",
                                role="student", msg="T9", order=999)]
    resolve(items)
    assert items[-1]["status"] == "rejected" and "lacks authority" in items[-1]["reason"]
    assert build_plan(items)["derived"]["budget_total"] == 900000


def test_claim_about_core_fact_is_rejected_not_applied():
    items = base_pack() + [item("event", "students", 300, t="suggestion", sender="Someone", role="individual")]
    resolve(items)
    assert items[-1]["status"] == "rejected" and "not a confirmed fact" in items[-1]["reason"]
    assert build_plan(items)["derived"]["students"] == 90


def test_magnitude_check_rejects_unit_error():
    items = base_pack() + [item("venue", "price", 200, e="Auditorium", t="update", sender="Campus Venues",
                                role="vendor", msg="T7", order=999)]
    resolve(items)
    assert items[-1]["status"] == "rejected" and "magnitude check" in items[-1]["reason"]
    assert build_plan(items)["venue"]["chosen"]["price"] == 200000


def test_normal_correction_passes_magnitude_check():
    items = base_pack() + [item("venue", "price", 230000, e="Auditorium", t="update", sender="Campus Venues",
                                role="vendor", msg="T8", order=999)]
    resolve(items)
    assert items[-1]["status"] == "accepted"
