"""HospitaLytics Streamlit application."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import APP_NAME, LLM_API_KEY, MAX_UPLOAD_BYTES, PROJECT_ROOT, TAGLINE
from core.document_processor import DocumentExtractionError, extract_document
from core.orchestrator import AnalysisOrchestrator
from utils.helpers import analysis_json, requirements_csv
from utils.report_generator import generate_pdf_report


st.set_page_config(page_title=APP_NAME, page_icon="🏨", layout="wide")
st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: #F3F7F8 !important;
        color: #163746 !important;
    }
    [data-testid="stHeader"] { background: rgba(243, 247, 248, .96) !important; }
    [data-testid="stMainBlockContainer"] { padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li, [data-testid="stCaptionContainer"],
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
    label, .stText, .stMarkdown { color: #243F4B !important; }
    h1, h2, h3, h4, h5, h6,
    [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4 {
        color: #102F40 !important;
        letter-spacing: -0.02em;
    }
    [data-testid="stSidebar"] {
        background: #102A3A !important;
        border-right: 1px solid #244554;
    }
    [data-testid="stSidebar"] * { color: #E8F1F3; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #D0E0E4 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
    [data-testid="stSidebar"] label:not([data-selected="true"]) {
        color: #D0E0E4 !important;
    }
    [data-testid="stSidebar"] [data-testid="stAlertContainer"] {
        background: #16414E !important;
        border: 1px solid #34717B !important;
    }
    [data-testid="stSidebar"] [data-testid="stAlertContainer"] * { color: #F4FBFC !important; }
    .sidebar-status {
        margin-top: .8rem;
        padding: .8rem .9rem;
        color: #F4FBFC !important;
        background: #16414E;
        border: 1px solid #34717B;
        border-radius: 10px;
        font-size: .9rem;
        line-height: 1.45;
    }
    [data-testid="stSidebar"] [role="radiogroup"] [data-selected="true"] {
        background: #0F766E !important;
        border-radius: 9px;
    }
    [data-testid="stSidebar"] [role="radiogroup"] [data-selected="true"] * {
        color: #FFFFFF !important;
        font-weight: 650;
    }
    [data-testid="stSidebar"] [role="radiogroup"] [data-selected="false"]:hover {
        background: #1A3E50 !important;
        border-radius: 9px;
    }
    [data-testid="stSidebar"] hr { border-color: #345362; }
    .hero {
        padding: 2.4rem 2.6rem;
        border: 1px solid #1B6C70;
        border-radius: 20px;
        color: #FFFFFF !important;
        background: linear-gradient(120deg, #0E766E 0%, #12465B 72%, #102F40 100%);
        box-shadow: 0 14px 34px rgba(16, 47, 64, .16);
    }
    .hero h1 { color: #FFFFFF !important; font-size: 2.85rem; margin: 0 0 .35rem; }
    .hero p { color: #E8F5F3 !important; font-size: 1.12rem; margin: 0; }
    [data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        background: #FFFFFF;
        border: 1px solid #DCE7E9;
        border-radius: 12px;
        box-shadow: 0 3px 12px rgba(16, 47, 64, .04);
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color: #4B6470 !important; }
    [data-testid="stMetricValue"] { color: #102F40 !important; }
    div[data-testid="stExpander"] {
        background: #FFFFFF;
        border: 1px solid #D5E2E5;
        border-radius: 12px;
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary p { color: #163746 !important; font-weight: 600; }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        background: #FFFFFF;
        border: 1px solid #D5E2E5;
        border-radius: 10px;
    }
    .stTextArea textarea, [data-testid="stTextArea"] textarea {
        min-height: 300px;
        padding: 1rem;
        background: #FFFFFF !important;
        color: #183744 !important;
        -webkit-text-fill-color: #183744 !important;
        opacity: 1 !important;
        border: 1px solid #AFC7CC !important;
        border-radius: 10px !important;
        font-family: "Cascadia Code", "Consolas", monospace !important;
        font-size: .92rem !important;
        line-height: 1.65 !important;
    }
    .stTextArea textarea:focus {
        border-color: #0F766E !important;
        box-shadow: 0 0 0 2px rgba(15, 118, 110, .16) !important;
    }
    input, [data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #183744 !important;
        border-color: #B7C9CE !important;
    }
    input::placeholder, textarea::placeholder { color: #627983 !important; opacity: 1; }
    [data-testid="stFileUploader"] section {
        background: #FFFFFF;
        border: 1px dashed #7BA6A9;
        border-radius: 14px;
    }
    [data-testid="stFileUploader"] section * { color: #294A56 !important; }
    [data-testid="stFileUploader"] button {
        background: #FFFFFF !important;
        color: #145A5C !important;
        border: 1px solid #7BA6A9 !important;
    }
    div.stButton > button, div.stDownloadButton > button {
        min-height: 2.6rem;
        padding: .55rem 1.1rem;
        color: #123543 !important;
        background: #FFFFFF !important;
        border: 1px solid #92AFB5 !important;
        border-radius: 9px !important;
        font-weight: 650 !important;
        transition: background .15s ease, box-shadow .15s ease, transform .15s ease;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        color: #FFFFFF !important;
        background: #145C68 !important;
        border-color: #145C68 !important;
        box-shadow: 0 4px 12px rgba(16, 47, 64, .16);
    }
    div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] {
        color: #FFFFFF !important;
        background: #0F766E !important;
        border-color: #0F766E !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stDownloadButton > button[kind="primary"]:hover {
        color: #FFFFFF !important;
        background: #0B5F5A !important;
        border-color: #0B5F5A !important;
    }
    div.stButton > button[kind="primary"] *,
    div.stDownloadButton > button[kind="primary"] *,
    div.stButton > button:hover *,
    div.stDownloadButton > button:hover * {
        color: #FFFFFF !important;
    }
    div.stButton > button:focus, div.stDownloadButton > button:focus {
        box-shadow: 0 0 0 3px rgba(15, 118, 110, .24) !important;
        outline: none !important;
    }
    [data-testid="stAlert"] { border-radius: 10px; }
    [data-testid="stPlotlyChart"] {
        padding: .5rem;
        background: #FFFFFF;
        border: 1px solid #DCE7E9;
        border-radius: 12px;
    }
    @media (max-width: 720px) {
        .hero { padding: 1.5rem; }
        .hero h1 { font-size: 2.2rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

for key, default in {
    "analysis_result": None,
    "analysis_context": None,
    "agent1_output": None,
    "agent2_output": None,
    "document_bytes": None,
    "document_name": None,
    "extracted": None,
    "analysis_error": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def _run_analysis(content: bytes, filename: str) -> None:
    st.session_state.analysis_error = None
    st.session_state.analysis_result = None
    st.session_state.analysis_context = None
    st.session_state.agent1_output = None
    st.session_state.agent2_output = None
    try:
        context = AnalysisOrchestrator().begin_analysis(content, filename)
    except (DocumentExtractionError, RuntimeError, ValueError) as error:
        st.session_state.analysis_error = str(error)
        st.session_state.agent2_output = None
        return
    st.session_state.analysis_context = context
    st.session_state.agent1_output = context["requirement_analysis"]


def _approve_requirements() -> None:
    context = st.session_state.analysis_context
    try:
        completed = AnalysisOrchestrator().approve_and_recommend(
            context,
            approved=True,
            approver="streamlit_user",
        )
    except (RuntimeError, ValueError, TypeError) as error:
        st.session_state.analysis_error = str(error)
        return
    st.session_state.analysis_context = completed
    st.session_state.analysis_result = {
        "document": completed["document"],
        "requirement_analysis": completed["requirement_analysis"],
        "sdlc_recommendation": completed["sdlc_recommendation"],
        "final_recommendation": completed["final_recommendation"],
        "trace_id": completed["trace_id"],
        "agent_messages": completed["agent_messages"],
        "audit_log": completed["audit_log"],
    }
    st.session_state.agent1_output = completed["requirement_analysis"]
    st.session_state.agent2_output = completed["sdlc_recommendation"]


def _reject_requirements() -> None:
    context = st.session_state.analysis_context
    try:
        st.session_state.analysis_context = AnalysisOrchestrator().approve_and_recommend(
            context,
            approved=False,
            approver="streamlit_user",
        )
    except (RuntimeError, ValueError, TypeError) as error:
        st.session_state.analysis_error = str(error)


if st.session_state.get("pending_page"):
    st.session_state.nav_page = st.session_state.pop("pending_page")

pages = ["Home", "Document Upload", "Requirement Analysis", "SDLC Recommendation", "SDLC Workflow", "Report Generation"]
selected_page = st.sidebar.radio("Navigate", pages, key="nav_page")
st.sidebar.divider()
st.sidebar.caption("Two-agent decision support for hospitality software.")
st.sidebar.markdown(f"**Analysis mode:** {'LLM-enhanced available' if LLM_API_KEY else 'Rule-based fallback'}")
if st.session_state.analysis_result:
    st.sidebar.markdown(
        '<div class="sidebar-status">Analysis results are saved for this session.</div>',
        unsafe_allow_html=True,
    )
elif st.session_state.analysis_context and st.session_state.analysis_context.get("status") == "awaiting_human_approval":
    st.sidebar.markdown(
        '<div class="sidebar-status">Agent 1 results are awaiting your approval.</div>',
        unsafe_allow_html=True,
    )
elif st.session_state.analysis_context and st.session_state.analysis_context.get("status") == "approval_rejected":
    st.sidebar.markdown(
        '<div class="sidebar-status">Agent 1 requirements were rejected; review or re-analyse the document.</div>',
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        '<div class="sidebar-status">Upload a document to begin.</div>',
        unsafe_allow_html=True,
    )


def _require_analysis():
    if (
        st.session_state.analysis_result is not None
        and st.session_state.agent1_output is not None
        and st.session_state.agent2_output is not None
    ):
        return st.session_state.analysis_result
    return None


def _show_requirements(items: list[dict]) -> None:
    if not items:
        st.info("No explicit requirements in this category were identified.")
        return
    table = pd.DataFrame([{
        "ID": item.get("requirement_id", ""),
        "Description": item["description"],
        "Category": item.get("category", ""),
        "Priority": item.get("priority", ""),
        "Evidence": item.get("source_evidence", ""),
        "Page": str(item["page_reference"]) if item.get("page_reference") is not None else "—",
        "Confidence": f"{item.get('confidence_score', 0):.0%}",
        "Origin": item.get("origin", "explicit"),
    } for item in items])
    st.dataframe(table, use_container_width=True, hide_index=True)


def _show_list(title: str, items: list) -> None:
    if title:
        st.markdown(f"#### {title}")
    if not items:
        st.caption("None identified.")
        return
    for item in items:
        if isinstance(item, dict):
            text = item.get("description", item.get("input", json.dumps(item, ensure_ascii=False)))
            if item.get("stakeholder"):
                text = f"{item['stakeholder']}: {text}"
            if item.get("reason"):
                text += f" — {item['reason']}"
            if item.get("source_evidence"):
                text += f" (source: {item['source_evidence']})"
            if item.get("origin") == "recommendation":
                text = f"Recommendation: {text}"
            elif item.get("origin") == "inferred_gap":
                text = f"Inferred gap: {text}"
        else:
            text = str(item)
        st.markdown(f"- {text}")


def _metric_row(metrics: list[tuple[str, str]]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value) in zip(columns, metrics):
        column.metric(label, value)


if selected_page == "Home":
    st.markdown(f'<div class="hero"><h1>{APP_NAME}</h1><p>{TAGLINE}</p></div>', unsafe_allow_html=True)
    st.write("")
    st.markdown("### From hospitality requirements to an actionable SDLC recommendation")
    st.write(
        "HospitaLytics processes an uploaded hospitality software requirements document, identifies "
        "requirements and quality gaps, then compares seven development life-cycle models using a "
        "transparent deterministic scoring engine."
    )
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("#### Agent 1 · Requirement Analysis")
            st.write("Extracts functional, non-functional, and technical requirements, evidence, project characteristics, and clarification questions.")
    with right:
        with st.container(border=True):
            st.markdown("#### Agent 2 · SDLC Intelligence")
            st.write("Consumes Agent 1's approved output, screens security, privacy, compliance and risks, retrieves hospitality guidance, scores all seven models, and creates a tailored workflow.")
    st.markdown("#### Supported documents")
    st.write("PDF · DOCX · TXT  |  Up to 20 MB  |  Multi-page PDF text with page references")
    st.markdown("#### How it works")
    st.write("Upload → Extract → Analyze requirements → Score SDLC models → Review workflow → Download report")
    if st.button("Start Analysis", type="primary"):
        st.session_state.pending_page = "Document Upload"
        st.rerun()
    st.markdown("#### Included examples")
    sample_names = ["Hotel Reservation Management System.txt", "Restaurant Management System.txt", "Resort Management System.txt"]
    cols = st.columns(3)
    for column, sample in zip(cols, sample_names):
        column.info(sample)

elif selected_page == "Document Upload":
    st.title("Document Upload")
    upload = st.file_uploader(
        "Upload a hospitality SRS or requirement document",
        type=["pdf", "docx", "txt"],
        key="requirements_upload",
    )
    if upload is not None:
        content = upload.getvalue()
        filename = upload.name
        if content != st.session_state.document_bytes or filename != st.session_state.document_name:
            st.session_state.document_bytes = content
            st.session_state.document_name = filename
            st.session_state.analysis_result = None
            st.session_state.analysis_context = None
            st.session_state.agent1_output = None
            st.session_state.agent2_output = None
            st.session_state.extracted = None
            st.session_state.analysis_error = None
            st.session_state["stakeholder_role"] = "Project stakeholder"
            st.session_state["stakeholder_response"] = ""
    else:
        content = st.session_state.document_bytes
        filename = st.session_state.document_name

    if content is not None and filename:
        st.write(f"**File:** {filename} · **Size:** {len(content) / 1024:.1f} KB · **Format:** {Path(filename).suffix[1:].upper()}")
        if len(content) > MAX_UPLOAD_BYTES:
            st.error("File exceeds the 20 MB upload limit.")
        else:
            try:
                extracted = extract_document(content, filename)
                st.session_state.extracted = extracted
                st.success(f"Extracted {len(extracted.pages)} page(s) of text.")
                with st.expander("Preview extracted text", expanded=True):
                    st.text_area("Document text", extracted.text[:12000], height=300, disabled=True)
                if st.session_state.analysis_error:
                    st.error(st.session_state.analysis_error)
                elif st.session_state.analysis_result:
                    st.success("Both agents completed successfully. Results are saved for this session.")
                elif st.session_state.analysis_context and st.session_state.analysis_context.get("status") == "awaiting_human_approval":
                    analysis = st.session_state.analysis_context["requirement_analysis"]
                    st.info(
                        f"Agent 1 validated {analysis['validation']['requirement_count']} structured items. "
                        "Review the extracted requirements before authorizing Agent 2."
                    )
                    with st.expander("Review Agent 1 requirements before approval", expanded=True):
                        _show_requirements(analysis["functional_requirements"])
                        _show_requirements(analysis["non_functional_requirements"])
                        _show_list("Technical requirements", analysis["technical_requirements"])
                        _show_list("Constraints", analysis["constraints"])
                    with st.form("stakeholder_input_form", clear_on_submit=True):
                        stakeholder = st.text_input("Stakeholder or role", value="Project stakeholder")
                        interaction = st.text_area(
                            "Clarification or requirement input",
                            help="Captured by Agent 1 as unvalidated stakeholder input; it is not automatically treated as an approved requirement.",
                        )
                        record_input = st.form_submit_button("Record stakeholder input")
                    if record_input:
                        try:
                            st.session_state.analysis_context = AnalysisOrchestrator().record_stakeholder_interaction(
                                st.session_state.analysis_context,
                                stakeholder,
                                interaction,
                            )
                            st.session_state.agent1_output = st.session_state.analysis_context["requirement_analysis"]
                            st.success("Stakeholder input recorded for Agent 1 review.")
                        except ValueError as error:
                            st.error(str(error))
                    _show_list("Captured stakeholder input (not yet validated as requirements)", analysis.get("stakeholder_interactions", []))
                    st.button(
                        "Approve requirements and run Agent 2",
                        type="primary",
                        key="approve_agent1_output",
                        on_click=_approve_requirements,
                    )
                    st.button(
                        "Reject requirements",
                        key="reject_agent1_output",
                        on_click=_reject_requirements,
                    )
                st.button(
                    "Analyse Document",
                    type="primary",
                    key="analyse_document",
                    on_click=_run_analysis,
                    args=(content, filename),
                )
            except DocumentExtractionError as error:
                st.error(str(error))
            except RuntimeError as error:
                st.error(str(error))
    else:
        st.caption("Upload a document to inspect its extracted text before analysis.")
    with st.expander("Try a sample requirement document"):
        samples = sorted((PROJECT_ROOT / "sample_documents").glob("*.txt"))
        for sample in samples:
            st.download_button(sample.name, sample.read_bytes(), file_name=sample.name, mime="text/plain")

elif selected_page == "Requirement Analysis":
    st.title("Requirement Analysis · Agent 1")
    result = _require_analysis()
    if result:
        analysis = result["requirement_analysis"]
    else:
        analysis = st.session_state.agent1_output
    if analysis:
        if result:
            st.success(f"Agent 1 complete · Mode: {analysis['analysis_mode']} · Confidence: {analysis['confidence_score']:.0%}")
        elif st.session_state.analysis_context and st.session_state.analysis_context.get("status") == "approval_rejected":
            st.error("Agent 1 requirements were rejected at the approval checkpoint. Re-analyse the source after updates.")
        else:
            st.warning("Agent 1 output is validated and waiting for human approval before Agent 2 can run.")
        st.subheader(analysis["project_name"])
        st.write(analysis["project_overview"])
        _metric_row([
            ("Stability", analysis["requirement_stability"]),
            ("Complexity", analysis["project_complexity"]),
            ("Change frequency", analysis["change_frequency"]),
            ("Security risk", analysis["security_risk"]),
        ])
        for title, field in (
            ("Project objectives", "project_objectives"),
            ("Stakeholders and roles", "stakeholders"),
            ("Technical requirements", "technical_requirements"),
            ("Constraints", "constraints"),
        ):
            _show_list(title, analysis.get(field, []))
        st.subheader("Functional requirements")
        _show_requirements(analysis.get("functional_requirements", []))
        st.subheader("Non-functional requirements")
        _show_requirements(analysis.get("non_functional_requirements", []))
        counts = analysis.get("requirement_category_counts", {})
        if counts:
            chart = px.pie(
                names=list(counts), values=list(counts.values()), hole=0.48,
                title="Requirement category distribution",
                color_discrete_sequence=["#0F766E", "#1C5D79", "#D59B48", "#6F8290", "#49A6A0"],
            )
            chart.update_layout(
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font={"color": "#163746"}, title_font={"color": "#102F40"},
                legend={"font": {"color": "#294A56"}},
            )
            st.plotly_chart(chart, use_container_width=True)
        quality_cols = st.columns(3)
        for column, title, field in (
            (quality_cols[0], "Ambiguities", "ambiguities"),
            (quality_cols[1], "Conflicts", "conflicts"),
            (quality_cols[2], "Missing requirements", "missing_requirements"),
        ):
            with column:
                _show_list(title, analysis.get(field, []))
        _show_list("Duplicate requirements", analysis.get("duplicate_requirements", []))
        _show_list("Recommendations for improvement", analysis.get("improvement_recommendations", []))
        _show_list("Clarification questions", analysis.get("clarification_questions", []))
    else:
        st.info("Upload and analyse a document first.")

elif selected_page == "SDLC Recommendation":
    st.title("SDLC Intelligence · Agent 2")
    result = _require_analysis()
    if result:
        recommendation = result["sdlc_recommendation"]
        st.success(f"Agent 2 complete · Consumed Agent 1 output for {recommendation['source_project']}")
        st.markdown(f"## Recommended: {recommendation['recommended_model']}")
        st.write(recommendation["justification"])
        hybrid = recommendation["hybrid_approach"]
        if hybrid["recommended"]:
            st.info(f"Optional hybrid approach: {' + '.join(hybrid['models'])}. {hybrid['reason']}")
        else:
            st.caption(f"No hybrid combination recommended. {hybrid['reason']}")
        score_rows = recommendation["ranked_comparison"]
        chart = px.bar(
            pd.DataFrame(score_rows), x="score", y="model", orientation="h",
            text="score", range_x=[0, 100], labels={"score": "Suitability score", "model": "SDLC model"},
            color="score", color_continuous_scale=["#b7d9d4", "#0b766e"],
        )
        chart.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
        chart.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            font={"color": "#163746"}, title_font={"color": "#102F40"},
            xaxis={"gridcolor": "#E2EAEC", "zerolinecolor": "#C7D5D8"},
        )
        st.plotly_chart(chart, use_container_width=True)
        st.dataframe(
            pd.DataFrame([{
                "model": item["model"],
                "score": item["score"],
                "suitability": item["suitability"],
                "advantages": "; ".join(item["advantages"]),
                "trade-offs": "; ".join(item["disadvantages"]),
                "explanation": item["explanation"],
            } for item in score_rows]),
            use_container_width=True,
            hide_index=True,
        )
        left, right = st.columns(2)
        left.markdown("#### Advantages")
        _show_list("", recommendation["advantages"])
        right.markdown("#### Trade-offs")
        _show_list("", recommendation["disadvantages"])
        _show_list("Project characteristics", [
            f"{key.replace('_', ' ').title()}: {value}"
            for key, value in recommendation["project_characteristics"].items()
        ])
        _show_list("Implementation considerations", recommendation["implementation_considerations"])
        _show_list("Security and privacy screening", [
            f"Risk: {recommendation['security_privacy_analysis']['risk_level']}",
            *recommendation["security_privacy_analysis"]["review_items"],
            recommendation["security_privacy_analysis"]["scope_note"],
        ])
        compliance = recommendation["hospitality_compliance_assessment"]
        _show_list("Hospitality compliance screening", [
            f"{item['area']}: {item['status']}" for item in compliance["items"]
        ] + [compliance["limitations"]])
        _show_list("Operational and technical risks", [
            f"{item['area']} ({item['level']}): {item['mitigation']}"
            for item in recommendation["operational_technical_risks"]
        ])
        with st.expander("Retrieved hospitality knowledge"):
            for item in recommendation["retrieved_hospitality_knowledge"]:
                st.markdown(f"**{item['topic']}** · `{item['source_id']}`")
                st.write(item["content"])
    else:
        st.info("Run Agent 1 from the Document Upload page first.")

elif selected_page == "SDLC Workflow":
    st.title("Project-Specific SDLC Workflow")
    result = _require_analysis()
    if result:
        recommendation = result["sdlc_recommendation"]
        st.caption(f"Tailored around {recommendation['recommended_model']} for {recommendation['source_project']}.")
        for phase in recommendation["workflow"]:
            with st.expander(phase["phase"], expanded=False):
                for label in ("activities", "responsible_roles", "deliverables", "review_checkpoints"):
                    st.markdown(f"**{label.replace('_', ' ').title()}**")
                    _show_list("", phase[label])
                st.write(f"**Testing:** {phase['testing_strategy']}")
                st.write(f"**Entry:** {phase['entry_criteria']}")
                st.write(f"**Exit:** {phase['exit_criteria']}")
                st.write(f"**Expected outcome:** {phase['expected_outcomes']}")
    else:
        st.info("Run both agents to generate the workflow.")

else:
    st.title("Report Generation")
    result = _require_analysis()
    if result:
        analysis = result["requirement_analysis"]
        recommendation = result["sdlc_recommendation"]
        st.write("Download the full analysis package. PDF includes the recommendation, scores, requirements, quality findings, and workflow.")
        st.download_button("Download PDF report", generate_pdf_report(analysis, recommendation),
                           file_name="hospitalytics_analysis_report.pdf", mime="application/pdf", type="primary")
        st.download_button("Download JSON analysis", analysis_json(result),
                           file_name="hospitalytics_analysis.json", mime="application/json")
        st.download_button("Download requirements CSV", requirements_csv(analysis),
                           file_name="hospitalytics_requirements.csv", mime="text/csv")
        with st.expander("Coordinator audit trail"):
            st.dataframe(pd.DataFrame(result.get("audit_log", [])), use_container_width=True, hide_index=True)
    else:
        st.info("Run both agents to generate downloadable reports.")
