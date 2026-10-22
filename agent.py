"""CropNova intelligent-agent workflow and integration adapters."""

from __future__ import annotations

import importlib
from typing import Any, Iterable, Mapping

from csp_solver import solve_constraints
from explanations import (
    build_evidence_package,
    build_explanations,
    follow_up_question,
)
from knowledge_base.loader import load_knowledge
from knowledge_base.query import find_crop
from knowledge_base.retrieval import get_usable_facts
from knowledge_base.validator import validate_knowledge


RESULT_STATUSES = {
    "FEASIBLE_OPTIONS_FOUND",
    "MORE_INFORMATION_NEEDED",
    "NO_FEASIBLE_OPTION",
    "NO_SUPPORTED_KNOWLEDGE",
    "INVALID_INPUT",
    "SYSTEM_ERROR",
}


ALLOWED = {
    "season": {
        "kharif",
        "rabi",
        "zaid",
        "unknown",
    },
    "soil.texture": {
        "sandy",
        "loamy",
        "clayey",
        "other",
        "unknown",
    },
    "soil.fertility": {
        "low",
        "moderate",
        "high",
        "unknown",
    },
    "water.availability": {
        "low",
        "moderate",
        "high",
        "unknown",
    },
    "water.irrigation": {
        "available",
        "rainfed",
        "limited",
        "unknown",
    },
    "objective": {
        "find_suitable_crop",
        "conserve_water",
        "soil_improvement",
        "compare_alternatives",
    },
}


LIMITATIONS = [
    "CropNova is an educational decision-support prototype, not a guarantee of crop success.",
    "Only applicable facts explicitly marked verified may satisfy a hard constraint.",
    "The prototype does not provide pesticide prescriptions, fertilizer dosage, live weather, market prices, yield, or profit predictions.",
    "Consult a local agricultural extension professional before consequential decisions.",
]


def _text(
    value: Any,
    default: str = "unknown",
) -> str:
    """Convert a value to normalized text."""

    if value is None or not str(value).strip():
        return default

    return str(value).strip()


