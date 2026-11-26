"""Agent 2: project characteristics, SDLC comparison, and workflow creation."""

from core.scoring_engine import MODEL_GUIDANCE, hybrid_approach, score_models
from agents.sdlc_tools import (
    analyze_security_privacy,
    assess_hospitality_compliance,
    assess_operational_technical_risks,
    retrieve_hospitality_knowledge,
)


class SDLCRecommendationAgent:
    def run(self, agent1_message: dict) -> dict:
        """Analyze a validated Agent 1 payload or coordinator-routed message."""
        message_metadata = {}
        if isinstance(agent1_message, dict) and "content" in agent1_message:
            if (
                agent1_message.get("sender") != "requirement_engineering_agent"
                or agent1_message.get("recipient") != "sdlc_intelligence_agent"
                or agent1_message.get("message_type") != "validated_requirements"
            ):
                raise ValueError("Agent 2 accepts only coordinator-routed, validated Agent 1 messages.")
            message_metadata = {
                "sender": agent1_message["sender"],
                "recipient": agent1_message["recipient"],
                "message_type": agent1_message["message_type"],
                "trace_id": agent1_message.get("trace_id"),
            }
            requirement_analysis = agent1_message["content"]
        else:
            requirement_analysis = agent1_message
        required_lists = ("functional_requirements", "non_functional_requirements", "technical_requirements")
        if (
            not isinstance(requirement_analysis, dict)
            or not requirement_analysis.get("project_name")
            or requirement_analysis.get("project_domain") != "Hospitality Management"
            or any(not isinstance(requirement_analysis.get(field), list) for field in required_lists)
            or not isinstance(requirement_analysis.get("validation"), dict)
            or requirement_analysis.get("validation", {}).get("status") != "validated"
        ):
            raise ValueError("SDLC recommendation requires Agent 1's validated structured requirement output.")
        security_analysis = analyze_security_privacy(requirement_analysis)
        compliance_assessment = assess_hospitality_compliance(requirement_analysis)
        operational_risks = assess_operational_technical_risks(requirement_analysis)
        knowledge = retrieve_hospitality_knowledge(requirement_analysis)
        scoring_context = dict(requirement_analysis)
        scoring_context["security_risk"] = security_analysis["risk_level"]
        scores = score_models(scoring_context)
        ranked = sorted(scores, key=lambda item: (-item["score"], item["model"]))
        winner = ranked[0]["model"]
        characteristics = _project_characteristics(requirement_analysis)
        if security_analysis["risk_level"] == "High":
            characteristics["security_risk"] = "High"
            characteristics["development_risks"] = "High"
        winner_explanation = _justification(winner, ranked, characteristics, requirement_analysis)
        for item in ranked:
            if item["model"] != winner:
                item["explanation"] = _alternative_explanation(
                    item["model"], item["score"], winner, ranked[0]["score"],
                    characteristics, requirement_analysis,
                )
        for item in scores:
            ranked_item = next(entry for entry in ranked if entry["model"] == item["model"])
            item["explanation"] = ranked_item["explanation"]
        return {
            "source_project": requirement_analysis["project_name"],
            "agent_1_input_received": True,
            "agent1_message": message_metadata,
            "project_characteristics": characteristics,
            "security_privacy_analysis": security_analysis,
            "hospitality_compliance_assessment": compliance_assessment,
            "operational_technical_risks": operational_risks,
            "retrieved_hospitality_knowledge": knowledge,
            "model_scores": scores,
            "ranked_comparison": ranked,
            "recommended_model": winner,
            "hybrid_approach": hybrid_approach(scores, scoring_context),
            "justification": winner_explanation,
            "factors_supporting_recommendation": _supporting_factors(characteristics),
            "alternatives": [
                {"model": item["model"], "score": item["score"], "why_lower": item["explanation"]}
                for item in ranked[1:]
            ],
            "advantages": _model_advantages(winner),
            "disadvantages": _model_disadvantages(winner),
            "model_suitability": MODEL_GUIDANCE[winner]["suitability"],
            "implementation_considerations": [
                f"Trace the {len(requirement_analysis.get('functional_requirements', []))} functional requirements to review and test evidence.",
                "Resolve high-priority quality gaps for payment processing and staff/guest data before release planning."
                if requirement_analysis.get("missing_requirements") else
                "Keep requirement-to-test traceability current as scope is refined.",
                "Review this model choice when measured risks, release cadence, or stakeholder availability materially changes.",
                *[
                    f"Use retrieved guidance on {item['topic']} ({item['source_id']}) during design and acceptance review."
                    for item in knowledge[:2]
                ],
                *[
                    item["mitigation"] for item in operational_risks[:2]
                ],
            ],
            "workflow": _workflow(winner, requirement_analysis),
            "analysis_mode": "deterministic weighted scoring",
        }


