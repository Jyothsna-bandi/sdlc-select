"""Deterministic weighted multi-criteria SDLC decision engine."""

CRITERIA_WEIGHTS = {
    "requirement_stability": 0.14,
    "change_frequency": 0.16,
    "project_complexity": 0.15,
    "project_risk": 0.16,
    "security_reliability": 0.12,
    "testing_verification": 0.10,
    "stakeholder_involvement": 0.09,
    "continuous_delivery": 0.08,
}

# In this order: stability, change, complexity, risk, security/reliability,
# verification, stakeholder involvement, and delivery automation.
MODEL_PROFILES = {
    "Waterfall": (0.95, 0.10, 0.35, 0.30, 0.60, 0.75, 0.25, 0.20),
    "V-Shaped (V-Model)": (0.90, 0.15, 0.55, 0.55, 0.95, 0.98, 0.35, 0.20),
    "Prototype": (0.35, 0.80, 0.45, 0.35, 0.45, 0.50, 0.90, 0.30),
    "RAD (Rapid Application Development)": (0.25, 0.90, 0.55, 0.40, 0.50, 0.55, 0.90, 0.50),
    "Spiral": (0.30, 0.55, 0.95, 0.98, 0.90, 0.88, 0.65, 0.30),
    "Iterative": (0.45, 0.75, 0.65, 0.55, 0.60, 0.72, 0.75, 0.40),
    "Agile": (0.20, 0.98, 0.60, 0.50, 0.55, 0.68, 0.98, 0.60),
}
WEIGHTED_DIMENSIONS = tuple(CRITERIA_WEIGHTS)

MODEL_GUIDANCE = {
    "Waterfall": {
        "suitability": "Stable, well-understood scope with formal approval gates and sequential delivery.",
        "advantages": ["Clear phases, documentation, and approval gates", "Predictable planning when requirements are stable"],
        "disadvantages": ["Late requirement changes can be costly", "Working software and user feedback arrive relatively late"],
    },
    "V-Shaped (V-Model)": {
        "suitability": "Stable scope requiring rigorous verification, validation, and requirement-to-test traceability.",
        "advantages": ["Testing is planned alongside each development stage", "Strong verification, validation, and traceability"],
        "disadvantages": ["Changes after baselining can disrupt paired test plans", "Formal documentation and reviews add overhead"],
    },
    "Prototype": {
        "suitability": "Unclear user needs or workflow assumptions that benefit from early mock-ups and stakeholder evaluation.",
        "advantages": ["Surfaces usability and workflow gaps early", "Creates concrete feedback before full implementation"],
        "disadvantages": ["Users may mistake a throwaway prototype for production-ready software", "Repeated revisions can obscure architecture and scope"],
    },
    "RAD (Rapid Application Development)": {
        "suitability": "Modular, time-constrained applications with available users, reusable components, and rapid feedback.",
        "advantages": ["Fast delivery of modular working increments", "Frequent user review helps refine hospitality workflows"],
        "disadvantages": ["Requires continuous access to decision-making users", "Less suitable for tightly coupled, high-risk systems without strong controls"],
    },
    "Spiral": {
        "suitability": "Large, complex, or high-risk work where explicit risk analysis and mitigation should guide each cycle.",
        "advantages": ["Risk-driven cycles target the most consequential uncertainties", "Prototyping and evaluation provide evidence before commitment"],
        "disadvantages": ["Risk assessment adds time and specialist effort", "Cost and schedule can be harder to forecast across cycles"],
    },
    "Iterative": {
        "suitability": "Projects where requirements and architecture can be progressively refined through planned increments.",
        "advantages": ["Delivers learning and value in successive increments", "Supports controlled refinement of requirements and architecture"],
        "disadvantages": ["Iteration scope and integration need active management", "Architecture can drift without deliberate design ownership"],
    },
    "Agile": {
        "suitability": "Changing requirements, short feedback cycles, and engaged stakeholders able to prioritize incremental delivery.",
        "advantages": ["Adapts quickly to changing requirements", "Frequent working increments enable ongoing stakeholder feedback"],
        "disadvantages": ["Requires sustained stakeholder participation", "Scope and delivery forecasting need active management"],
    },
}


