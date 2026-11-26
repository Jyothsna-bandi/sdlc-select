"""Rule-based requirement extraction and focused quality checks."""

import re
from collections import Counter

NFR_CATEGORIES = {
    "security": ("security", "secure", "encrypt", "authentication", "authorization", "password", "access control", "protect", "payment data"),
    "privacy": ("privacy", "confidential", "personal data", "contact details", "data protection"),
    "performance": ("response time", "within ", "concurrent", "throughput", "load within", "seconds", "milliseconds", "peak period"),
    "availability": ("availability", "uptime", "24/7", "operating hours", "service hours", "available during", "available throughout", "available at all times"),
    "reliability": ("reliable", "reliability", "backup", "recovery", "fault tolerant", "disaster recovery"),
    "usability": ("easy to use", "intuitive", "user-friendly", "usability"),
    "scalability": ("scalable", "scale", "growth"),
    "maintainability": ("maintainable", "maintenance", "modular"),
    "portability": ("portable", "portability", "cross-platform"),
    "compatibility": ("compatible", "interoperability"),
    "accessibility": ("accessibility", "accessible", "wcag", "screen reader"),
}
FUNCTIONAL_CUES = (
    "shall ", "must ", "should ", "can ", "allow ", "enable ", "support ",
    "provides ", "manage ", "record ", "generate ", "display ", "send ",
    "create ", "cancel ", "search ", "book ", "reserve ", "update ",
    "calculate ", "view ", "submit ", "mark ", "protect ", "integrate ",
    "provide ", "remain ", "available ",
)
TECHNICAL_CUES = (
    "api", "database", "cloud", "browser", "mobile application", "payment gateway",
    "platform", "integration", "technology", "architecture", "server", "point-of-sale",
    "pos terminal", "web interface",
)
AMBIGUOUS_CUES = ("fast", "user-friendly", "easy", "appropriate", "sufficient", "secure", "quickly", "as needed")
MEASURABLE_CUES = ("within ", "%", "seconds", "milliseconds", "minutes", "hours", "concurrent", "per day", "99.")
SECTION_HEADERS = {
    "functional requirements": "functional",
    "functional requirement": "functional",
    "non-functional requirements": "non_functional",
    "nonfunctional requirements": "non_functional",
    "non-functional requirement": "non_functional",
    "technical requirements": "technical",
    "technical requirement": "technical",
    "constraints": "constraints",
    "constraint": "constraints",
    "stakeholders": "stakeholders",
    "users and roles": "stakeholders",
    "user roles": "stakeholders",
    "objectives": "objectives",
    "project objectives": "objectives",
    "assumptions": "assumptions",
    "dependencies": "dependencies",
    "risks": "risks",
    "project overview": "overview",
    "overview": "overview",
}
REQUIREMENT_ID = re.compile(r"^\s*((?:FR|NFR|TR|REQ)-?\d+)\b[\s:.-]*(.*)$", re.IGNORECASE)


def _clean_line(line: str) -> str:
    return line.strip().lstrip("#").strip().lstrip("-*• \t").strip()


def split_sentences(text: str) -> list[str]:
    """Split at document line boundaries and sentence ends without flattening IDs."""
    statements = []
    for line in text.replace("\r", "\n").split("\n"):
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=(?:[A-Z0-9]))", cleaned)
        statements.extend(part.strip() for part in parts if len(part.strip()) >= 8)
    return statements


def _statements_with_sections(text: str) -> list[tuple[str, str]]:
    statements = []
    section = ""
    for line in text.replace("\r", "\n").split("\n"):
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        normalized_header = re.sub(r"[:\s]+$", "", cleaned).lower()
        if normalized_header in SECTION_HEADERS:
            section = SECTION_HEADERS[normalized_header]
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=(?:[A-Z0-9]))", cleaned)
        for part in parts:
            part = part.strip()
            if len(part) >= 8:
                statements.append((part, section))
    return statements


def _classify_nfr(lower: str) -> str | None:
    # Protecting payment/contact data is a security control, even without
    # conventional words such as "encrypt" or "authentication".
    if any(cue in lower for cue in NFR_CATEGORIES["security"]):
        return "security"
    if any(cue in lower for cue in NFR_CATEGORIES["privacy"]):
        return "privacy"
    if any(cue in lower for cue in NFR_CATEGORIES["performance"]):
        return "performance"
    if any(cue in lower for cue in NFR_CATEGORIES["availability"]):
        return "availability"
    return next(
        (category for category, cues in NFR_CATEGORIES.items() if any(cue in lower for cue in cues)),
        None,
    )


