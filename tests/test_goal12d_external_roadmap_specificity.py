from pathlib import Path


def test_goal12d_external_roadmap_is_goal_specific():
    text = Path("docs/EXTERNAL_REFERENCE_GOAL_BY_GOAL_ADOPTION_PLAN.md").read_text(encoding="utf-8")
    for phrase in [
        "Goal 12D",
        "optlib-master.zip: formula parity and edge-case validation inspiration",
        "quant-traderr-lab-main.zip: diagnostics validation concept",
        "OpenAlice-master.zip: review queue and artifact workflow concept",
        "OpenStock-main.zip: report/watchlist/case workflow UX concept",
        "Goal 13",
        "tensortrade-master.zip: action-less simulation architecture",
        "QuantDinger-main.zip: strategy lifecycle monitoring UX",
        "Kronos-master.zip: model artifact governance / forecast caveat schema only",
        "Goal 14",
        "OpenBB-develop.zip: optional provider capability expansion only",
    ]:
        assert phrase in text
    assert text.count("future-review-required") < 8