def _has_category(analysis: dict, category: str) -> bool:
    return any(item.get("category", "").strip().lower() == category for item in analysis.get("non_functional_requirements", []))


def _supporting_factors(characteristics: dict) -> list[str]:
    return [f"{key.replace('_', ' ').title()}: {value}" for key, value in characteristics.items()]


def _project_characteristics(analysis: dict) -> dict:
    nfrs = analysis.get("non_functional_requirements", [])
    categories = {item.get("category", "").strip().casefold() for item in nfrs}
    requirements_text = " ".join(
        str(item.get("description", ""))
        for key in ("functional_requirements", "non_functional_requirements", "technical_requirements", "constraints")
        for item in analysis.get(key, [])
        if isinstance(item, dict)
    ).casefold()
    integrations = " ".join(
        str(item.get("description", item) if isinstance(item, dict) else item)
        for item in analysis.get("technical_requirements", []) + analysis.get("dependencies", [])
    ).casefold()
    security_is_explicit = bool(categories.intersection({"security", "privacy"}))
    security_risk = "High" if security_is_explicit and any(
        cue in requirements_text for cue in ("payment", "personal data", "contact details", "guest data", "diner", "financial")
    ) else analysis.get("security_risk", "Medium")
    performance_evidence = [
        item for item in nfrs
        if item.get("category", "").casefold() == "performance"
        and (
            item.get("acceptance_criteria_measurable")
            or any(cue in item.get("description", "").casefold() for cue in ("within", "seconds", "milliseconds", "concurrent", "throughput", "latency"))
        )
    ]
    stakeholders = analysis.get("stakeholders", [])
    stakeholder_level = "High" if len(stakeholders) >= 4 else ("Medium" if stakeholders else "Low")
    has_integrations = bool(analysis.get("dependencies")) or any(
        cue in integrations for cue in ("integrat", "gateway", "point-of-sale", "pos terminal", "third-party", "external system", "api")
    )
    constraints = analysis.get("constraints", [])
    time_constraints = any(
        cue in str(item.get("description", item)).casefold()
        for item in constraints
        for cue in ("deadline", "launch", "budget", "fixed date", "before the", "rollout")
    )
    continuous_delivery_text = " ".join(
        str(item.get("description", item) if isinstance(item, dict) else item)
        for item in analysis.get("technical_requirements", [])
    ).casefold()
    return {
        "requirement_stability": analysis.get("requirement_stability", "Medium"),
        "change_frequency": analysis.get("change_frequency", "Medium"),
        "project_complexity": analysis.get("project_complexity", "Medium"),
        "project_size": analysis.get("project_size", "Medium"),
        "security_risk": security_risk,
        "performance_requirements": bool(performance_evidence),
        "availability_requirements": "availability" in categories,
        "maintenance_requirements": "maintainability" in categories,
        "testing_requirements": bool(categories.intersection({"reliability", "security", "performance", "availability"})),
        "stakeholder_involvement": stakeholder_level,
        "integration_requirements": has_integrations,
        "time_constraints": time_constraints,
        "development_risks": security_risk,
        "continuous_delivery": any(
            cue in continuous_delivery_text for cue in ("continuous", "ci/cd", "automated deployment", "frequent release")
        ),
    }


