"""Coordinates extraction, both agents, scoring, and report-ready results."""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Callable
from uuid import uuid4

from agents.requirement_agent import RequirementAnalysisAgent
from agents.sdlc_agent import SDLCRecommendationAgent
class AnalysisOrchestrator:
    """Central coordinator for validated Agent 1 output and Agent 2 handoff."""

    def __init__(self) -> None:
        self.requirement_agent = RequirementAnalysisAgent()
        self.sdlc_agent = SDLCRecommendationAgent()

    def begin_analysis(
        self,
        content: bytes,
        filename: str,
        on_requirements_analyzed: Callable[[dict], None] | None = None,
    ) -> dict:
        trace_id = str(uuid4())
        audit_log = [_audit_event("analysis_started", "coordinator", trace_id)]
        document, requirement_result = self.requirement_agent.process_document(content, filename)
        audit_log.append(_audit_event("document_extracted", "coordinator", trace_id))
        requirement_result["source_document"] = document.filename
        if requirement_result.get("validation", {}).get("status") != "validated":
            audit_log.append(_audit_event("agent1_validation_failed", "requirement_engineering_agent", trace_id))
            raise ValueError(
                "Agent 1 output failed structured validation: "
                + "; ".join(requirement_result.get("validation", {}).get("errors", []))
            )
        audit_log.append(_audit_event("agent1_output_validated", "requirement_engineering_agent", trace_id))
        if on_requirements_analyzed is not None:
            on_requirements_analyzed(requirement_result)
        return {
            "trace_id": trace_id,
            "document": asdict(document),
            "requirement_analysis": requirement_result,
            "status": "awaiting_human_approval",
            "agent_messages": [],
            "audit_log": audit_log,
        }

    def approve_and_recommend(
        self,
        shared_context: dict,
        approved: bool,
        approver: str = "human reviewer",
    ) -> dict:
        if (
            not isinstance(shared_context, dict)
            or shared_context.get("status") != "awaiting_human_approval"
            or not isinstance(shared_context.get("requirement_analysis"), dict)
        ):
            raise ValueError("Coordinator requires a pending, shared Agent 1 analysis context.")
        if not approved:
            shared_context["status"] = "approval_rejected"
            shared_context["audit_log"].append(
                _audit_event("requirements_rejected", approver, shared_context["trace_id"])
            )
            return shared_context

        requirement_output = shared_context["requirement_analysis"]
        if requirement_output.get("validation", {}).get("status") != "validated":
            raise ValueError("Agent 2 handoff requires Agent 1's validated output.")
        message = {
            "sender": "requirement_engineering_agent",
            "recipient": "sdlc_intelligence_agent",
            "message_type": "validated_requirements",
            "trace_id": shared_context["trace_id"],
            "content": requirement_output,
        }
        message_audit = _audit_event(
            "agent1_to_agent2_handoff",
            "coordinator",
            shared_context["trace_id"],
            details={
                "sender": message["sender"],
                "recipient": message["recipient"],
                "message_type": message["message_type"],
                "payload_sha256": hashlib.sha256(
                    json.dumps(requirement_output, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
            },
        )
        shared_context["agent_messages"].append(message_audit["details"])
        shared_context["audit_log"].extend([
            _audit_event("requirements_approved", approver, shared_context["trace_id"]),
            message_audit,
        ])
        shared_context["status"] = "agent2_running"
        try:
            recommendation = self.sdlc_agent.run(message)
        except (RuntimeError, ValueError, TypeError) as error:
            shared_context["status"] = "agent2_failed"
            shared_context["audit_log"].append(
                _audit_event("agent2_failed", "sdlc_intelligence_agent", shared_context["trace_id"],
                             details={"error_type": type(error).__name__})
            )
            raise
        shared_context["audit_log"].append(
            _audit_event("agent2_completed", "sdlc_intelligence_agent", shared_context["trace_id"])
        )
        shared_context["status"] = "completed"
        shared_context["sdlc_recommendation"] = recommendation
        shared_context["final_recommendation"] = recommendation["recommended_model"]
        return shared_context

    def record_stakeholder_interaction(
        self,
        shared_context: dict,
        stakeholder: str,
        interaction: str,
    ) -> dict:
        if (
            not isinstance(shared_context, dict)
            or shared_context.get("status") != "awaiting_human_approval"
            or not isinstance(shared_context.get("requirement_analysis"), dict)
        ):
            raise ValueError("Stakeholder input can only be recorded during Agent 1 review.")
        recorded = self.requirement_agent.record_stakeholder_interaction(
            shared_context["requirement_analysis"],
            stakeholder,
            interaction,
        )
        interactions = shared_context["requirement_analysis"].setdefault("stakeholder_interactions", [])
        if any(
            item.get("stakeholder") == recorded["stakeholder"] and item.get("input") == recorded["input"]
            for item in interactions
        ):
            raise ValueError("This stakeholder input has already been recorded.")
        interactions.append(recorded)
        shared_context["audit_log"].append(
            _audit_event(
                "stakeholder_input_recorded",
                "requirement_engineering_agent",
                shared_context["trace_id"],
                details={
                    "stakeholder": recorded["stakeholder"],
                    "input_characters": len(recorded["input"]),
                    "status": recorded["status"],
                },
            )
        )
        return shared_context

    def analyze(
        self,
        content: bytes,
        filename: str,
        on_requirements_analyzed: Callable[[dict], None] | None = None,
    ) -> dict:
        shared_context = self.begin_analysis(content, filename, on_requirements_analyzed)
        shared_context = self.approve_and_recommend(
            shared_context,
            approved=True,
            approver="automatic compatibility flow",
        )
        return {
            "document": shared_context["document"],
            "requirement_analysis": shared_context["requirement_analysis"],
            "sdlc_recommendation": shared_context["sdlc_recommendation"],
            "final_recommendation": shared_context["final_recommendation"],
            "trace_id": shared_context["trace_id"],
            "agent_messages": shared_context["agent_messages"],
            "audit_log": shared_context["audit_log"],
        }


def _audit_event(event: str, actor: str, trace_id: str, details: dict | None = None) -> dict:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "actor": actor,
        "event": event,
        "details": details or {},
    }
