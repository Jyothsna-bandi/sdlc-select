from io import BytesIO
import json
from pathlib import Path

import pymupdf
from docx import Document
from streamlit.testing.v1 import AppTest

from agents.requirement_agent import RequirementAnalysisAgent
from agents.sdlc_agent import SDLCRecommendationAgent
from core.document_processor import DocumentExtractionError, extract_document
from core.orchestrator import AnalysisOrchestrator
from core.requirement_classifier import classify_requirements
from core.scoring_engine import MODEL_GUIDANCE, MODEL_PROFILES, hybrid_approach, score_models
from utils.report_generator import generate_pdf_report
from utils.helpers import analysis_json, requirements_csv


HOTEL_TEXT = """Project Name: Boutique Hotel Reservation System
Overview: The system provides room reservations and front desk management.
Stakeholders: Guests, Front-desk staff, Hotel manager
The system shall allow a guest to search available rooms by date.
Search results must load within 3 seconds.
Booking information must be encrypted.
Requirements are stable after approval."""


def _pdf_bytes(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_txt_extraction_and_page_references():
    content = extract_document(b"First page\fSecond page", "requirements.txt")
    assert content.pages == ("First page", "Second page")
    assert content.file_type == "txt"


def test_pdf_extraction_preserves_pages():
    content = extract_document(_pdf_bytes("Reservation requirement"), "requirements.pdf")
    assert len(content.pages) == 1
    assert "Reservation requirement" in content.text


def test_docx_extraction():
    content = extract_document(_docx_bytes("Guests can reserve a room."), "requirements.docx")
    assert "Guests can reserve a room." in content.text
    assert content.pages[0] == content.text


def test_empty_and_unsupported_documents_are_rejected():
    for data, name in (
        (b"", "empty.txt"),
        (b"text", "requirements.rtf"),
        (b"\xff", "invalid-encoding.txt"),
        (b"not a pdf", "corrupt.pdf"),
        (b"not a docx", "corrupt.docx"),
    ):
        try:
            extract_document(data, name)
        except DocumentExtractionError:
            pass
        else:
            raise AssertionError("Invalid input should be rejected.")


def test_functional_and_nonfunctional_classification():
    result = classify_requirements(
        "Guests can cancel a reservation. The system shall load within 2 seconds."
    )
    assert len(result["functional_requirements"]) == 1
    assert result["non_functional_requirements"][0]["category"] == "Performance"


def test_requirement_quality_identifies_ambiguity_duplicates_and_gaps():
    text = (
        "The system should be fast and easy to use. "
        "The system should be fast and easy to use. "
        "Guests can reserve a room."
    )
    result = classify_requirements(text)
    assert result["ambiguities"]
    assert result["duplicate_requirements"]
    assert any(item["category"] == "Security" for item in result["missing_requirements"])


def test_agent_one_returns_json_ready_structured_output(monkeypatch):
    from core import llm_client

    monkeypatch.setattr(llm_client, "is_configured", lambda: False)
    result = RequirementAnalysisAgent().run(HOTEL_TEXT, (HOTEL_TEXT,))
    encoded = json.dumps(result)
    assert "Boutique Hotel Reservation System" in encoded
    assert result["project_domain"] == "Hospitality Management"
    assert result["functional_requirements"][0]["requirement_id"].startswith("FR-")
    assert result["functional_requirements"][0]["source_evidence"]
    assert result["analysis_mode"] == "rule-based fallback"


def test_agent_two_requires_agent_one_output():
    try:
        SDLCRecommendationAgent().run({"project_name": "Only"})
    except ValueError:
        pass
    else:
        raise AssertionError("Agent 2 must reject unrelated/incomplete input.")
    analysis = RequirementAnalysisAgent().run(HOTEL_TEXT)
    recommendation = SDLCRecommendationAgent().run(analysis)
    assert recommendation["source_project"] == analysis["project_name"]
    assert recommendation["agent_1_input_received"] is True


def test_scoring_returns_all_models_normalized():
    expected_models = [
        "Waterfall",
        "V-Shaped (V-Model)",
        "Prototype",
        "RAD (Rapid Application Development)",
        "Spiral",
        "Iterative",
        "Agile",
    ]
    analysis = RequirementAnalysisAgent().run(HOTEL_TEXT)
    scores = score_models(analysis)
    assert list(MODEL_PROFILES) == expected_models
    assert list(MODEL_GUIDANCE) == expected_models
    assert [item["model"] for item in scores] == expected_models
    assert len({item["model"] for item in scores}) == 7
    assert all(item["suitability"] and item["advantages"] and item["disadvantages"] for item in scores)
    assert all(0 <= item["score"] <= 100 for item in scores)


def test_each_sdlc_model_has_a_distinct_workflow_and_hybrid_is_not_an_eighth_model():
    from agents.sdlc_agent import _workflow

    analysis = RequirementAnalysisAgent().run(HOTEL_TEXT)
    recommendation = SDLCRecommendationAgent().run(analysis)
    ranked_models = [item["model"] for item in recommendation["ranked_comparison"]]
    assert len(ranked_models) == 7
    assert set(ranked_models) == set(MODEL_PROFILES)
    assert [item["model"] for item in recommendation["model_scores"]] == list(MODEL_PROFILES)
    assert recommendation["recommended_model"] in MODEL_PROFILES
    assert len(recommendation["hybrid_approach"]["models"]) <= 2
    assert "Hybrid" not in MODEL_PROFILES
    assert "DevOps" not in MODEL_PROFILES
    assert all(model in MODEL_PROFILES for model in recommendation["hybrid_approach"]["models"])
    for model in MODEL_PROFILES:
        workflow = _workflow(model, analysis)
        assert workflow
        assert all(phase["activities"] and phase["testing_strategy"] for phase in workflow)


def test_hybrid_option_requires_close_scores_and_complementary_characteristic_fit():
    analysis = {
        "requirement_stability": "Low",
        "change_frequency": "Low",
        "project_complexity": "High",
        "security_risk": "High",
        "project_size": "Medium",
        "stakeholders": ["manager", "staff", "guest", "finance"],
        "functional_requirements": [{}] * 6,
        "non_functional_requirements": [
            {"category": "security"},
            {"category": "performance"},
            {"category": "availability"},
        ],
        "technical_requirements": [],
    }
    scores = score_models(analysis)
    hybrid = hybrid_approach(scores, analysis)
    assert hybrid["recommended"] is True
    assert len(hybrid["models"]) == 2
    assert all(model in MODEL_PROFILES for model in hybrid["models"])
    assert len(scores) == 7

    scores[0]["score"] = 100
    scores[1]["score"] = 0
    assert hybrid_approach(scores, analysis)["recommended"] is False


def test_best_model_is_selected_from_programmatic_ranking():
    analysis = RequirementAnalysisAgent().run(HOTEL_TEXT)
    result = SDLCRecommendationAgent().run(analysis)
    expected = max(result["model_scores"], key=lambda item: item["score"])["model"]
    assert result["recommended_model"] == expected


def test_orchestrator_passes_agent_one_output_to_agent_two():
    orchestrator = AnalysisOrchestrator()
    captured = []
    original_run = orchestrator.sdlc_agent.run

    def run_after_agent1(message):
        assert message["sender"] == "requirement_engineering_agent"
        assert message["recipient"] == "sdlc_intelligence_agent"
        assert message["content"] is captured[0]
        return original_run(message)

    orchestrator.sdlc_agent.run = run_after_agent1
    result = orchestrator.analyze(
        HOTEL_TEXT.encode(),
        "hotel.txt",
        on_requirements_analyzed=captured.append,
    )
    assert captured[0] is result["requirement_analysis"]
    assert result["sdlc_recommendation"]["source_project"] == result["requirement_analysis"]["project_name"]
    assert result["final_recommendation"] == result["sdlc_recommendation"]["recommended_model"]
    assert result["agent_messages"][0]["message_type"] == "validated_requirements"
    assert [event["event"] for event in result["audit_log"]][-2:] == [
        "agent1_to_agent2_handoff",
        "agent2_completed",
    ]
    json.dumps(result)


def test_coordinator_waits_for_human_approval_and_records_rejection():
    orchestrator = AnalysisOrchestrator()
    calls = []
    original_run = orchestrator.sdlc_agent.run

    def capture_message(message):
        calls.append(message)
        return original_run(message)

    orchestrator.sdlc_agent.run = capture_message

    pending = orchestrator.begin_analysis(HOTEL_TEXT.encode(), "hotel.txt")
    assert pending["status"] == "awaiting_human_approval"
    assert pending["requirement_analysis"]["validation"]["status"] == "validated"
    assert calls == []

    rejected = orchestrator.approve_and_recommend(pending, approved=False, approver="reviewer")
    assert rejected["status"] == "approval_rejected"
    assert calls == []
    assert rejected["audit_log"][-1]["event"] == "requirements_rejected"

    pending = orchestrator.begin_analysis(HOTEL_TEXT.encode(), "hotel.txt")
    approved = orchestrator.approve_and_recommend(pending, approved=True, approver="reviewer")
    assert approved["status"] == "completed"
    assert calls[0]["content"] is pending["requirement_analysis"]
    assert calls[0]["trace_id"] == pending["trace_id"]


def test_coordinator_records_stakeholder_input_without_promoting_it_to_a_requirement():
    orchestrator = AnalysisOrchestrator()
    context = orchestrator.begin_analysis(HOTEL_TEXT.encode(), "hotel.txt")
    requirement_count = context["requirement_analysis"]["validation"]["requirement_count"]
    orchestrator.record_stakeholder_interaction(
        context,
        "Front-desk manager",
        "Please clarify how late cancellations should be handled.",
    )
    interaction = context["requirement_analysis"]["stakeholder_interactions"][0]
    assert interaction["status"] == "captured_unvalidated"
    assert interaction["handled_by"] == "requirement_engineering_agent"
    assert context["requirement_analysis"]["validation"]["requirement_count"] == requirement_count
    assert context["audit_log"][-1]["event"] == "stakeholder_input_recorded"


def test_agent_two_runs_security_compliance_and_local_retrieval_modules():
    sample = Path("sample_documents") / "Restaurant Management System.txt"
    analysis = RequirementAnalysisAgent().run(sample.read_text(encoding="utf-8"))
    recommendation = SDLCRecommendationAgent().run(analysis)
    assert recommendation["security_privacy_analysis"]["risk_level"] == "High"
    assert recommendation["hospitality_compliance_assessment"]["assessment_type"] == "hospitality compliance screening"
    assert recommendation["operational_technical_risks"]
    retrieved = recommendation["retrieved_hospitality_knowledge"]
    assert retrieved
    assert all(item["source_id"] and item["matched_terms"] for item in retrieved)


def test_report_generation_returns_pdf():
    result = AnalysisOrchestrator().analyze(HOTEL_TEXT.encode(), "hotel.txt")
    pdf = generate_pdf_report(result["requirement_analysis"], result["sdlc_recommendation"])
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_three_sample_documents_run_end_to_end_and_have_distinct_profiles():
    profiles = []
    expected_counts = {
        "Hotel Reservation Management System.txt": (5, 4, 2, 2),
        "Restaurant Management System.txt": (6, 4, 2, 2),
        "Resort Management System.txt": (8, 6, 3, 3),
    }
    for path in sorted(Path("sample_documents").glob("*.txt")):
        result = AnalysisOrchestrator().analyze(path.read_bytes(), path.name)
        analysis = result["requirement_analysis"]
        recommendation = result["sdlc_recommendation"]
        profiles.append(analysis["change_frequency"])
        assert (
            len(analysis["functional_requirements"]),
            len(analysis["non_functional_requirements"]),
            len(analysis["technical_requirements"]),
            len(analysis["constraints"]),
        ) == expected_counts[path.name]
        assert recommendation["agent_1_input_received"]
        assert len(recommendation["model_scores"]) == 7
        exported = json.loads(analysis_json(result))
        exported_models = [
            item["model"] for item in exported["sdlc_recommendation"]["model_scores"]
        ]
        assert exported_models == list(MODEL_PROFILES)
        assert len(set(exported_models)) == 7
        assert result["final_recommendation"] in MODEL_PROFILES
        assert analysis_json(result)
        assert requirements_csv(analysis)
    assert len(set(profiles)) > 1


def test_restaurant_requirements_keep_ids_evidence_types_and_document_derived_characteristics():
    sample = Path("sample_documents") / "Restaurant Management System.txt"
    captured = []
    result = AnalysisOrchestrator().analyze(
        sample.read_bytes(),
        sample.name,
        on_requirements_analyzed=captured.append,
    )
    analysis = result["requirement_analysis"]
    recommendation = result["sdlc_recommendation"]
    assert captured[0] is analysis
    assert recommendation["source_project"] == analysis["project_name"]

    functional = analysis["functional_requirements"]
    non_functional = analysis["non_functional_requirements"]
    assert [item["requirement_id"] for item in functional] == [f"FR-{number:02d}" for number in range(1, 7)]
    assert [item["requirement_id"] for item in non_functional] == [f"NFR-{number:02d}" for number in range(1, 5)]
    assert len(analysis["technical_requirements"]) == 2
    assert len(analysis["constraints"]) == 2
    assert all(item["source_evidence"] for item in functional + non_functional)
    assert all(item["source_evidence"] for item in analysis["technical_requirements"] + analysis["constraints"])
    assert {item["requirement_id"]: item["category"] for item in non_functional} == {
        "NFR-01": "Performance",
        "NFR-02": "Security",
        "NFR-03": "Performance",
        "NFR-04": "Availability",
    }

    characteristics = recommendation["project_characteristics"]
    assert characteristics["availability_requirements"] is True
    assert characteristics["security_risk"] == "High"
    assert characteristics["performance_requirements"] is True
    assert characteristics["integration_requirements"] is True
    assert characteristics["change_frequency"] == "High"
    assert characteristics["stakeholder_involvement"] == "High"
    assert len(recommendation["model_scores"]) == 7
    assert recommendation["recommended_model"] == max(
        recommendation["model_scores"], key=lambda item: item["score"]
    )["model"]
    assert analysis["missing_requirements"]
    assert all(item["origin"] == "inferred_gap" for item in analysis["missing_requirements"])
    assert analysis["improvement_recommendations"]
    assert all(item["origin"] == "recommendation" for item in analysis["improvement_recommendations"])


def test_recommended_workflow_has_phase_specific_details_and_pdf_wraps_long_text():
    sample = Path("sample_documents") / "Restaurant Management System.txt"
    result = AnalysisOrchestrator().analyze(sample.read_bytes(), sample.name)
    analysis = result["requirement_analysis"]
    recommendation = result["sdlc_recommendation"]
    workflow = recommendation["workflow"]

    for field in ("activities", "responsible_roles", "deliverables", "testing_strategy", "entry_criteria", "exit_criteria", "review_checkpoints"):
        values = [
            tuple(phase[field]) if isinstance(phase[field], list) else phase[field]
            for phase in workflow
        ]
        assert all(values)
        assert len(set(values)) == len(values), f"{field} should vary by workflow phase"

    long_text = "FR-01 " + ("Reservation details remain readable when wrapped across report lines. " * 45) + "LONG_REQUIREMENT_END_MARKER"
    analysis["functional_requirements"][0]["description"] = long_text
    analysis["functional_requirements"][0]["source_evidence"] = long_text
    pdf = generate_pdf_report(analysis, recommendation)
    document = pymupdf.open(stream=pdf, filetype="pdf")
    extracted = "\n".join(page.get_text() for page in document)
    assert len(document) > 1
    assert "LONG_REQUIREMENT_END_MARKER" in extracted
    assert "FR-01" in extracted and "NFR-04" in extracted and "TR-01" in extracted
    assert "Existing point-of-sale terminals must remain operational during rollout." in extracted
    assert "Security and privacy screening" in extracted
    assert "Hospitality compliance screening" in extracted
    assert "Operational and technical risks" in extracted
    assert "Retrieved hospitality guidance" in extracted
    assert all(model in extracted for model in MODEL_PROFILES)
    assert "DevOps" not in extracted
    assert "Confidential project analysis - validate findings with stakeholders" in extracted
    for page in document:
        for block in page.get_text("blocks"):
            assert block[0] >= 0 and block[1] >= 0
            assert block[2] <= page.rect.width + 0.5
            assert block[3] <= page.rect.height + 0.5


def test_streamlit_analyse_button_runs_both_agents_and_preserves_navigation_state():
    project_root = Path(__file__).resolve().parents[1]
    sample = project_root / "sample_documents" / "Hotel Reservation Management System.txt"
    app = AppTest.from_file(str(project_root / "app.py")).run(timeout=30)
    app.radio[0].set_value("Document Upload").run(timeout=30)
    app.file_uploader[0].set_value((sample.name, sample.read_bytes(), "text/plain")).run(timeout=30)
    app.button[0].click().run(timeout=30)

    assert not app.exception
    agent1 = app.session_state["agent1_output"]
    assert agent1["project_name"] == "Hotel Reservation Management System"
    assert agent1["functional_requirements"]
    assert agent1["non_functional_requirements"]
    assert agent1["ambiguities"]
    assert agent1["missing_requirements"]
    assert agent1["validation"]["status"] == "validated"
    assert app.session_state["agent2_output"] is None
    assert app.session_state["analysis_context"]["status"] == "awaiting_human_approval"

    next(button for button in app.button if button.label == "Approve requirements and run Agent 2").click().run(timeout=30)
    assert not app.exception
    agent2 = app.session_state["agent2_output"]
    assert agent2["source_project"] == agent1["project_name"]
    assert agent2["agent1_message"]["sender"] == "requirement_engineering_agent"
    assert len(agent2["model_scores"]) == 7
    assert agent2["recommended_model"] == max(
        agent2["model_scores"], key=lambda item: item["score"]
    )["model"]

    app.radio[0].set_value("SDLC Recommendation").run(timeout=30)
    assert not app.exception
    assert app.session_state["agent1_output"] == agent1
    assert app.session_state["agent2_output"] == agent2
    assert any("Recommended:" in markdown.value for markdown in app.markdown)