def _justification(model: str, ranked: list[dict], characteristics: dict, analysis: dict) -> str:
    actuals = []
    for field in ("change_frequency", "project_complexity", "security_risk", "stakeholder_involvement"):
        actuals.append(f"{field.replace('_', ' ')} is {characteristics[field].lower()}")
    perf = [
        item["description"] for item in analysis.get("non_functional_requirements", [])
        if item.get("category", "").casefold() == "performance"
    ]
    if perf:
        actuals.append(f"the SRS specifies {perf[0]}")
    if characteristics["availability_requirements"]:
        actuals.append("the service has an explicit availability requirement")
    if characteristics["integration_requirements"]:
        actuals.append("external integrations are specified")
    runner_up = ranked[1] if len(ranked) > 1 else None
    comparison = f" It leads the next model, {runner_up['model']}, by {ranked[0]['score'] - runner_up['score']:.1f} points." if runner_up else ""
    return (
        f"{model} received the highest weighted fit score ({ranked[0]['score']:.1f}/100) because "
        + ", ".join(actuals)
        + f". {MODEL_GUIDANCE[model]['suitability']} The recommendation follows the assessed project profile and the existing weighted criteria."
        + comparison
    )


def _alternative_explanation(model: str, score: float, winner: str, winner_score: float, characteristics: dict, analysis: dict) -> str:
    return (
        f"{model} scored {score:.1f}/100, {winner_score - score:.1f} points below {winner}. "
        f"{MODEL_GUIDANCE[model]['suitability']} This remains a viable alternative if project priorities "
        "or delivery constraints change."
    )


def _model_advantages(model: str) -> list[str]:
    return MODEL_GUIDANCE[model]["advantages"]


def _model_disadvantages(model: str) -> list[str]:
    return MODEL_GUIDANCE[model]["disadvantages"]


