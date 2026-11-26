"""Agent 1: hospitality software requirement analysis."""

import re

from core import llm_client
from core.document_processor import DocumentContent, extract_document
from core.requirement_classifier import classify_requirements, split_sentences


class RequirementAnalysisAgent:
    def process_document(self, content: bytes, filename: str) -> tuple[DocumentContent, dict]:
        """Extract a source document and perform Agent 1 requirement engineering."""
        document = extract_document(content, filename)
        return document, self.run(document.text, document.pages)

    def run(self, text: str, pages: tuple[str, ...] = ()) -> dict:
        if not text.strip():
            raise ValueError("Requirement analysis requires extracted document text.")
        extracted = classify_requirements(text, pages)
        sentences = split_sentences(text)
        analysis_mode = "rule-based fallback"
        if llm_client.is_configured():
            _apply_llm_classifications(extracted, sentences, text, pages)
            analysis_mode = "LLM-enhanced"
        for prefix, key in (("FR", "functional_requirements"), ("NFR", "non_functional_requirements"), ("TR", "technical_requirements")):
            used = {item["requirement_id"] for item in extracted[key] if item.get("requirement_id")}
            next_number = 1
            for requirement in extracted[key]:
                if requirement.get("requirement_id"):
                    continue
                while f"{prefix}-{next_number:02d}" in used:
                    next_number += 1
                requirement["requirement_id"] = f"{prefix}-{next_number:02d}"
                used.add(requirement["requirement_id"])
                next_number += 1
        title = _project_name(text, sentences)
        stakeholders = _extract_list(text, ("stakeholders", "users", "roles", "actors"))
        objectives = _collect_sentences(sentences, ("objective", "goal", "aim", "purpose", "improve", "provide"))
        constraints = extracted["constraints"]
        assumptions = _collect_sentences(sentences, ("assume", "assumption", "will be provided", "expected to"))
        dependencies = _collect_sentences(sentences, ("depend", "third-party", "payment gateway", "integrat"))
        scope = _collect_sentences(sentences, ("system shall", "system must", "system should", "include", "support"))
        technical = extracted["technical_requirements"]
        functional = extracted["functional_requirements"]
        nfrs = extracted["non_functional_requirements"]
        lower = text.lower()
        change_frequency = _level(lower, ("frequent change", "evolving", "regularly update", "iterative feedback", "changing requirements", "short feedback cycles", "pilot feedback", "after staff feedback", "evolve after", "may evolve", "workflow may evolve"), "High",
                                  ("stable requirements", "fixed requirements", "requirements are stable", "stable after"), "Low")
        stability = {"High": "Low", "Low": "High"}.get(change_frequency, "Medium")
        integration_count = sum(
            1 for cue in ("payment gateway", "point-of-sale", "pos terminal", "external booking", "property management system", "email service")
            if cue in lower
        )
        complexity = _level(lower, ("multi-property", "distributed", "real-time", "complex", "microservices"), "High",
                            ("simple system", "single property", "single city hotel", "one property", "basic system"), "Low")
        if complexity == "Medium" and integration_count >= 2:
            complexity = "High"
        elif complexity == "Medium" and len(functional) + len(nfrs) >= 8:
            complexity = "Medium"
        nfr_categories = {item.get("category", "").casefold() for item in nfrs}
        risk = "High" if (
            nfr_categories.intersection({"security", "privacy"})
            and any(cue in lower for cue in ("payment", "personal data", "contact details", "guest data", "diner"))
        ) or any(cue in lower for cue in ("high-impact risk", "high risk", "regulatory", "data breach", "critical system")) else (
            "Low" if "low risk" in lower or "minimal risk" in lower else "Medium"
        )
        size = "Large" if len(functional) + len(nfrs) >= 12 else ("Small" if len(functional) + len(nfrs) <= 4 else "Medium")
        project_overview = _project_overview(text, title)
        confidence = round(min(0.95, 0.45 + min(len(functional) + len(nfrs), 15) * 0.025), 2)
        output = {
            "project_name": title,
            "project_domain": "Hospitality Management",
            "project_overview": project_overview,
            "project_objectives": objectives[:8],
            "project_scope": scope[:12],
            "stakeholders": stakeholders,
            "user_roles": stakeholders,
            **{key: extracted[key] for key in (
                "functional_requirements", "non_functional_requirements", "technical_requirements",
                "constraints", "ambiguities", "conflicts", "missing_requirements",
                "improvement_recommendations", "duplicate_requirements",
                "clarification_questions", "requirement_category_counts",
            )},
            "constraints": constraints,
            "assumptions": assumptions[:10],
            "dependencies": dependencies[:10],
            "requirement_stability": stability,
            "project_complexity": complexity,
            "change_frequency": change_frequency,
            "security_risk": risk,
            "project_size": size,
            "confidence_score": confidence,
            "analysis_mode": analysis_mode,
            "source_document": "",
        }
        output["validation"] = _validate_structured_requirements(output)
        return output

    def record_stakeholder_interaction(
        self,
        requirement_output: dict,
        stakeholder: str,
        interaction: str,
    ) -> dict:
        if not stakeholder.strip() or not interaction.strip():
            raise ValueError("Stakeholder role and clarification input must both be provided.")
        return {
            "stakeholder": stakeholder.strip(),
            "input": interaction.strip(),
            "status": "captured_unvalidated",
            "handled_by": "requirement_engineering_agent",
        }