def score_models(analysis: dict) -> list[dict]:
    targets = _targets(analysis)
    raw_scores = {}
    for model, profile in MODEL_PROFILES.items():
        fit = sum(
            CRITERIA_WEIGHTS[dimension] * (1 - abs(targets[dimension] - profile[index]))
            for index, dimension in enumerate(WEIGHTED_DIMENSIONS)
        )
        raw_scores[model] = round(max(0.0, min(100.0, fit * 100)), 1)
    results = []
    for model, score in raw_scores.items():
        profile = MODEL_PROFILES[model]
        guidance = MODEL_GUIDANCE[model]
        results.append({
            "model": model,
            "score": score,
            "explanation": _explanation(model, targets),
            "criteria_weights": CRITERIA_WEIGHTS.copy(),
            "suitability": guidance["suitability"],
            "advantages": guidance["advantages"],
            "disadvantages": guidance["disadvantages"],
            "profile_characteristics": {
                dimension: profile[index]
                for index, dimension in enumerate(WEIGHTED_DIMENSIONS)
            },
        })
    return results


def hybrid_approach(scores: list[dict], analysis: dict) -> dict:
    """Offer a two-model hybrid only when close scores have distinct strengths."""
    ranked = sorted(scores, key=lambda item: (-item["score"], item["model"]))
    not_recommended = {
        "recommended": False,
        "models": [],
        "reason": "No close-scoring pair has complementary strengths on important project characteristics.",
    }
    if len(ranked) < 2 or ranked[0]["score"] - ranked[1]["score"] > 5.0:
        return not_recommended

    targets = _targets(analysis)
    first, second = ranked[:2]
    first_profile = MODEL_PROFILES[first["model"]]
    second_profile = MODEL_PROFILES[second["model"]]
    first_strengths = []
    second_strengths = []
    for index, dimension in enumerate(WEIGHTED_DIMENSIONS):
        if targets[dimension] < 0.65:
            continue
        first_fit = 1 - abs(targets[dimension] - first_profile[index])
        second_fit = 1 - abs(targets[dimension] - second_profile[index])
        if first_fit - second_fit >= 0.12:
            first_strengths.append(dimension.replace("_", " "))
        elif second_fit - first_fit >= 0.12:
            second_strengths.append(dimension.replace("_", " "))
    if not first_strengths or not second_strengths:
        return not_recommended
    return {
        "recommended": True,
        "models": [first["model"], second["model"]],
        "reason": (
            f"The two standalone scores are within {first['score'] - second['score']:.1f} points, "
            f"and have complementary fit: {first['model']} supports {', '.join(first_strengths)}, "
            f"while {second['model']} supports {', '.join(second_strengths)}. "
            "This is an optional combination, not a separately scored model."
        ),
    }


def _targets(analysis: dict) -> dict[str, float]:
    nfr_categories = {
        item.get("category", "").lower()
        for item in analysis.get("non_functional_requirements", [])
    }
    stability = _level(analysis.get("requirement_stability", "Medium"), stable=0.9, variable=0.1)
    change = _level(analysis.get("change_frequency", "Medium"), stable=0.1, variable=0.9)
    complexity = _level(analysis.get("project_complexity", "Medium"), stable=0.1, variable=0.9)
    risk = _level(analysis.get("security_risk", "Medium"), stable=0.1, variable=0.9)
    size = _level(analysis.get("project_size", "Medium"), stable=0.1, variable=0.9)
    count = len(analysis.get("functional_requirements", [])) + len(analysis.get("non_functional_requirements", []))
    return {
        "requirement_stability": stability,
        "change_frequency": change,
        "project_complexity": min(1.0, complexity * 0.75 + size * 0.25),
        "project_risk": risk,
        "security_reliability": 0.85 if {"security", "privacy", "reliability", "availability"} & nfr_categories else risk,
        "testing_verification": 0.85 if {"security", "reliability", "performance", "availability"} & nfr_categories else min(0.8, 0.4 + count * 0.02),
        "stakeholder_involvement": min(1.0, 0.25 + 0.16 * len(analysis.get("stakeholders", []))),
        "continuous_delivery": 0.85 if any(
            word in " ".join(analysis.get("technical_requirements", []) if all(isinstance(item, str) for item in analysis.get("technical_requirements", [])) else [
                item.get("description", "") for item in analysis.get("technical_requirements", [])
            ]).lower()
            for word in ("continuous", "automated deployment", "ci/cd", "frequent release")
        ) else 0.45,
    }


def _level(value: str, stable: float, variable: float) -> float:
    normalized = str(value).lower()
    if normalized in {"high", "large"}:
        return variable
    if normalized in {"low", "small"}:
        return stable
    return 0.5


def _explanation(model: str, targets: dict[str, float]) -> str:
    profile = MODEL_PROFILES[model]
    best_fits = sorted(
        ((1 - abs(targets[key] - profile[index])) * CRITERIA_WEIGHTS[key], key)
        for index, key in enumerate(WEIGHTED_DIMENSIONS)
    )
    factors = [key.replace("_", " ") for _, key in best_fits[-3:]]
    return f"{model} aligns well with the assessed {', '.join(factors)} characteristics."
