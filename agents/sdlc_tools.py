"""Specialist tools owned and orchestrated by the SDLC Intelligence Agent."""

import re


_KNOWLEDGE_BASE = (
    {
        "id": "hospitality-payment-security",
        "topic": "Payment and personal-data security",
        "content": (
            "Use a payment provider for card processing, minimize stored payment data, "
            "protect personal information with least-privilege access, and define secure "
            "failure handling. Confirm applicable payment-security obligations with the provider."
        ),
        "terms": {"payment", "card", "security", "personal", "diner", "guest", "contact", "privacy"},
    },
    {
        "id": "hospitality-privacy-governance",
        "topic": "Guest and staff privacy",
        "content": (
            "Document the purpose and lifecycle of guest and staff data, limit collection and access, "
            "and identify retention, correction, and deletion procedures. Applicable privacy duties "
            "depend on jurisdiction and require qualified review."
        ),
        "terms": {"privacy", "personal", "guest", "staff", "data", "contact", "retention", "consent"},
    },
    {
        "id": "hospitality-service-continuity",
        "topic": "Hospitality service continuity",
        "content": (
            "For reservation, ordering, and property operations, define service-hour availability, "
            "degraded-mode procedures, recovery objectives, monitoring, and tested rollback plans."
        ),
        "terms": {"availability", "operating", "reservation", "order", "property", "recovery", "rollout"},
    },
    {
        "id": "hospitality-integration-resilience",
        "topic": "Payment and property-system integrations",
        "content": (
            "Specify interface ownership, versioning, timeouts, retry limits, idempotency, reconciliation, "
            "failure alerts, and end-to-end testing for payment, point-of-sale, booking, and property systems."
        ),
        "terms": {"integration", "payment", "gateway", "pos", "point-of-sale", "booking", "property", "retry"},
    },
    {
        "id": "hospitality-acceptance-and-operations",
        "topic": "Operational acceptance and stakeholder validation",
        "content": (
            "Validate workflows with front-desk, restaurant, housekeeping, finance, and management roles. "
            "Define measurable acceptance checks for business-critical reservations, orders, billing, and reports."
        ),
        "terms": {"stakeholder", "staff", "manager", "reservation", "order", "billing", "acceptance", "workflow"},
    },
)


def analyze_security_privacy(requirement_analysis: dict) -> dict:
    requirements = _all_requirements(requirement_analysis)
    text = " ".join(
        str(item.get("description", "")).casefold()
        for item in requirements
    )
    categories = {
        str(item.get("category", "")).casefold()
        for item in requirement_analysis.get("non_functional_requirements", [])
    }
    data_exposure = any(
        cue in text for cue in ("payment", "card", "personal data", "contact details", "guest data", "diner")
    )
    controls = {
        "authentication": any(cue in text for cue in ("authentication", "login", "sign in")),
        "authorization": any(cue in text for cue in ("authorization", "role-based", "access control", "permissions")),
        "data_protection": any(cue in text for cue in ("encrypt", "protect", "privacy", "data protection")),
    }
    return {
        "risk_level": "High" if data_exposure and categories.intersection({"security", "privacy"}) else (
            "Medium" if data_exposure or categories.intersection({"security", "privacy"}) else "Low"
        ),
        "sensitive_data_requirements_present": data_exposure,
        "security_privacy_categories_present": sorted(categories.intersection({"security", "privacy"})),
        "control_evidence": controls,
        "review_items": [
            f"Specify {control} controls." for control, present in controls.items() if not present
        ],
        "scope_note": "Document-based risk screening; not a security audit or compliance certification.",
    }