def _workflow(model: str, analysis: dict) -> list[dict]:
    functional = analysis.get("functional_requirements", [])
    examples = [
        f"{item.get('requirement_id', 'REQ')}: {item.get('description', '')}"
        for item in functional[:3]
    ]
    focus = "; ".join(examples) or f"key workflows for {analysis.get('project_name', 'the project')}"
    integration_list = [
        item.get("description", "") if isinstance(item, dict) else str(item)
        for item in analysis.get("technical_requirements", [])
    ]
    integration_focus = "; ".join(
        item for item in integration_list
        if any(cue in item.casefold() for cue in ("integrat", "gateway", "pos", "point-of-sale", "api"))
    ) or "documented service boundaries"
    sensitive_categories = {
        item.get("category", "").casefold()
        for item in analysis.get("non_functional_requirements", [])
    }
    data_risk = "security, privacy, and payment controls" if sensitive_categories.intersection({"security", "privacy"}) else "data protection and operational controls"

    templates = {
        "Waterfall": [
            ("Requirements baseline", ["Baseline scope and acceptance criteria for " + focus, "Resolve ambiguities and record change control"], ["Business analyst", "Hotel operations owner"], ["Approved SRS", "Requirement traceability matrix", "Signed acceptance criteria"], "Review requirement coverage and acceptance measurability.", "Stakeholders and source documents are available.", "Requirements are approved and each has an owner and acceptance check."),
            ("System and integration design", ["Define architecture and data flows for " + integration_focus, "Specify access control and failure handling"], ["Solution architect", "Security engineer", "Integration lead"], ["Architecture specification", "Interface contracts", "Threat and integration risk register"], "Design inspection, API contract validation, and threat-model review.", "Requirements baseline and integration contacts are approved.", "Design traces to requirements; high risks and interfaces have mitigation plans."),
            ("Implementation and integration", ["Implement the approved reservation/order and staff workflows", "Integrate and validate " + integration_focus], ["Development team", "Integration engineer"], ["Versioned application increment", "Integration build", "Updated traceability"], "Code review, unit tests, and interface contract tests for changed components.", "Design is baselined and development environment is ready.", "All planned components build and component tests pass."),
            ("System verification and acceptance", ["Execute system, security, performance, and user-acceptance tests", "Verify requirement IDs against acceptance evidence"], ["QA lead", "Security tester", "Restaurant/hotel operations representative"], ["Test report", "Defect register", "Business acceptance record"], "Requirement-based regression, payment failure tests, access-control tests, and measured load checks.", "Integrated build and approved test environment are available.", "Critical defects are closed and acceptance evidence is signed."),
            ("Controlled release and maintenance", ["Plan deployment and rollback around existing property operations", "Monitor live service and resolve production incidents"], ["Release manager", "Operations manager", "Support lead"], ["Release and rollback plan", "Operational runbook", "Maintenance backlog"], "Deployment rehearsal, smoke checks, recovery/restore test, and production monitoring.", "Acceptance sign-off and operational readiness are complete.", "Release health is stable and ongoing support ownership is established."),
        ],
        "Agile": [
            ("Product discovery and backlog", ["Create an ordered backlog from " + focus, "Agree a definition of done and acceptance examples with stakeholders"], ["Product owner", "Business analyst", "Guest/staff representatives"], ["Prioritized product backlog", "Story acceptance examples", "Initial risk list"], "Three-amigos review and acceptance-criteria walkthrough.", "Stakeholders and outcome measures are identified.", "Top stories are understood, sized, and ready for sprint planning."),
            ("Sprint planning and design", ["Select a thin hospitality workflow slice", "Design only the interfaces needed for " + integration_focus], ["Product owner", "Tech lead", "UX designer"], ["Sprint goal", "Story map", "Just-enough design notes"], "Design huddle and test-scenario review before implementation.", "Ready backlog items and team capacity are agreed.", "Sprint goal, test scenarios, and dependencies have owners."),
            ("Sprint implementation", ["Build and integrate the selected guest/staff user journey", "Demonstrate working software for " + focus], ["Cross-functional delivery team", "Domain representative"], ["Working increment", "Reviewed code", "Updated acceptance evidence"], "Automated unit, component, and integration tests on each change.", "Sprint plan and development environment are ready.", "Definition of done passes and increment is demonstrable."),
            ("Sprint review and acceptance", ["Demo the increment to operations and guest-facing stakeholders", "Record feedback and reprioritize workflow gaps"], ["Product owner", "Operations representatives", "QA engineer"], ["Accepted or revised stories", "Stakeholder feedback", "Updated backlog"], "Acceptance tests and exploratory usability tests with representative users.", "A potentially releasable increment and demo data are available.", "Feedback is recorded and accepted items meet their criteria."),
            ("Release and retrospective", ["Release accepted increments through a controlled rollout", "Inspect delivery and service measures; choose a concrete improvement"], ["Release engineer", "Support lead", "Whole team"], ["Release notes", "Operational metrics", "Retrospective action"], "Regression smoke suite, security checks, and post-deploy health verification.", "Release readiness and rollback plan are confirmed.", "Service is healthy and improvement actions have owners."),
        ],
        "Prototype": [
            ("Discover user needs and assumptions", ["Map guest and staff workflows from " + focus, "Identify uncertain interactions and define prototype questions"], ["Business analyst", "UX designer", "Hospitality staff representatives"], ["User journey maps", "Assumption register", "Prototype objectives"], "Review scenarios with representative guests and staff before prototyping.", "Stakeholders and high-uncertainty workflows are identified.", "Prototype scope and evaluation questions are agreed."),
            ("Build focused prototypes", ["Create low-fidelity screens for reservations, ordering, and " + focus, "Mock integration behavior for " + integration_focus], ["UX designer", "Front-end developer", "Integration specialist"], ["Clickable prototype", "Mock integration flows", "Prototype notes"], "Usability walkthroughs, accessibility checks, and interface feasibility spikes.", "Prototype objectives and sample scenarios are approved.", "Users can complete target journeys and major feasibility questions are recorded."),
            ("Evaluate and refine requirements", ["Observe users completing representative tasks", "Convert validated feedback into acceptance-ready requirements"], ["Product owner", "Restaurant/hotel operations staff", "Business analyst"], ["Evaluation findings", "Refined requirement backlog", "Prioritized usability changes"], "Task completion observation, stakeholder review, and requirement traceability checks.", "Prototype is ready and representative users are available.", "Feedback decisions are prioritized and requirements are baselined for implementation."),
            ("Engineer and validate production solution", ["Replace prototype components with production-grade implementation", "Verify security, data handling, and " + integration_focus], ["Development team", "Security engineer", "QA lead"], ["Production implementation", "Interface contracts", "Acceptance evidence"], "Unit, integration, security, performance, and user-acceptance tests.", "Validated requirements and production architecture are approved.", "Production solution passes acceptance and operational readiness checks."),
        ],
        "RAD (Rapid Application Development)": [
            ("Requirements planning and timeboxing", ["Agree a bounded release scope for " + focus, "Set timeboxes, reuse options, and user review availability"], ["Product owner", "Facilitator", "Hospitality operations representatives"], ["Timeboxed delivery plan", "Prioritized requirements", "Component reuse assessment"], "Feasibility review, risk check, and acceptance criteria walkthrough.", "Business goals, time constraints, and empowered users are confirmed.", "Timebox, scope boundaries, and delivery roles are approved."),
            ("User design workshops", ["Co-design modular guest/staff workflows with operational users", "Define reusable interfaces to " + integration_focus], ["UX designer", "Business analyst", "Guest/staff representatives"], ["Workshop decisions", "Screen and data prototypes", "Module/interface specifications"], "Structured user walkthroughs and interface contract reviews.", "Timeboxed plan and representative users are available.", "Users accept module designs and interface assumptions are documented."),
            ("Rapid construction in modules", ["Build prioritized modules for " + focus, "Integrate reusable components and service interfaces incrementally"], ["Cross-functional module teams", "Integration developer"], ["Working modules", "Incremental integration build", "Updated requirements trace"], "Continuous unit, module integration, and regression checks.", "Module designs and testable acceptance criteria are agreed.", "Modules meet acceptance checks and integrate with adjacent components."),
            ("User validation and transition", ["Run end-to-end staff and guest scenarios", "Package release, training, and operational handover"], ["QA lead", "Operations representatives", "Release manager"], ["User acceptance record", "Training material", "Release and support plan"], "Scenario-based acceptance, security, performance, and recovery testing.", "Integrated modules and representative test data are ready.", "Critical defects are resolved, users approve, and support accepts the release."),
        ],
        "Spiral": [
            ("Set objectives and alternatives", ["Set the iteration goal around " + focus, "Compare implementation and integration alternatives for " + integration_focus], ["Product owner", "Architect", "Risk analyst"], ["Iteration objectives", "Alternative analysis", "Risk-ranked plan"], "Risk-based test objectives and acceptance measures are reviewed.", "Stakeholders agree the iteration objective.", "Alternatives and highest-impact uncertainties are documented."),
            ("Risk analysis and prototyping", ["Prototype uncertain guest/staff flows and external interfaces", "Analyze payment, privacy, availability, and rollout risks"], ["Risk analyst", "Security engineer", "Integration specialist"], ["Prototype findings", "Updated risk register", "Mitigation experiments"], "Security threat probes, interface contract spikes, and performance feasibility tests.", "Prioritized risks and testable hypotheses are defined.", "Critical risks have evidence-backed mitigations or an escalation decision."),
            ("Engineering the next increment", ["Implement the risk-approved slice for " + focus, "Refine design against observed prototype results"], ["Engineering team", "QA engineer"], ["Integrated increment", "Risk mitigation evidence", "Updated design"], "Automated unit/integration suites and regression against mitigated risks.", "Risk response and iteration plan are approved.", "Increment passes engineering tests and risk controls are verified."),
            ("Stakeholder evaluation and next-cycle decision", ["Evaluate the increment with hotel/restaurant operations", "Reassess residual risks and select the next spiral"], ["Business owner", "Risk board", "Operations representatives"], ["Evaluation record", "Residual risk decision", "Next-spiral plan"], "Scenario-based user acceptance and recovery/security test review.", "An increment and its risk evidence are ready for review.", "Stakeholders accept the outcome or authorize another risk-driven cycle."),
        ],
        "V-Shaped (V-Model)": [
            ("Requirements and acceptance-test design", ["Baseline functional and non-functional requirements for " + focus, "Define acceptance scenarios and traceability"], ["Business analyst", "Business owner", "QA lead"], ["Approved requirement baseline", "Acceptance-test specification", "Traceability matrix"], "Acceptance test reviews against user and operational needs.", "Stakeholders and source evidence are available.", "Each requirement maps to a measurable acceptance check."),
            ("System architecture and system-test design", ["Specify system boundaries and integration contracts for " + integration_focus, "Design end-to-end availability and security verification"], ["System architect", "Security architect", "System test lead"], ["System specification", "System-test plan", "Interface control documents"], "Architecture review and system test design inspection.", "Requirements baseline is approved.", "System design is testable and traced to system acceptance criteria."),
            ("Detailed design and integration-test design", ["Define component interfaces and order/reservation data flows", "Prepare integration tests for partner and operational systems"], ["Technical lead", "Integration test lead"], ["Component design", "Integration-test specification", "Data-flow model"], "Interface walkthrough and integration-test coverage review.", "System design and partner interface details are stable.", "Components and integration cases are traceable to architecture."),
            ("Implementation and unit verification", ["Implement components with requirement and design references", "Review code and component boundaries"], ["Development team", "Code reviewers"], ["Versioned components", "Code review record", "Unit-test results"], "Static analysis, unit tests, and component-level security checks.", "Detailed design and coding standards are approved.", "Unit tests pass and component requirements are verified."),
            ("Integration verification", ["Assemble components and validate " + integration_focus, "Verify data exchange and error paths"], ["Integration engineer", "Integration QA"], ["Integrated system build", "Interface test report", "Defect log"], "Contract, integration, negative-path, and payment-failure tests.", "Unit-verified components and test environments are available.", "Interfaces behave to contract and critical integration defects are closed."),
            ("System verification and business validation", ["Execute traceable system and non-functional tests", "Obtain business acceptance for operational scenarios"], ["System QA lead", "Performance tester", "Operations owner"], ["System verification report", "Performance/security evidence", "Acceptance sign-off"], "Regression, measured load, access-control, availability, and user-acceptance tests.", "Integrated system passes integration exit criteria.", "All critical requirements pass their mapped tests and business accepts."),
        ],
        "Iterative": [
            ("Inception and architecture baseline", ["Define project boundary and risk-bearing workflows from " + focus, "Select an architecture that can evolve with stakeholder learning"], ["Product owner", "Architect", "Business analyst"], ["Initial vision", "Architecture baseline", "Iteration roadmap"], "Architecture feasibility spike and early acceptance scenarios.", "Problem statement and stakeholders are confirmed.", "First iteration scope and architecture risks are explicit."),
            ("Iteration planning and prototype", ["Choose a high-value slice and create a prototype", "Validate assumptions about " + integration_focus], ["Iteration lead", "UX designer", "Integration engineer"], ["Iteration plan", "Clickable or technical prototype", "Refined stories"], "Prototype usability checks and interface contract tests.", "Prioritized iteration backlog is available.", "Prototype findings have updated the backlog and design."),
            ("Build and verify iteration", ["Implement a working increment for " + focus, "Review each feature against its acceptance scenario"], ["Developers", "QA engineer", "Domain expert"], ["Working increment", "Iteration test report", "Updated trace links"], "Unit, integration, and focused regression tests for increment scope.", "Prototype and acceptance scenarios are reviewed.", "Increment passes its tests and is ready for stakeholder evaluation."),
            ("Evaluate and refine", ["Review the increment with staff and management", "Adjust estimates, scope, and architecture from observed feedback"], ["Product owner", "Operations staff", "Architect"], ["Evaluation notes", "Revised requirements", "Next iteration plan"], "Exploratory workflow testing and risk regression from prior iterations.", "A demonstrable increment is ready.", "Feedback and next-step decisions are accepted and recorded."),
            ("Stabilize and transition", ["Integrate validated iterations into a release candidate", "Complete operational documentation and support handoff"], ["Release lead", "QA lead", "Operations manager"], ["Release candidate", "Regression evidence", "Support handover"], "Full regression, recovery, security, and operational readiness testing.", "Required scope is implemented and open defects are triaged.", "Release gates pass and maintenance ownership is accepted."),
        ],
    }
    phase_templates = templates[model]
    phases = []
    for index, (name, activities, roles, deliverables, testing, entry, exit_criteria) in enumerate(phase_templates, 1):
        requirement = functional[min(index - 1, len(functional) - 1)] if functional else None
        if requirement and index in {2, 3}:
            activities = activities + [
                f"Maintain traceability to {requirement.get('requirement_id', 'requirement')}."
            ]
        phases.append({
            "phase": f"{index}. {name}",
            "activities": activities,
            "responsible_roles": roles,
            "deliverables": deliverables,
            "testing_strategy": testing,
            "review_checkpoints": [
                f"{model} checkpoint: {name} outputs meet the documented exit criteria.",
                f"Review evidence for {requirement.get('requirement_id', 'project requirements') if requirement else 'project requirements'}.",
            ],
            "entry_criteria": entry,
            "exit_criteria": exit_criteria,
            "expected_outcomes": f"{name} evidence for {analysis.get('project_name', 'the project')}.",
        })
    return phases