def normalize_profile(
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Normalize flat or nested user profile input.

    The agent accepts both forms:

        {
            "state": "Haryana",
            "soil_texture": "loamy"
        }

    and:

        {
            "region": {
                "state": "Haryana"
            },
            "soil": {
                "texture": "loamy"
            }
        }
    """

    region = (
        raw.get("region")
        if isinstance(
            raw.get("region"),
            Mapping,
        )
        else {}
    )

    soil = (
        raw.get("soil")
        if isinstance(
            raw.get("soil"),
            Mapping,
        )
        else {}
    )

    water = (
        raw.get("water")
        if isinstance(
            raw.get("water"),
            Mapping,
        )
        else {}
    )

    # ---------------------------------------------
    # Soil pH
    # ---------------------------------------------

    ph_value = soil.get(
        "ph",
        raw.get("soil_ph"),
    )

    try:
        if (
            ph_value is None
            or str(ph_value).strip().casefold()
            in {"", "unknown"}
        ):
            ph = None
        else:
            ph = float(ph_value)

    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid soil pH value: {ph_value}"
        ) from error

    # ---------------------------------------------
    # Candidate IDs
    # ---------------------------------------------

    candidates = raw.get(
        "candidate_ids",
        raw.get(
            "candidates",
            [],
        ),
    )

    if isinstance(
        candidates,
        str,
    ):
        candidates = [
            item.strip()
            for item in candidates.split(",")
            if item.strip()
        ]

    elif not isinstance(
        candidates,
        Iterable,
    ):
        candidates = []

    else:
        candidates = list(candidates)

    # ---------------------------------------------
    # Normalized profile
    # ---------------------------------------------

    return {
        "region": {
            "state": _text(
                region.get(
                    "state",
                    raw.get("state"),
                ),
                "",
            ),
            "district": _text(
                region.get(
                    "district",
                    raw.get("district"),
                ),
                "",
            )
            or None,
        },

        "season": _text(
            raw.get("season")
        ).casefold(),

        "soil": {
            "texture": _text(
                soil.get(
                    "texture",
                    raw.get("soil_texture"),
                )
            ).casefold(),

            "ph": ph,

            "fertility": _text(
                soil.get(
                    "fertility",
                    raw.get("soil_fertility"),
                )
            ).casefold(),
        },

        "water": {
            "availability": _text(
                water.get(
                    "availability",
                    raw.get(
                        "water_availability"
                    ),
                )
            ).casefold(),

            "irrigation": _text(
                water.get(
                    "irrigation",
                    raw.get("irrigation"),
                )
            ).casefold(),
        },

        "objective": _text(
            raw.get("objective"),
            "find_suitable_crop",
        ).casefold(),

        "priority": _text(
            raw.get(
                "priority"
            ),
            "",
        ).casefold()
        or None,

        "candidate_ids": candidates,
    }


def validate_profile(
    profile: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Validate the normalized user profile."""

    errors: list[dict[str, str]] = []

    # ---------------------------------------------
    # State
    # ---------------------------------------------

    state = profile.get(
        "region",
        {},
    ).get("state")

    if not state:
        errors.append(
            {
                "field": "state",
                "code": "REQUIRED",
                "message": (
                    "State or region is required."
                ),
            }
        )

    # ---------------------------------------------
    # Enumerated fields
    # ---------------------------------------------

    checks = {
        "season": profile.get(
            "season"
        ),
        "soil.texture": profile.get(
            "soil",
            {},
        ).get("texture"),
        "soil.fertility": profile.get(
            "soil",
            {},
        ).get("fertility"),
        "water.availability": profile.get(
            "water",
            {},
        ).get("availability"),
        "water.irrigation": profile.get(
            "water",
            {},
        ).get("irrigation"),
        "objective": profile.get(
            "objective"
        ),
    }

    for field, value in checks.items():

        if value not in ALLOWED[field]:
            errors.append(
                {
                    "field": field,
                    "code": "UNSUPPORTED_VALUE",
                    "message": (
                        f"Choose a supported value "
                        f"for {field.replace('.', ' ')}."
                    ),
                }
            )

    # ---------------------------------------------
    # pH
    # ---------------------------------------------

    ph = profile.get(
        "soil",
        {},
    ).get("ph")

    if ph is not None and not 0 <= ph <= 14:
        errors.append(
            {
                "field": "soil.ph",
                "code": "OUT_OF_RANGE",
                "message": (
                    "Soil pH must be between 0 and 14."
                ),
            }
        )

    return errors


# =========================================================
# RULE ENGINE ADAPTER
# =========================================================

def _rule_adapter(
    profile: Mapping[str, Any],
    crops: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Connect the Agent to the Rule Engine.

    The Rule Engine is evaluated independently for each
    crop using that crop's usable verified facts.
    """

    try:
        module = importlib.import_module(
            "rule_engine"
        )

        evaluator = getattr(
            module,
            "evaluate_rules",
        )

    except (
        ImportError,
        AttributeError,
    ):

        return {
            "status": "not_available",
            "candidates": crops,
            "fired_rules": [],
            "rule_results": [],
            "warnings": [
                (
                    "Rule engine is not available; "
                    "knowledge-base candidates were "
                    "passed to the CSP."
                )
            ],
            "missing_information": [],
        }

    rule_results: list[
        dict[str, Any]
    ] = []

    fired_rules: list[
        dict[str, Any]
    ] = []

    warnings: list[str] = []

    missing_information: list[
        dict[str, Any]
    ] = []

    # ---------------------------------------------
    # Evaluate every candidate independently
    # ---------------------------------------------

    for crop in crops:

        crop_id = str(
            crop.get(
                "crop_id",
                "",
            )
        ).strip()

        if not crop_id:
            continue

        crop_facts = crop.get(
            "facts",
            [],
        )

        if not isinstance(
            crop_facts,
            list,
        ):
            crop_facts = []

        # IMPORTANT:
        # crop_id is temporary and is NOT added
        # permanently to the shared user profile.
        rule_profile = dict(profile)
        rule_profile["crop_id"] = crop_id

        evaluation = evaluator(
            rule_profile,
            crop_facts,
        )

        # -----------------------------------------
        # Convert RuleEvaluation to dictionary
        # -----------------------------------------

        if hasattr(
            evaluation,
            "to_dict",
        ):
            evaluation_dict = (
                evaluation.to_dict()
            )

        elif isinstance(
            evaluation,
            Mapping,
        ):
            evaluation_dict = dict(
                evaluation
            )

        else:
            raise TypeError(
                "Rule engine must return "
                "RuleEvaluation or a mapping."
            )

        results = evaluation_dict.get(
            "results",
            [],
        )

        crop_trace = {
            "crop_id": crop_id,
            "results": results,
        }

        rule_results.append(
            crop_trace
        )

        # -----------------------------------------
        # Inspect individual rules
        # -----------------------------------------

        for result in results:

            if not isinstance(
                result,
                Mapping,
            ):
                continue

            status = result.get(
                "status"
            )

            rule_id = result.get(
                "rule_id"
            )

            # -------------------------------------
            # Fired rule
            # -------------------------------------

            if status == "fired":

                fired_rules.append(
                    {
                        "crop_id": crop_id,
                        "rule_id": rule_id,
                        "status": status,
                        "conclusion": result.get(
                            "conclusion",
                            "",
                        ),
                        "explanation": result.get(
                            "explanation",
                            "",
                        ),
                        "fact_ids": result.get(
                            "fact_ids",
                            [],
                        ),
                        "source_ids": result.get(
                            "source_ids",
                            [],
                        ),
                        "reason_codes": result.get(
                            "reason_codes",
                            [],
                        ),
                    }
                )

            # -------------------------------------
            # Unknown rule
            # -------------------------------------

            elif status == "unknown":

                missing_fields = result.get(
                    "missing_fields",
                    [],
                )

                reason_codes = result.get(
                    "reason_codes",
                    [],
                )

                missing_information.append(
                    {
                        "crop_id": crop_id,
                        "rule_id": rule_id,
                        "missing_fields": (
                            missing_fields
                        ),
                        "reason_codes": (
                            reason_codes
                        ),
                    }
                )

                warnings.append(
                    (
                        f"Rule {rule_id} for crop "
                        f"'{crop_id}' could not be "
                        "fully evaluated because "
                        "required information or "
                        "evidence was unknown."
                    )
                )

    # ---------------------------------------------
    # Overall Rule Engine status
    # ---------------------------------------------

    if fired_rules:
        overall_status = "fired"

    elif missing_information:
        overall_status = "unknown"

    else:
        overall_status = "not_fired"

    return {
        "status": overall_status,
        "candidates": crops,
        "fired_rules": fired_rules,
        "rule_results": rule_results,
        "warnings": list(
            dict.fromkeys(
                warnings
            )
        ),
        "missing_information": (
            missing_information
        ),
    }


# =========================================================
# KNOWLEDGE BASE → CANDIDATE ADAPTER
# =========================================================

def _candidate_records(
    knowledge: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """
    Convert knowledge-base crop records into CSP candidates.

    Verified usable facts are attached to every candidate.
    """

    candidates: list[
        dict[str, Any]
    ] = []

    for crop in knowledge.get(
        "crops",
        [],
    ):

        if (
            not isinstance(
                crop,
                Mapping,
            )
            or not crop.get("crop_id")
        ):
            continue

        crop_id = str(
            crop["crop_id"]
        )

        facts = get_usable_facts(
            dict(knowledge),
            crop_id=crop_id,
        )

        candidates.append(
            {
                **dict(crop),

                "candidate_id": crop_id,

                "name": crop.get(
                    "common_name",
                    crop.get(
                        "name",
                        crop_id,
                    ),
                ),

                "category": crop.get(
                    "crop_group",
                    crop.get(
                        "category"
                    ),
                ),

                "verification_status": crop.get(
                    "status",
                    crop.get(
                        "verification_status",
                        "unknown",
                    ),
                ),

                "facts": facts,
            }
        )

    return candidates


# =========================================================
# CANDIDATE SELECTION
# =========================================================

def _select_candidates(
    crops: list[dict[str, Any]],
    selected_ids: list[str],
    rule_result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """
    Select candidates requested by the user.

    The Rule Engine does NOT itself decide suitability.
    It only supplies evidence/traces to the workflow.
    """

    knowledge_view = {
        "crops": crops
    }

    by_id = {
        str(
            crop.get("crop_id")
        ): crop
        for crop in crops
    }

    # ---------------------------------------------
    # Explicit candidate selection
    # ---------------------------------------------

    if selected_ids:

        selected: list[
            dict[str, Any]
        ] = []

        for item in selected_ids:

            item_id = str(item)

            found = find_crop(
                knowledge_view,
                item_id,
            )

            crop = by_id.get(
                item_id
            )

            if (
                crop is None
                and found is not None
            ):
                crop = by_id.get(
                    str(
                        found.get(
                            "crop_id"
                        )
                    )
                )

            if (
                crop is not None
                and crop not in selected
            ):
                selected.append(
                    crop
                )

        return selected

    # ---------------------------------------------
    # Otherwise use all Rule Engine candidates
    # ---------------------------------------------

    candidates = rule_result.get(
        "candidates",
        crops,
    )

    resolved: list[
        dict[str, Any]
    ] = []

    if not isinstance(
        candidates,
        list,
    ):
        candidates = crops

    for item in candidates:

        if isinstance(
            item,
            Mapping,
        ):
            resolved.append(
                dict(item)
            )
            continue

        item_id = str(item)

        found = find_crop(
            knowledge_view,
            item_id,
        )

        crop = by_id.get(
            item_id
        )

        if (
            crop is None
            and found is not None
        ):
            crop = by_id.get(
                str(
                    found.get(
                        "crop_id"
                    )
                )
            )

        if crop:
            resolved.append(
                crop
            )

    return resolved


# =========================================================
# KNOWLEDGE SUMMARY
# =========================================================

def _knowledge_summary(
    knowledge: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a compact knowledge-base summary."""

    crops = [
        item
        for item in knowledge.get(
            "crops",
            [],
        )
        if isinstance(
            item,
            Mapping,
        )
    ]

    top_level_facts = knowledge.get(
        "facts",
        [],
    )

    if (
        isinstance(
            top_level_facts,
            list,
        )
        and top_level_facts
    ):

        facts = [
            fact
            for fact in top_level_facts
            if isinstance(
                fact,
                Mapping,
            )
        ]

    else:

        facts = [
            fact
            for crop in crops
            for fact in crop.get(
                "facts",
                [],
            )
            if isinstance(
                fact,
                Mapping,
            )
        ]

    statuses: dict[
        str,
        int,
    ] = {}

    for fact in facts:

        key = str(
            fact.get(
                "verification_status",
                "unknown",
            )
        ).casefold()

        statuses[key] = (
            statuses.get(
                key,
                0,
            )
            + 1
        )

    verified_count = sum(
        statuses.get(
            key,
            0,
        )
        for key in (
            "verified",
            "verified_general",
            "verified_context_specific",
        )
    )

    return {
        "total_crops": len(
            crops
        ),
        "total_facts": len(
            facts
        ),
        "verified_facts": (
            verified_count
        ),
        "usable_facts": len(
            get_usable_facts(
                dict(knowledge)
            )
        ),
        "fact_status_counts": statuses,
        "total_sources": len(
            knowledge.get(
                "sources",
                [],
            )
        ),
        "dataset_status": knowledge.get(
            "metadata",
            {},
        ).get(
            "status",
            "unknown",
        ),
    }


# =========================================================
# SOURCE RESOLUTION
# =========================================================

def _resolve_evidence_sources(
    knowledge: Mapping[str, Any],
    source_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Resolve source IDs into source records."""

    wanted = set(
        source_ids
    )

    return [
        dict(source)
        for source in knowledge.get(
            "sources",
            [],
        )
        if (
            isinstance(
                source,
                Mapping,
            )
            and source.get(
                "source_id"
            )
            in wanted
        )
    ]


# =========================================================
# CSP UNKNOWN EXTRACTION
# =========================================================

def _missing(
    csp_result: Mapping[str, Any],
) -> list[dict[str, str]]:
    """
    Extract missing information from unknown CSP results.
    """

    result: list[
        dict[str, str]
    ] = []

    seen: set[
        tuple[str, str]
    ] = set()

    for candidate in csp_result.get(
        "unknown_candidates",
        [],
    ):

        for outcome in candidate.get(
            "unknown_constraints",
            [],
        ):

            fields = (
                outcome.get(
                    "missing_fields"
                )
                or [""]
            )

            for field in fields:

                key = (
                    field,
                    outcome.get(
                        "reason_code",
                        "UNKNOWN",
                    ),
                )

                if key in seen:
                    continue

                result.append(
                    {
                        "field": field,
                        "reason_code": outcome.get(
                            "reason_code",
                            "UNKNOWN",
                        ),
                        "message": outcome.get(
                            "reason",
                            "Information is missing.",
                        ),
                    }
                )

                seen.add(key)

    return result


# =========================================================
# FINAL STATUS
# =========================================================

def _status(
    csp_result: Mapping[str, Any],
    missing: list[dict[str, str]],
    rule_result: Mapping[str, Any] | None = None,
    profile: Mapping[str, Any] | None = None,
) -> str:
    """
    Determine the final assessment status.

    Important distinction:

        FEASIBLE_OPTIONS_FOUND
            ↓
        At least one candidate satisfies the CSP.

        MORE_INFORMATION_NEEDED
            ↓
        The user has not supplied information required
        to evaluate the assessment.

        NO_SUPPORTED_KNOWLEDGE
            ↓
        The user has supplied the required information,
        but CropNova's verified knowledge cannot establish
        a supported answer.

        NO_FEASIBLE_OPTION
            ↓
        Candidates were evaluated and none satisfied
        the constraints.
    """

    # --------------------------------------------------
    # 1. Feasible candidate exists
    # --------------------------------------------------

    if csp_result.get(
        "feasible_candidates"
    ):
        return "FEASIBLE_OPTIONS_FOUND"

    # --------------------------------------------------
    # 2. Unknown candidates exist
    # --------------------------------------------------

    if csp_result.get(
        "unknown_candidates"
    ):

        # ----------------------------------------------
        # Determine whether the user's profile is
        # already complete.
        # ----------------------------------------------

        profile_complete = False

        if profile:

            region = profile.get(
                "region",
                {},
            )

            soil = profile.get(
                "soil",
                {},
            )

            water = profile.get(
                "water",
                {},
            )

            required_values = [
                region.get(
                    "state"
                ),
                profile.get(
                    "season"
                ),
                soil.get(
                    "texture"
                ),
                soil.get(
                    "fertility"
                ),
                water.get(
                    "availability"
                ),
                water.get(
                    "irrigation"
                ),
                profile.get(
                    "objective"
                ),
            ]

            profile_complete = all(
                value not in (
                    None,
                    "",
                    "unknown",
                )
                for value in required_values
            )

        # ----------------------------------------------
        # User information is complete.
        #
        # Therefore unresolved candidates indicate
        # insufficient supported knowledge rather than
        # missing user input.
        # ----------------------------------------------

        if profile_complete:
            return "NO_SUPPORTED_KNOWLEDGE"

        # ----------------------------------------------
        # User information is genuinely incomplete.
        # ----------------------------------------------

        if missing:
            return "MORE_INFORMATION_NEEDED"

        return "NO_SUPPORTED_KNOWLEDGE"

    # --------------------------------------------------
    # 3. CSP explicitly reports missing information
    # --------------------------------------------------

    if missing:

        only_knowledge_missing = all(
            item.get(
                "reason_code"
            )
            in {
                "MISSING_VERIFIED_FACT",
                "CONFLICTING_VERIFIED_FACTS",
                "INCOMPATIBLE_VERIFIED_FACTS",
            }
            for item in missing
        )

        if only_knowledge_missing:
            return "NO_SUPPORTED_KNOWLEDGE"

        return "MORE_INFORMATION_NEEDED"

    # --------------------------------------------------
    # 4. Candidates evaluated but none feasible
    # --------------------------------------------------

    return "NO_FEASIBLE_OPTION"


# =========================================================
# MAIN AGENT WORKFLOW
# =========================================================

def run_assessment(
    user_profile: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Execute the complete CropNova assessment workflow.

    Architecture:

        User Input
             ↓
        Profile Validation
             ↓
        Knowledge Base
             ↓
        Rule Engine
             ↓
        CSP Solver
             ↓
        Explainable Report
    """

    # ==================================================
    # INPUT NORMALIZATION
    # ==================================================

    try:

        profile = normalize_profile(
            user_profile
        )

    except (
        TypeError,
        ValueError,
    ) as error:

        return {
            "status": "INVALID_INPUT",

            "errors": [
                {
                    "field": "soil.ph",
                    "code": "INVALID_NUMBER",
                    "message": str(error),
                }
            ],

            "warnings": [],

            "limitations": LIMITATIONS,
        }

    # ==================================================
    # INPUT VALIDATION
    # ==================================================

    errors = validate_profile(
        profile
    )

    if errors:

        return {
            "status": "INVALID_INPUT",

            "profile": profile,

            "errors": errors,

            "warnings": [],

            "limitations": LIMITATIONS,
        }

    try:

        # ==============================================
        # KNOWLEDGE BASE
        # ==============================================

        knowledge = load_knowledge()

        knowledge_errors = (
            validate_knowledge(
                knowledge
            )
        )

        if knowledge_errors:

            raise ValueError(
                "Knowledge validation failed: "
                + "; ".join(
                    knowledge_errors
                )
            )

        crops = _candidate_records(
            knowledge
        )

        if not crops:

            return {
                "status": "NO_SUPPORTED_KNOWLEDGE",

                "profile": profile,

                "errors": [],

                "warnings": [
                    (
                        "The knowledge base "
                        "contains no crop records."
                    )
                ],

                "missing_information": [],

                "follow_up_questions": [],

                "limitations": LIMITATIONS,
            }

        # ==============================================
        # RULE ENGINE
        # ==============================================

        rule_result = _rule_adapter(
            profile,
            crops,
        )

        # ==============================================
        # CANDIDATE SELECTION
        # ==============================================

        candidates = _select_candidates(
            crops,
            profile[
                "candidate_ids"
            ],
            rule_result,
        )

        if not candidates:

            return {
                "status": "NO_SUPPORTED_KNOWLEDGE",

                "profile": profile,

                "errors": [],

                "warnings": [
                    (
                        "No requested candidates "
                        "are present in the "
                        "knowledge base."
                    )
                ],

                "missing_information": [],

                "follow_up_questions": [],

                "limitations": LIMITATIONS,
            }

        # ==============================================
        # CSP SOLVER
        # ==============================================

        csp_result = solve_constraints(
            candidates,
            profile,
        )

        missing = _missing(
            csp_result
        )

        # ==============================================
        # FINAL STATUS
        # ==============================================

        status = _status(
            csp_result,
            missing,
            rule_result,
            profile,
        )

        # ==============================================
        # REPORT
        # ==============================================

        report = {
            "status": status,

            "profile": profile,

            "knowledge_version": knowledge.get(
                "metadata",
                {},
            ).get(
                "version",
                "unknown",
            ),

            "knowledge_summary": (
                _knowledge_summary(
                    knowledge
                )
            ),

            # ------------------------------------------
            # Rule Engine information
            # ------------------------------------------

            "rule_status": rule_result.get(
                "status",
                "unknown",
            ),

            "rule_trace": rule_result.get(
                "fired_rules",
                [],
            ),

            "rule_results": rule_result.get(
                "rule_results",
                [],
            ),

            # ------------------------------------------
            # CSP information
            # ------------------------------------------

            "csp_result": csp_result,

            "feasible_options": (
                csp_result.get(
                    "feasible_candidates",
                    [],
                )
            ),

            "rejected_options": (
                csp_result.get(
                    "rejected_candidates",
                    [],
                )
            ),

            "unknown_options": (
                csp_result.get(
                    "unknown_candidates",
                    [],
                )
            ),

            # ------------------------------------------
            # Warnings
            # ------------------------------------------

            "warnings": list(
                dict.fromkeys(
                    rule_result.get(
                        "warnings",
                        [],
                    )
                )
            ),

            # ------------------------------------------
            # Missing information
            # ------------------------------------------

            "missing_information": missing,

            "follow_up_questions": [
                follow_up_question(
                    item["field"]
                )
                for item in missing
                if (
                    item["field"]
                    and item["reason_code"]
                    == "MISSING_USER_INPUT"
                )
            ],

            "errors": [],

            "limitations": LIMITATIONS,
        }

        # ==============================================
        # EXPLANATIONS
        # ==============================================

        report["explanations"] = (
            build_explanations(
                status,
                csp_result,
            )
        )

        # ==============================================
        # EVIDENCE PACKAGE
        # ==============================================

        report["evidence_package"] = (
            build_evidence_package(
                report
            )
        )

        report["evidence"] = (
            _resolve_evidence_sources(
                knowledge,
                report[
                    "evidence_package"
                ][
                    "source_ids_used"
                ],
            )
        )

        return report

    # ==================================================
    # SYSTEM ERROR
    # ==================================================

    except Exception as error:

        return {
            "status": "SYSTEM_ERROR",

            "profile": profile,

            "errors": [
                {
                    "code": "MODULE_FAILURE",
                    "message": str(error),
                }
            ],

            "warnings": [],

            "limitations": LIMITATIONS,
        }


__all__ = [
    "RESULT_STATUSES",
    "normalize_profile",
    "validate_profile",
    "run_assessment",
]