def assess_hospitality_compliance(requirement_analysis: dict) -> dict:
    requirements = _all_requirements(requirement_analysis)
    text = " ".join(
        str(item.get("description", "")).casefold()
        for item in requirements
    )
    payment_context = any(cue in text for cue in ("payment", "card", "billing", "payment gateway"))
    personal_data_context = any(cue in text for cue in ("personal data", "guest data", "contact details", "diner"))
    explicit_references = [
        str(item.get("description", ""))
        for item in requirements
        if any(cue in str(item.get("description", "")).casefold() for cue in ("pci", "gdpr", "privacy law", "regulation"))
    ]
    return {
        "assessment_type": "hospitality compliance screening",
        "items": [
            {
                "area": "Payment security",
                "status": "in_scope_review_required" if payment_context else "not_indicated",
                "evidence": explicit_references,
            },
            {
                "area": "Guest and staff privacy",
                "status": "in_scope_review_required" if personal_data_context else "not_indicated",
                "evidence": explicit_references,
            },
            {
                "area": "Hospitality operational continuity",
                "status": "review_required" if requirement_analysis.get("constraints") else "not_indicated",
                "evidence": [
                    str(item.get("description", ""))
                    for item in requirement_analysis.get("constraints", [])
                ],
            },
        ],
        "explicit_regulatory_references": explicit_references,
        "limitations": (
            "This is a requirements-based screening, not legal advice or a declaration of compliance. "
            "Applicability depends on jurisdiction, vendors, and data flows."
        ),
    }


def assess_operational_technical_risks(requirement_analysis: dict) -> list[dict]:
    requirements = _all_requirements(requirement_analysis)
    text = " ".join(str(item.get("description", "")).casefold() for item in requirements)
    risks = []
    if any(cue in text for cue in ("payment", "gateway", "point-of-sale", "pos terminal", "integration")):
        risks.append({
            "area": "External integrations",
            "level": "High",
            "evidence": "Integration or payment dependency appears in Agent 1 requirements.",
            "mitigation": "Agree interface contracts, failure behavior, test environments, and rollout/rollback ownership.",
        })
    if any(cue in text for cue in ("available", "availability", "operating hours", "uptime")):
        risks.append({
            "area": "Service continuity",
            "level": "High",
            "evidence": "Availability or operating-hours requirement appears in Agent 1 output.",
            "mitigation": "Define service targets, monitoring, recovery objectives, and degraded-mode procedures.",
        })
    if any(cue in text for cue in ("evolve", "feedback", "changing", "pilot")):
        risks.append({
            "area": "Operational change",
            "level": "Medium",
            "evidence": "Requirements or workflows may change during feedback or rollout.",
            "mitigation": "Use controlled pilots, staff feedback reviews, and explicit change-impact checks.",
        })
    if not risks:
        risks.append({
            "area": "Requirements uncertainty",
            "level": "Medium",
            "evidence": "No specific external dependency or operational risk was explicit in Agent 1 output.",
            "mitigation": "Confirm operating constraints and technical dependencies with project stakeholders.",
        })
    return risks


def retrieve_hospitality_knowledge(requirement_analysis: dict, limit: int = 3) -> list[dict]:
    query = " ".join(
        str(item.get("description", ""))
        for item in _all_requirements(requirement_analysis)
    ).casefold()
    query_terms = set(re.findall(r"[a-z0-9][a-z0-9-]*", query))
    ranked = []
    for record in _KNOWLEDGE_BASE:
        matched_terms = sorted(query_terms.intersection(record["terms"]))
        if matched_terms:
            ranked.append((len(matched_terms), record, matched_terms))
    ranked.sort(key=lambda result: (-result[0], result[1]["id"]))
    return [
        {
            "source_id": record["id"],
            "topic": record["topic"],
            "content": record["content"],
            "matched_terms": terms,
            "retrieval_score": score,
        }
        for score, record, terms in ranked[:max(0, limit)]
    ]


def _all_requirements(requirement_analysis: dict) -> list[dict]:
    return [
        item
        for key in ("functional_requirements", "non_functional_requirements", "technical_requirements", "constraints")
        for item in requirement_analysis.get(key, [])
        if isinstance(item, dict)
    ]
