
# HospitaLytics

**AI-Based Requirement Analysis and Intelligent SDLC Recommendation System for Hospitality Management**

> Transforming Hospitality Software Requirements into Intelligent SDLC Decisions.

HospitaLytics is an academic decision-support application for hospitality software projects. It accepts a hospitality software requirements document, extracts traceable requirements, evaluates requirement quality, and compares seven SDLC models using a deterministic weighted scoring engine. Agent 2 consumes Agent 1's structured analysis; it does not analyze a separate document.

## Problem statement

Hospitality software projects combine guest-facing experiences with operational workflows, integrations, payment and personal data, and differing levels of requirement stability. Selecting an SDLC approach without systematically considering those factors can lead to unsuitable governance, testing, and delivery practices.

## Proposed solution and objectives

- Process PDF, DOCX, and TXT requirement documents and preview extracted text.
- Identify functional, non-functional, and technical requirements with evidence, page references where available, priority, and confidence.
- Flag ambiguities, duplicates, possible conflicts, and missing quality criteria; suggest clarification questions.
- Pass the structured Agent 1 output to Agent 2.
- Compare exactly seven models—Waterfall, V-Shaped (V-Model), Prototype, RAD (Rapid Application Development), Spiral, Iterative, and Agile—with transparent weighted criteria. DevOps and Hybrid are not individual comparison models.
- Optionally suggest a two-model Hybrid approach only when top standalone scores are close and the models have complementary strengths on important project characteristics.
- Generate a tailored workflow and downloadable PDF, JSON, and CSV.

The hospitality scope includes hotel reservation, restaurant, resort, guest, room booking, billing, event, housekeeping, and staff management systems. The application analyzes the uploaded content rather than selecting a model based on a fixed project type.

## Two-agent architecture

The application has exactly two primary agents. Risk, compliance, and retrieval responsibilities are tools owned by Agent 2, not additional agents.

1. **Agent 1: Requirement Engineering Agent** — processes the source document, extracts and classifies requirements, preserves evidence and IDs, detects ambiguity, duplicates and conflicts, proposes clarification questions, captures stakeholder input as unvalidated feedback, and validates its structured output.
2. **Central coordinator (`AnalysisOrchestrator`)** — maintains shared analysis context and trace IDs, logs execution events, pauses for a human to approve Agent 1's validated output, then routes that output to Agent 2 in a typed message envelope. Agent 2 does not receive or re-process the source document.
3. **Agent 2: SDLC Intelligence Agent** — consumes only the coordinator-routed Agent 1 output. Its internal tools perform security/privacy screening, hospitality compliance screening, operational/technical risk assessment, and local hospitality guidance retrieval. It then evaluates all seven models with the weighted scoring engine and creates a tailored workflow.
4. **Supporting utilities** — document extraction, deterministic scoring, report generation, and the Streamlit interface; these are not agents.

The Streamlit workflow is upload → Agent 1 analysis → human review/approval → Agent 2 recommendation. The coordinator retains the trace, handoff metadata, and session audit events with the results. The legacy `analyze()` convenience method remains available for programmatic use and records its approval as automatic; the interactive UI uses the explicit human checkpoint.

Agent 2's knowledge retrieval uses a small curated local hospitality guidance collection in `agents/sdlc_tools.py`. It is transparent and works offline; retrieved notes are general engineering guidance, not legal advice or proof of regulatory compliance.

### Scoring methodology

For each project criterion, the engine compares a normalized project characteristic with an explicit SDLC model profile. The weighted fit is:

`score(model) = 100 × Σ(weightᵢ × (1 − |project_targetᵢ − model_profileᵢ|))`

The criteria weights sum to 1:

| Criterion | Weight |
|---|---:|
| Requirement stability | 0.14 |
| Change frequency | 0.16 |
| Project complexity | 0.15 |
| Project risk | 0.16 |
| Security and reliability | 0.12 |
| Testing and verification | 0.10 |
| Stakeholder involvement | 0.09 |
| Continuous delivery | 0.08 |

Model profiles and weights are documented in `core/scoring_engine.py`. Heuristic project values are derived from Agent 1's findings and surfaced in the results. The percentages are comparative decision-support estimates, not empirical probabilities.

## Technology

- Python and Streamlit
- PyMuPDF and python-docx
- Pandas and Plotly
- ReportLab
- pytest
- Optional OpenAI-compatible chat-completions API; no API key is required for local fallback mode

## Project structure

```text
XC Project/
├── app.py
├── agents/
│   ├── requirement_agent.py
│   ├── sdlc_tools.py
│   └── sdlc_agent.py
├── config/
├── core/
│   ├── document_processor.py
│   ├── llm_client.py
│   ├── orchestrator.py
│   ├── requirement_classifier.py
│   └── scoring_engine.py
├── sample_documents/
├── tests/
├── utils/
├── .env.example
└── requirements.txt
```

## Windows installation and execution

Use Python 3.10 or newer. From PowerShell in the project directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local Streamlit URL displayed in the terminal (typically `http://localhost:8501`). Navigate to **Document Upload**, upload a file, inspect its extracted text and Agent 1 requirements, then approve them to run Agent 2. Completed results remain available when navigating between application pages during that session.

## Optional LLM mode

Without `OPENAI_API_KEY`, Agent 1 uses the built-in rule-based classifier and Agent 2 remains deterministic. To enable optional classification, set these environment variables before starting the application:

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "gpt-4o-mini"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
streamlit run app.py
```

The LLM is asked to classify only source sentences supplied by Agent 1; returned requirement evidence is mapped back to those exact sentences. Agent 1 reports its operating mode. Do not commit credentials; `.env.example` contains placeholders only.

## Samples and tests

Three sample TXT requirement documents are included for hotel reservation, restaurant, and resort management. They deliberately differ in scope, stability, and risk. Recommendations are generated by the same scoring engine used for user uploads; samples do not hardcode expected winners.

Run tests:

```powershell
python -m pytest -q
```

The test suite covers PDF, DOCX, and TXT extraction; invalid documents; requirement classification and quality checks; both agents; ranking; orchestration; JSON serialization; and PDF generation.

## Example output

An analysis includes the source document, extracted requirement categories, source evidence/page references, quality findings and clarifications, Agent 1 characteristics, all seven ranked model scores, recommendation rationale, workflow phases, and exportable report data. The recommended model depends on the uploaded requirements.

## Limitations

- Extraction quality depends on readable text; scanned PDFs require OCR, which is not currently included.
- DOCX has no dependable page layout metadata in this extraction approach, so page references are not guaranteed for DOCX.
- Rule-based inference is intentionally transparent but less nuanced than domain-expert review; ambiguous inputs need human clarification.
- Characteristic levels and profile weights are heuristic academic decision-support assumptions and should be calibrated for a real organization.
- The optional API mode sends the supplied text/candidate requirement sentences to the configured endpoint; review data-handling requirements before enabling it.

## Future enhancements

- Add OCR and document-layout-aware extraction.
- Add configurable organizational SDLC profiles with weight sensitivity analysis.
- Add requirement traceability matrices, acceptance-criteria generation, and stakeholder review.
- Add authentication, persistent project workspaces, durable audit storage, and deployment monitoring.
- Validate the scoring framework with hospitality engineering teams and project outcomes.
=======
