"""Check nutrient balance, source applicability and the saved-page entry point."""

from datetime import date
from itertools import product

import pytest

from cropnova.fertilizer.fertilizer_adviser import ACRES_PER_HECTARE, advise, combinations
from tests.test_multipage import request, saved
from cropnova.reports.report_store import load_report


PROFILE = {"region": {"state": "Punjab", "district": "Ludhiana"}, "season": "rabi"}
CROPS = [
    {"id": "wheat", "name": "Wheat", "status": "feasible", "label": "Matches checked conditions"}
]
VALUES = {
    "crop": "wheat",
    "area": "2",
    "area_unit": "acre",
    "scope": "planning",
    "basis": "pau",
    "irrigated": "yes",
    "sowing": "timely",
    "organic_carbon": "0.3",
    "phosphorus": "medium",
    "potassium": "low",
    "special_management": "none",
    "rotation": "other",
    "products_confirm": "yes",
    "use_urea": "yes",
    "use_dap": "yes",
    "use_ssp": "yes",
    "use_mop": "yes",
}


def test_source_rules_and_cross_product_nitrogen_are_used():
    result = advise(PROFILE, CROPS, VALUES)
    assert result["target"] == pytest.approx((59.8, 25, 12))
    assert len(result["plans"]) == 2
    dap = result["plans"][0]
    assert dap["amounts"]["dap"] == pytest.approx(25 / 0.46)
    assert dap["amounts"]["urea"] == pytest.approx((59.8 - 25 / 0.46 * 0.18) / 0.46)
    assert dap["amounts"]["mop"] == 20
    assert result["plans"][1]["amounts"]["urea"] > dap["amounts"]["urea"]
    assert all(plan["delivered"] == pytest.approx(result["target"]) for plan in result["plans"])


@pytest.mark.parametrize(
    "oc,category,phosphate",
    [
        (".399", "medium", 25),
        (".4", "medium", 18.75),
        (".6", "high", 12.5),
        (".601", "high", 0),
        (".8", "low", 31.25),
        (".2", "very_high", 0),
    ],
)
def test_pau_phosphorus_table_boundaries(oc, category, phosphate):
    result = advise(PROFILE, CROPS, {**VALUES, "organic_carbon": oc, "phosphorus": category})
    assert result["target"][1] == phosphate


def test_potassium_requires_deficiency_and_specific_district():
    profile = {**PROFILE, "region": {"state": "Punjab", "district": "Rupnagar"}}
    assert advise(profile, CROPS, VALUES)["target"][2] == 24
    assert advise(profile, CROPS, {**VALUES, "potassium": "adequate"})["target"][2] == 0
    with pytest.raises(ValueError, match="district"):
        advise({**PROFILE, "region": {"state": "Punjab"}}, CROPS, VALUES)


@pytest.mark.parametrize(
    "updates",
    [
        {"organic_carbon": ""},
        {"organic_carbon": "nan"},
        {"area": "inf"},
        {"area": "-2"},
        {"irrigated": "no"},
        {"sowing": "late"},
        {"special_management": "organic"},
        {"potassium": "unknown"},
        {"scope": ""},
        {"products_confirm": ""},
        {"phosphorus": "high", "rotation": "maize_wheat"},
    ],
)
def test_missing_or_unsupported_context_never_generates_a_dose(updates):
    with pytest.raises(ValueError):
        advise(PROFILE, CROPS, {**VALUES, **updates})


def test_source_is_not_transferred_to_a_different_region_or_unresolved_crop():
    with pytest.raises(ValueError, match="Punjab"):
        advise({**PROFILE, "region": {"state": "Haryana"}}, CROPS, VALUES)
    with pytest.raises(ValueError, match="open field checks"):
        advise(PROFILE, [{**CROPS[0], "status": "unknown"}], VALUES)


def test_soil_card_unit_conversion_preserves_total_field_requirement():
    values = {
        **VALUES,
        "basis": "card",
        "dose_n": "100",
        "dose_p": "40",
        "dose_k": "20",
        "dose_unit": "hectare",
        "area_unit": "hectare",
        "test_date": "2026-01-01",
        "authority": "Local soil laboratory",
        "card_confirm": "yes",
    }
    result = advise(PROFILE, CROPS, values)
    assert result["target"] == pytest.approx(
        (100 / ACRES_PER_HECTARE, 40 / ACRES_PER_HECTARE, 20 / ACRES_PER_HECTARE)
    )
    assert tuple(x * result["acres"] for x in result["target"]) == pytest.approx((200, 80, 40))
    assert result["source"]["url"] == ""
    with pytest.raises(ValueError, match="recommended"):
        advise(PROFILE, CROPS, {**values, "card_confirm": ""})
    with pytest.raises(ValueError, match="future"):
        advise(PROFILE, CROPS, {**values, "test_date": "2999-01-01"})


def test_constraint_search_never_oversupplies_nitrogen_or_uses_unavailable_products():
    assert combinations((1, 25, 0), {"urea", "dap"}) == []
    for target in product((0, 10, 50), repeat=3):
        for plan in combinations(target, {"urea", "dap", "ssp", "mop"}):
            assert all(x >= 0 for x in plan["amounts"].values())
            assert plan["delivered"] == pytest.approx(target)
    assert combinations((50, 25, 12), {"urea", "dap"}) == []


def test_fertilizer_form_saves_new_plan_and_preserves_existing_assessment(tmp_path, monkeypatch):
    monkeypatch.setattr("cropnova.reports.report_store.DATABASE_PATH", tmp_path / "reports.sqlite3")
    base, before = saved()  # Haryana wheat uses the soil-card option.
    form = request(base + "/fertilizer")
    assert form["status"] == "200 OK"
    assert b"fertilizer already applied" not in form["body"].lower()
    assert b"Fertilizer adviser" in form["body"]
    invalid = request(base + "/fertilizer", "POST", VALUES)
    assert invalid["status"] == "422 Unprocessable Entity"
    values = {
        **VALUES,
        "basis": "card",
        "dose_n": "50",
        "dose_p": "25",
        "dose_k": "0",
        "dose_unit": "acre",
        "test_date": "2026-01-01",
        "authority": "<script>Lab</script>",
        "card_confirm": "yes",
    }
    response = request(base + "/fertilizer", "POST", values)
    assert response["status"] == "303 See Other"
    new_page = response["headers"]["Location"]
    assert new_page != base + "/fertilizer"
    result = request(new_page)
    assert b"Your seasonal nutrient plan" in result["body"]
    assert b"Why these quantities were chosen" in result["body"]
    assert b"<script>Lab</script>" not in result["body"]
    assert result["headers"]["X-Robots-Tag"].startswith("noindex")
    assert load_report(base.rsplit("/", 1)[-1]) == before
    assert request("/assessment/invalid/fertilizer", "POST", values)["status"] == "404 Not Found"
