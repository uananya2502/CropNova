"""Source-backed wheat rules and a small fertilizer-combination constraint search.

PAU rates apply to Punjab. Soil-test quantities and fertilizer nutrient doses have
different meanings, so we use the laboratory's categories rather than subtracting
available soil nutrients from a fertilizer target. No language model invents doses.
"""

from datetime import date, datetime
from math import isfinite
from zoneinfo import ZoneInfo

SOURCE = {
    "title": "PAU Package of Practices for Crops of Punjab, Rabi 2025-26",
    "url": "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf",
    "sections": "Wheat pp. 9-10; soil-test guidance pp. 106-108, Tables 1-2; Appendix IV p. 160",
}
PRODUCTS = {
    "urea": {"name": "Urea", "nutrients": (0.46, 0, 0)},
    "dap": {"name": "DAP", "nutrients": (0.18, 0.46, 0)},
    "ssp": {"name": "Single superphosphate (SSP)", "nutrients": (0, 0.16, 0)},
    "mop": {"name": "Muriate of potash (MOP)", "nutrients": (0, 0, 0.60)},
}
ACRES_PER_HECTARE = 2.4710538147
# Printed p. 9 lists these districts for the 24 kg K2O/acre rate.
HIGH_K_DISTRICTS = {
    "gurdaspur",
    "hoshiarpur",
    "rupnagar",
    "roopnagar",
    "ropar",
    "shaheed bhagat singh nagar",
    "sbs nagar",
    "nawanshahr",
}
PHOSPHORUS_FACTORS = {
    "low_oc": {"low": 1.25, "medium": 1, "high": 0.75, "very_high": 0},
    "medium_oc": {"low": 1.25, "medium": 0.75, "high": 0.5, "very_high": 0},
    "high_oc": {"low": 1.25, "medium": 0.5, "high": 0, "very_high": 0},
}


def number(values, key, low, high, label):
    raw = values.get(key, "")
    try:
        value = float(raw)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f"Enter {label}.") from None
    if isinstance(raw, bool) or not isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label.capitalize()} must be between {low:g} and {high:g}.")
    return value


def rule(rule_id, reason):
    return {"id": rule_id, "reason": reason}


def wheat_requirement(profile, values):
    """Apply PAU's explicit soil-test table, retaining conditions and fired rules."""
    state = str(profile.get("region", {}).get("state", "")).strip().casefold()
    if state != "punjab" or profile.get("season") != "rabi":
        raise ValueError(
            "The published wheat guide covers Punjab in Rabi. Use the soil-card recommendation option for this field."
        )
    if values.get("irrigated") != "yes":
        raise ValueError(
            "This guide covers irrigated wheat. Confirm irrigation or use a local soil-card recommendation."
        )
    if values.get("sowing") != "timely":
        raise ValueError(
            "This built-in guide covers timely-sown wheat. For late sowing, use a local crop-specific recommendation."
        )
    if values.get("special_management") != "none":
        raise ValueError(
            "Manure, legume rotations, long-term straw retention or salt-affected soil can change the dose. Use the crop-specific recommendation from your soil adviser."
        )
    oc = number(values, "organic_carbon", 0, 10, "soil organic carbon percentage")
    phosphorus = values.get("phosphorus")
    potassium = values.get("potassium")
    if phosphorus not in {"low", "medium", "high", "very_high"}:
        raise ValueError("Select the phosphorus category printed on your soil test.")
    if potassium not in {"low", "adequate"}:
        raise ValueError("Select the potassium category printed on your soil test.")
    # Table 1 supplies urea-equivalent rates of 130/110/90 kg/acre.
    # Use the explicit medium-soil N target of 50 kg/acre from the wheat chapter.
    if oc < 0.4:
        nitrogen = 130 * 0.46
    elif oc <= 0.75:
        nitrogen = 50
    else:
        nitrogen = 90 * 0.46
    trace = [
        rule(
            "WHEAT_N_OC",
            f"Organic carbon {oc:g}% selects the PAU nitrogen category. The seasonal nitrogen target is {nitrogen:g} kg N/acre.",
        )
    ]
    if oc < 0.4:
        oc_group = "low_oc"
    elif oc <= 0.6:
        oc_group = "medium_oc"
    else:
        oc_group = "high_oc"
    factor = PHOSPHORUS_FACTORS[oc_group][phosphorus]
    phosphate = 25 * factor
    trace.append(
        rule(
            "WHEAT_P_OC",
            f'Table 2 combines {phosphorus.replace("_", " ")} soil phosphorus and {oc:g}% organic carbon. Apply {factor:g} times the 25 kg P₂O₅/acre reference.',
        )
    )
    if values.get("rotation") == "maize_wheat" and phosphorus == "high":
        raise ValueError(
            "For maize–wheat fields, PAU changes phosphorus guidance above 16 kg P/acre. Ask your soil adviser for the precise dose and use the soil-card option."
        )
    if values.get("rotation") not in {"other", "maize_wheat"}:
        raise ValueError("Select the cropping sequence so the phosphorus rule can be checked.")
    district = str(profile.get("region", {}).get("district", "")).strip().casefold()
    if potassium == "low" and not district:
        raise ValueError(
            "Add your district to the field assessment before calculating potassium for deficient soil."
        )
    potash = 0
    if potassium == "low":
        potash = 24 if district in HIGH_K_DISTRICTS else 12
    trace.append(
        rule(
            "WHEAT_K_TEST",
            f"Soil potassium is {potassium}. The matching district rule gives {potash:g} kg K₂O/acre.",
        )
    )
    return (nitrogen, phosphate, potash), trace, SOURCE


