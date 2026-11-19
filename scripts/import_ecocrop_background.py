"""Import historical FAO attributes for the ten crops, without changing decisions.

One non-empty, original database field becomes one reference record. No missing
values or duplicated sentences are invented to meet a target count. Cotton has
four species in this reference; it remains one crop option in the assessment.
FAO discontinued ECOCROP around 2015: these records need local review before any
promotion into active crop checks. Annual rainfall is not seasonal water supply.
"""

import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "knowledge_base/data/knowledge_facts.json"
SNAPSHOT = "https://raw.githubusercontent.com/OpenCLIM/ecocrop/ea43ecd418fd1a1ea08d32c7dce64b7fae02dec4/EcoCrop_DB.csv"
LOOKUP = "https://raw.githubusercontent.com/OpenCLIM/ecocrop/f13577f4237604b15d85d8e43741714a2d1eb2d4/Ecocrop_variable_lookup.csv"
SPECIES = {
    "Triticum aestivum": "wheat",
    "Oryza sativa": "rice",
    "Zea mays ssp. mays": "maize",
    "Cicer arietinum": "chickpea",
    "Hordeum vulgare": "barley",
    "Gossypium hirsutum": "cotton",
    "Gossypium arboreum": "cotton",
    "Gossypium barbadense": "cotton",
    "Gossypium herbaceum": "cotton",
    "Arachis hypogaea": "groundnut",
    "Sorghum bicolor": "sorghum",
    "Pennisetum glaucum": "pearl_millet",
    "Glycine max": "soybean",
}


def main():
    raw = urlopen(SNAPSHOT, timeout=30).read(2_000_000)
    lookup_raw = urlopen(LOOKUP, timeout=30).read(100_000)
    rows = list(csv.DictReader(io.StringIO(raw.decode("cp1252"))))
    labels = {
        r["Variable"]: r["Explanation"]
        for r in csv.DictReader(io.StringIO(lookup_raw.decode()))
        if r.get("Variable")
    }
    knowledge = json.loads(PATH.read_text())
    knowledge["facts"] = [f for f in knowledge["facts"] if not f.get("historical_reference")]
    knowledge["sources"] = [
        s for s in knowledge["sources"] if not s["source_id"].startswith("SRC_ECOCROP_")
    ]
    found, count = set(), 0
    for row in rows:
        name = row["ScientificName"]
        if name not in SPECIES:
            continue
        found.add(name)
        code, crop = row["EcoPortCode"], SPECIES[name]
        sid = "SRC_ECOCROP_" + code
        knowledge["sources"].append(
            dict(
                source_id=sid,
                organization="FAO ECOCROP",
                title=name + " — historical ecological reference",
                url="https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=" + code,
                review_status="reviewed_for_background_only",
                snapshot_url=SNAPSHOT,
                snapshot_sha256=hashlib.sha256(raw).hexdigest(),
                imported_on="2026-11-15",
                notes="Original fields retained. FAO discontinued this database around 2015. Background only; not locally verified or eligible for crop decisions.",
            )
        )
        for key, value in row.items():
            if (
                key not in labels
                or key in {"AUTH", "FAMNAME", "SYNO", "COMNAME"}
                or value.strip() in {"", "NA"}
            ):
                continue
            unit = (
                "mm/year"
                if key in {"ROPMN", "ROPMX", "RMIN", "RMAX"}
                else (
                    "°C"
                    if key in {"TOPMN", "TOPMX", "TMIN", "TMAX", "KTMP", "KTMPR"}
                    else (
                        "days"
                        if key in {"GMIN", "GMAX"}
                        else "m above sea level" if key == "ALTMX" else None
                    )
                )
            )
            knowledge["facts"].append(
                dict(
                    fact_id=f"ECOCROP_{code}_{key}",
                    crop_id=crop,
                    property="ecocrop_" + key.lower(),
                    category="historical_reference",
                    statement=f"{name}: {labels[key]}.",
                    value=value,
                    unit=unit,
                    source_ids=[sid],
                    applicability={},
                    verification_status="needs_review",
                    confidence="unvalidated_local_context",
                    constraint_eligible=False,
                    historical_reference=True,
                    scientific_name=name,
                    source_column=key,
                    notes="Historical global reference. Not a field recommendation. Rainfall fields describe annual totals, not effective seasonal crop-water supply.",
                )
            )
            count += 1
    if found != set(SPECIES):
        raise ValueError("Some selected species were not present in the pinned snapshot.")
    for crop in knowledge["crops"]:
        facts = [f for f in knowledge["facts"] if f["crop_id"] == crop["crop_id"]]
        crop["fact_ids"] = [f["fact_id"] for f in facts]
        crop["source_ids"] = list(dict.fromkeys(s for f in facts for s in f["source_ids"]))
    knowledge["metadata"].update(
        historical_reference_records=count,
        historical_reference_species=len(found),
        historical_reference_snapshot=SNAPSHOT,
        historical_reference_sha256=hashlib.sha256(raw).hexdigest(),
        version="0.5.0",
    )
    from knowledge_base.validator import validate_knowledge

    errors = validate_knowledge(knowledge)
    if errors:
        raise ValueError(errors)
    PATH.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2) + "\n")
    print(
        f"Imported {count} original background fields; {len(knowledge['facts'])} total knowledge records. Active crop checks unchanged."
    )


if __name__ == "__main__":
    main()
