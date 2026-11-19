"""Dropdown choices are input conveniences, not additional agricultural knowledge.

Geography checked against Government of India directory on 15 November 2026.
District lists are included for the two reference states and Punjab. A district
name in this file does not establish district-specific crop guidance.
"""

import math
from cropnova.config.public_profiles import REFERENCE_PROFILES

STATES = sorted(
    [
        "Andaman and Nicobar Islands",
        "Andhra Pradesh",
        "Arunachal Pradesh",
        "Assam",
        "Bihar",
        "Chandigarh",
        "Chhattisgarh",
        "Dadra and Nagar Haveli and Daman and Diu",
        "Delhi",
        "Goa",
        "Gujarat",
        "Haryana",
        "Himachal Pradesh",
        "Jammu and Kashmir",
        "Jharkhand",
        "Karnataka",
        "Kerala",
        "Ladakh",
        "Lakshadweep",
        "Madhya Pradesh",
        "Maharashtra",
        "Manipur",
        "Meghalaya",
        "Mizoram",
        "Nagaland",
        "Odisha",
        "Puducherry",
        "Punjab",
        "Rajasthan",
        "Sikkim",
        "Tamil Nadu",
        "Telangana",
        "Tripura",
        "Uttar Pradesh",
        "Uttarakhand",
        "West Bengal",
    ]
)
DISTRICTS = {
    "Haryana": sorted(
        "Ambala|Bhiwani|Charkhi Dadri|Faridabad|Fatehabad|Gurugram|Hansi|Hisar|Jhajjar|Jind|Kaithal|Karnal|Kurukshetra|Mahendragarh|Nuh|Palwal|Panchkula|Panipat|Rewari|Rohtak|Sirsa|Sonipat|Yamunanagar".split(
            "|"
        )
    ),
    "Rajasthan": sorted(
        "Ajmer|Alwar|Balotra|Banswara|Baran|Barmer|Beawar|Bharatpur|Bhilwara|Bikaner|Bundi|Chittorgarh|Churu|Dausa|Deeg|Dholpur|Didwana-Kuchaman|Dungarpur|Ganganagar|Hanumangarh|Jaipur|Jaisalmer|Jalore|Jhalawar|Jhunjhunu|Jodhpur|Karauli|Khairthal-Tijara|Kota|Kotputli-Behror|Nagaur|Pali|Phalodi|Pratapgarh|Rajsamand|Salumbar|Sawai Madhopur|Sikar|Sirohi|Tonk|Udaipur".split(
            "|"
        )
    ),
    "Punjab": sorted(
        "Amritsar|Barnala|Bathinda|Faridkot|Fatehgarh Sahib|Fazilka|Ferozepur|Gurdaspur|Hoshiarpur|Jalandhar|Kapurthala|Ludhiana|Malerkotla|Mansa|Moga|Pathankot|Patiala|Rupnagar|S.A.S Nagar|Sangrur|Shahid Bhagat Singh Nagar|Sri Muktsar Sahib|Tarn Taran".split(
            "|"
        )
    ),
}
GEOGRAPHY_SOURCES = [
    "https://igod.gov.in/sg/states",
    "https://igod.gov.in/sg/HR/E042/organizations",
    "https://igod.gov.in/sg/RJ/E042/organizations",
    "https://igod.gov.in/sg/PB/E042/organizations",
    "https://hansi.haryana.gov.in/",
]
TEXTURES = [
    ("unknown", "Not sure yet"),
    ("loamy", "Loamy"),
    ("clayey", "Clayey"),
    ("sandy", "Sandy"),
    ("clay_loam", "Clay loam"),
    ("sandy_loam", "Sandy loam"),
    ("silt_loam", "Silt loam"),
    ("silty_clay_loam", "Silty clay loam"),
    ("other", "Other"),
]


def numeric_choices(selected, *, kind):
    """Preserve an exact saved value, even if it is not a standard menu increment."""
    current = "" if selected is None else str(selected)
    try:
        number = float(current)
    except (ValueError, TypeError, OverflowError):
        number = None
    if kind == "ph":
        values = [step / 10 for step in range(141)]
    else:
        values = list(range(0, 2001, 25)) + [2500, 3000, 4000, 5000, 7500, 10000]
    choices = [("", "Not measured / not sure yet")]
    matched = False
    for value in values:
        is_current = number is not None and math.isfinite(number) and value == number
        key = current if is_current else f"{value:g}"
        label = f"{value:.1f}" if kind == "ph" else f"{value:g} mm"
        choices.append((key, label))
        matched = matched or is_current
    if current and not matched:
        valid = (
            number is not None
            and math.isfinite(number)
            and 0 <= number <= (14 if kind == "ph" else 10000)
        )
        label = (
            current + ("" if kind == "ph" else " mm") + " (saved exact value)"
            if valid
            else current + " (check value)"
        )
        choices.append((current, label))
    return choices


def state_choices(selected=""):
    choices = [("", "Select your state / region")]
    choices += [(state, state) for state in STATES]
    if selected and selected not in STATES:
        choices.append((str(selected), str(selected) + " — saved region"))
    return choices


def district_choices(state="", selected=""):
    # Without JavaScript, grouped labels still allow selection from these states.
    choices = [("", "Not specified (optional)")]
    if state:
        choices += [(district, district) for district in DISTRICTS.get(state, [])]
    else:
        choices += [
            (district, state + " / " + district)
            for state, items in DISTRICTS.items()
            for district in items
        ]
    if selected and not any(key == selected for key, _ in choices):
        choices.append((str(selected), str(selected) + " — saved district"))
    return choices


def submitted_crops(values):
    """Accept the single menu, a preserved multi-crop choice, or legacy checkboxes."""
    if "__all__" in values:
        return []
    return list(
        dict.fromkeys(crop.strip() for value in values for crop in value.split(",") if crop.strip())
    )


def public_options():
    return {
        "districts": DISTRICTS,
        "profiles": REFERENCE_PROFILES,
        "district_note": "District menus are available for Haryana, Rajasthan and Punjab. District is optional; a district name does not add crop-specific evidence.",
    }