def _is_requirement_id(sentence: str) -> str | None:
    match = REQUIREMENT_ID.match(sentence)
    return match.group(1).upper() if match else None


def _make_requirement(
    sentence: str,
    category: str,
    requirement_id: str | None,
    page: int | None,
) -> dict:
    lower = sentence.lower()
    id_match = REQUIREMENT_ID.match(sentence)
    description = id_match.group(2).strip() if id_match else sentence
    return {
        "requirement_id": requirement_id or "",
        "description": description or sentence,
        "category": category,
        "priority": "High" if any(word in lower for word in ("payment", "personal data", "security", "reservation", "critical")) else "Medium",
        "source_evidence": sentence,
        "page_reference": page,
        "confidence_score": 0.9 if requirement_id else 0.78,
        "origin": "explicit",
        "acceptance_criteria_measurable": any(cue in lower for cue in MEASURABLE_CUES),
        "duplicate_count": 1,
    }


def classify_requirements(text: str, pages: tuple[str, ...] = ()) -> dict:
    functional, non_functional, technical, constraints = [], [], [], []
    seen: dict[str, dict] = {}
    ambiguities, missing, recommendations = [], [], []
    statements = _statements_with_sections(text)

    for sentence, section in statements:
        normalized = re.sub(r"[^a-z0-9 ]", "", sentence.lower())
        requirement_id = _is_requirement_id(sentence)
        id_kind = "functional" if requirement_id and requirement_id.upper().startswith("FR") else (
            "non_functional" if requirement_id and requirement_id.upper().startswith("NFR") else (
                "technical" if requirement_id and requirement_id.upper().startswith("TR") else ""
            )
        )
        if normalized in seen:
            seen[normalized]["duplicate_count"] += 1
            continue
        page = next(
            (index for index, content in enumerate(pages, 1) if sentence[:45].casefold() in content.casefold()),
            None,
        )
        lower = sentence.lower()
        nfr_category = _classify_nfr(lower)
        target_kind = id_kind
        if not target_kind:
            if section == "constraints":
                target_kind = "constraints"
            elif section == "technical":
                target_kind = "technical"
            elif section == "non_functional":
                target_kind = "non_functional"
            elif section == "functional":
                target_kind = "functional"
            elif section in {"stakeholders", "objectives", "assumptions", "dependencies", "risks", "overview"}:
                target_kind = "ignore"
            elif nfr_category:
                target_kind = "non_functional"
            elif any(cue in lower for cue in TECHNICAL_CUES):
                target_kind = "technical"
            elif any(cue in lower for cue in FUNCTIONAL_CUES):
                target_kind = "functional"
        if target_kind in {"functional", "non_functional", "technical"}:
            if target_kind == "functional" and nfr_category and not id_kind:
                target_kind = "non_functional"
            if target_kind == "non_functional":
                category = nfr_category or "Non-functional"
                item = _make_requirement(sentence, category.title(), requirement_id, page)
                non_functional.append(item)
            elif target_kind == "technical":
                item = _make_requirement(sentence, "Technical", requirement_id, page)
                technical.append(item)
            else:
                item = _make_requirement(sentence, "Functional", requirement_id, page)
                functional.append(item)
            item["duplicate_count"] = 1
            item["source_section"] = section or "Unlabeled"
            seen[normalized] = item
            if any(cue in lower for cue in AMBIGUOUS_CUES):
                ambiguities.append({
                    "description": sentence,
                    "reason": "Contains qualitative wording without a defined threshold or acceptance measure.",
                    "page_reference": page,
                    "source_evidence": sentence,
                    "origin": "analysis",
                })
        elif target_kind == "constraints":
            item = _make_requirement(sentence, "Constraint", None, page)
            item["source_section"] = section or "Constraints"
            constraints.append(item)
            seen[normalized] = item

    for requirements, prefix in (
        (functional, "FR"),
        (non_functional, "NFR"),
        (technical, "TR"),
    ):
        for index, requirement in enumerate(requirements, 1):
            requirement["requirement_id"] = requirement["requirement_id"] or f"{prefix}-{index:02d}"
    for index, constraint in enumerate(constraints, 1):
        constraint["requirement_id"] = f"CON-{index:02d}"

    duplicates = [
        {"description": item["description"], "occurrences": item["duplicate_count"]}
        for item in seen.values() if item.get("duplicate_count", 1) > 1
    ]
    requirement_text = " ".join(
        item["description"].casefold()
        for item in functional + non_functional + technical + constraints
    )
    if functional and not any(
        cue in requirement_text
        for cue in ("acceptance criteria", "acceptance test", "test case", "testable", "shall pass")
    ):
        recommendations.append({
            "description": "Add acceptance criteria or test cases for each functional workflow.",
            "reason": "The document describes behavior but does not state explicit acceptance checks.",
            "origin": "recommendation",
        })
    if any(cue in requirement_text for cue in ("payment", "bill", "billing", "tip", "transaction")) and not any(
        cue in requirement_text for cue in ("payment failure", "failed payment", "retry", "refund", "reconcile", "reversal")
    ):
        missing.append({
            "description": "Specify how failed, delayed, or duplicated payment transactions are handled.",
            "category": "Payment resilience",
            "source_evidence": "",
            "origin": "inferred_gap",
        })
    if any(cue in requirement_text for cue in ("guest", "diner", "personal data", "payment data")) and not any(
        cue in requirement_text for cue in ("authentication", "authorization", "access control", "role-based")
    ):
        missing.append({
            "description": "Define authentication, authorization, and role-based access controls for guest/staff data.",
            "category": "Security",
            "source_evidence": "",
            "origin": "inferred_gap",
        })
    if any(cue in requirement_text for cue in ("reservation", "order", "room inventory", "database")) and not any(
        cue in requirement_text for cue in ("backup", "recovery", "disaster recovery", "restore")
    ):
        recommendations.append({
            "description": "Consider defining backup, restore, and recovery objectives for operational data.",
            "reason": "Reservations or operational records are central to service continuity.",
            "origin": "recommendation",
        })
    nfr_categories = {item["category"].casefold() for item in non_functional}
    if "performance" not in nfr_categories and any(
        cue in requirement_text for cue in ("response time", "seconds", "concurrent", "latency", "throughput")
    ):
        # Defensive: keep measurable targets represented as performance even
        # if section-context classification was used.
        candidates = [item for item in non_functional if any(cue in item["description"].lower() for cue in ("seconds", "concurrent", "latency", "throughput"))]
        for item in candidates:
            item["category"] = "Performance"

    conflicts = _find_conflicts([statement for statement, _ in statements])
    return {
        "functional_requirements": functional,
        "non_functional_requirements": non_functional,
        "technical_requirements": technical,
        "constraints": constraints,
        "ambiguities": ambiguities,
        "conflicts": conflicts,
        "missing_requirements": missing,
        "improvement_recommendations": recommendations,
        "duplicate_requirements": duplicates,
        "clarification_questions": [
            f"What measurable acceptance checks apply to: {item['description']}"
            for item in ambiguities[:10]
        ] + [
            f"How should the project address this gap: {item['description']}"
            for item in missing
        ],
        "requirement_category_counts": dict(Counter(
            item["category"] for item in functional + non_functional + technical
        )),
    }


def _find_conflicts(sentences: list[str]) -> list[dict]:
    conflicts = []
    groups = (
        (("no login", "without authentication", "anonymous access"), ("must log in", "authentication is required")),
        (("unlimited", "no limit"), ("maximum of", "limited to", "must not exceed")),
    )
    lowered = [(item, item.lower()) for item in sentences]
    for positive, negative in groups:
        matches_a = [text for text, low in lowered if any(cue in low for cue in positive)]
        matches_b = [text for text, low in lowered if any(cue in low for cue in negative)]
        if matches_a and matches_b:
            conflicts.append({
                "description": f"Potentially conflicting statements: '{matches_a[0]}' and '{matches_b[0]}'",
                "page_reference": None,
                "source_evidence": f"{matches_a[0]} | {matches_b[0]}",
                "origin": "analysis",
            })
    return conflicts