def combinations(target, available):
    """Enumerate phosphorus carriers and solve the nutrient balance for each.

    All three nutrient constraints must match. DAP contributes nitrogen, so
    residual N can become negative: reject that alternative instead of oversupplying.
    """
    nitrogen, phosphate, potash = target
    carriers = ["dap", "ssp"] if phosphate else [None]
    plans = []
    for carrier in carriers:
        if carrier and carrier not in available:
            continue
        amounts = {product: 0.0 for product in PRODUCTS}
        if carrier:
            amounts[carrier] = phosphate / PRODUCTS[carrier]["nutrients"][1]
        remaining_n = nitrogen - amounts["dap"] * 0.18
        if remaining_n < -1e-8:
            continue
        amounts["urea"] = max(0, remaining_n) / 0.46
        amounts["mop"] = potash / 0.60
        if any(amount > 1e-8 and product not in available for product, amount in amounts.items()):
            continue
        delivered = tuple(
            sum(amounts[p] * PRODUCTS[p]["nutrients"][i] for p in PRODUCTS) for i in range(3)
        )
        if all(abs(wanted - actual) < 1e-6 for wanted, actual in zip(target, delivered)):
            plans.append({"carrier": carrier, "amounts": amounts, "delivered": delivered})
    return plans


def advise(profile, candidates, values):
    """Return a complete seasonal plan or a targeted explanation of missing inputs."""
    crop_id = values.get("crop", "")
    crop = next((crop for crop in candidates if crop["id"] == crop_id), None)
    if not crop:
        raise ValueError("Choose a crop included in this field assessment.")
    area = number(values, "area", 0.01, 10000, "field area")
    unit = values.get("area_unit")
    if unit not in {"acre", "hectare"}:
        raise ValueError("Choose acres or hectares for field area.")
    acres = area * (ACRES_PER_HECTARE if unit == "hectare" else 1)
    if values.get("scope") != "planning":
        raise ValueError("Confirm that you are planning fertilizer for the upcoming crop.")
    if crop["status"] != "feasible":
        raise ValueError(
            "Resolve this crop’s open field checks or shortfall before planning fertilizer. Update the field assessment and try again."
        )
    basis = values.get("basis")
    if basis == "pau":
        if crop_id != "wheat":
            raise ValueError(
                "The published built-in guide currently covers wheat. Choose your soil-card recommendation for this crop."
            )
        target, trace, source = wheat_requirement(profile, values)
    elif basis == "card":
        if values.get("card_confirm") != "yes":
            raise ValueError(
                "Confirm that these are crop-specific fertilizer doses recommended by the lab, rather than soil nutrient measurements."
            )
        raw_date = values.get("test_date", "")
        try:
            test_date = date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            raise ValueError("Enter the date on the soil-test recommendation.") from None
        if test_date > datetime.now(ZoneInfo("Asia/Kolkata")).date():
            raise ValueError("The soil-test recommendation date cannot be in the future.")
        authority = str(values.get("authority", "")).strip()
        if not authority or len(authority) > 120:
            raise ValueError(
                "Enter the laboratory or adviser named on the recommendation, within 120 characters."
            )
        dose_unit = values.get("dose_unit")
        if dose_unit not in {"acre", "hectare"}:
            raise ValueError("Choose the recommendation’s units.")
        target = tuple(
            number(values, key, 0, 1000, label)
            for key, label in (
                ("dose_n", "recommended nitrogen dose"),
                ("dose_p", "recommended P₂O₅ dose"),
                ("dose_k", "recommended K₂O dose"),
            )
        )
        if dose_unit == "hectare":
            target = tuple(value / ACRES_PER_HECTARE for value in target)
        trace = [
            rule(
                "CARD_DOSE",
                f"Using the crop-specific recommendation entered from {authority}, dated {test_date}. Values are fertilizer nutrient doses.",
            )
        ]
        source = {
            "title": authority,
            "sections": f"Farmer-entered crop recommendation dated {test_date}; document not independently verified",
            "url": "",
        }
    else:
        raise ValueError("Choose a recommendation source.")
    if values.get("products_confirm") != "yes":
        raise ValueError(
            "Confirm which fertilizers you can obtain and their labelled nutrient grades."
        )
    available = {product for product in PRODUCTS if values.get("use_" + product) == "yes"}
    plans = combinations(target, available)
    trace.append(
        rule(
            "NUTRIENT_BALANCE",
            "Compare the available phosphorus carriers, account for nitrogen in DAP, and require each alternative to supply the specified N, P₂O₅ and K₂O.",
        )
    )
    return {
        "crop": crop,
        "acres": acres,
        "area": area,
        "area_unit": unit,
        "target": target,
        "trace": trace,
        "source": source,
        "plans": plans,
        "basis": basis,
    }