def _validate_structured_requirements(output: dict) -> dict:
    errors = []
    requirement_fields = (
        "functional_requirements",
        "non_functional_requirements",
        "technical_requirements",
        "constraints",
    )
    for field in requirement_fields:
        items = output.get(field)
        if not isinstance(items, list):
            errors.append(f"{field} must be a list.")
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{field}[{index}] must be a structured requirement.")
                continue
            for required_field in ("requirement_id", "description", "source_evidence"):
                if not item.get(required_field):
                    errors.append(f"{field}[{index}] is missing {required_field}.")
    requirement_count = sum(
        len(output.get(field, []))
        for field in requirement_fields
        if isinstance(output.get(field), list)
    )
    if not requirement_count:
        errors.append("At least one structured requirement or constraint is required.")
    return {
        "status": "validated" if not errors else "invalid",
        "errors": errors,
        "requirement_count": requirement_count,
    }


def _apply_llm_classifications(extracted: dict, sentences: list[str], text: str, pages: tuple[str, ...]) -> None:
    candidates = [
        {"index": index, "text": sentence}
        for index, sentence in enumerate(sentences)
        if len(sentence) <= 500
    ]
    result = llm_client.complete_json(
        "Classify only supplied candidate sentences. Return JSON with a classifications array. "
        "Each item must contain candidate_index, type (functional/non_functional/technical/irrelevant), "
        "category, priority (High/Medium/Low), confidence_score (0-1). Never invent evidence, wording, "
        "or requirements. Exclude irrelevant sentences.",
        str(candidates),
    )
    existing = {
        item["source_evidence"].casefold()
        for key in ("functional_requirements", "non_functional_requirements", "technical_requirements")
        for item in extracted[key]
    }
    categories = {
        "functional": "functional_requirements",
        "non_functional": "non_functional_requirements",
        "technical": "technical_requirements",
    }
    for item in result.get("classifications", []):
        if not isinstance(item, dict):
            continue
        index = item.get("candidate_index")
        kind = item.get("type")
        if not isinstance(index, int) or not 0 <= index < len(sentences) or kind not in categories:
            continue
        sentence = sentences[index]
        if sentence.casefold() in existing:
            continue
        page = next((number for number, content in enumerate(pages, 1) if sentence[:45].casefold() in content.casefold()), None)
        confidence = item.get("confidence_score", 0.65)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.65
        extracted[categories[kind]].append({
            "description": sentence,
            "category": str(item.get("category") or kind.title())[:60],
            "priority": item.get("priority") if item.get("priority") in {"High", "Medium", "Low"} else "Medium",
            "source_evidence": sentence,
            "page_reference": page,
            "confidence_score": confidence,
            "origin": "explicit",
            "acceptance_criteria_measurable": False,
            "duplicate_count": 1,
        })
        existing.add(sentence.casefold())


def _project_name(text: str, sentences: list[str]) -> str:
    for line in text.splitlines()[:15]:
        clean = line.strip().lstrip("#").strip()
        match = re.match(r"(?i)(?:project\s*(?:name|title)?\s*[:\-]\s*)(.+)", clean)
        if match:
            return match.group(1).strip()[:100]
    for sentence in sentences[:8]:
        match = re.search(r"(?i)(?:for|of)\s+(?:the\s+)?([A-Z][\w ]{2,55}?(?:System|Platform|Application))\b", sentence)
        if match:
            return match.group(1).strip()
    return "Hospitality Management Software Project"


def _extract_list(text: str, labels: tuple[str, ...]) -> list[str]:
    lines = text.splitlines()
    result = []
    for index, line in enumerate(lines):
        if any(label in line.lower() for label in labels) and (":" in line or len(line.split()) <= 5):
            candidates = [line.split(":", 1)[1]] if ":" in line else []
            if ":" not in line:
                for following in lines[index + 1:index + 8]:
                    if not following.strip() or following.strip().endswith(":"):
                        break
                    candidates.append(following)
            for candidate in candidates:
                for value in re.split(r"[,;|•]|\s{2,}", candidate.strip(" -*\t")):
                    value = value.strip(" .")
                    if 2 <= len(value) <= 70 and value.lower() not in {label for label in labels}:
                        result.append(value)
    unique = list(dict.fromkeys(result))
    if unique:
        return unique[:12]
    roles = [role for role in ("guest", "customer", "administrator", "manager", "staff", "housekeeper", "restaurant") if role in text.lower()]
    return [role.title() for role in roles]


def _collect_sentences(sentences: list[str], cues: tuple[str, ...]) -> list[str]:
    headers = {"dependencies", "assumptions", "risks", "objectives", "stakeholders"}
    return list(dict.fromkeys(
        sentence for sentence in sentences
        if sentence.casefold().strip(" :") not in headers
        and any(cue in sentence.lower() for cue in cues)
    ))[:12]


def _level(text: str, high_cues: tuple[str, ...], high: str, low_cues: tuple[str, ...], low: str) -> str:
    if any(cue in text for cue in high_cues):
        return high
    if any(cue in text for cue in low_cues):
        return low
    return "Medium"


def _project_overview(text: str, title: str) -> str:
    overview = _collect_sentences(split_sentences(text), ("overview", "system provides", "system will", "platform enables", "designed to"))
    if overview:
        return overview[0]
    first = next((line.strip() for line in text.splitlines() if len(line.strip()) > 35), "")
    return first[:500] if first else f"{title} supports hospitality management processes."
