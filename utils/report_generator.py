"""Paginated, wrapped PDF report generation for the full analysis."""

from io import BytesIO


PAGE_WIDTH_MM = 210
LEFT_MARGIN_MM = 18
RIGHT_MARGIN_MM = 18
TABLE_WIDTH_MM = PAGE_WIDTH_MM - LEFT_MARGIN_MM - RIGHT_MARGIN_MM


def generate_pdf_report(analysis: dict, recommendation: dict) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            LongTable,
            Paragraph,
            SimpleDocTemplate,
            TableStyle,
        )
    except ImportError as error:
        raise RuntimeError("PDF export requires ReportLab. Install the project requirements.") from error

    palette = {
        "navy": colors.HexColor("#153A4A"),
        "teal": colors.HexColor("#0F766E"),
        "pale": colors.HexColor("#EAF3F2"),
        "line": colors.HexColor("#D1DFE2"),
        "ink": colors.HexColor("#243F4B"),
        "muted": colors.HexColor("#536D78"),
        "white": colors.white,
        "stripe": colors.HexColor("#F6F9F9"),
    }
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=RIGHT_MARGIN_MM * mm,
        leftMargin=LEFT_MARGIN_MM * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title="HospitaLytics Analysis",
        author="HospitaLytics",
    )
    base = getSampleStyleSheet()
    styles = {
        "brand": ParagraphStyle(
            "ReportBrand", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=23, leading=27, textColor=palette["teal"], alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], fontSize=10, leading=13,
            textColor=palette["muted"], spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "ReportH1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=14, leading=18, textColor=palette["navy"],
            spaceBefore=13, spaceAfter=6, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "ReportH2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=13, textColor=palette["teal"],
            spaceBefore=9, spaceAfter=4, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReportBody", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9, leading=13, textColor=palette["ink"],
            spaceAfter=5, splitLongWords=True,
        ),
        "small": ParagraphStyle(
            "ReportSmall", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.6, leading=10, textColor=palette["ink"], splitLongWords=True,
        ),
        "table_header": ParagraphStyle(
            "ReportTableHeader", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.6, leading=9.4, textColor=palette["white"],
        ),
        "table_cell": ParagraphStyle(
            "ReportTableCell", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.5, leading=9.6, textColor=palette["ink"], splitLongWords=True,
        ),
        "table_small": ParagraphStyle(
            "ReportTableSmall", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.1, leading=8.8, textColor=palette["ink"], splitLongWords=True,
        ),
    }

    story = [
        Paragraph("HospitaLytics", styles["brand"]),
        Paragraph("AI-Based Requirement Analysis and Intelligent SDLC Recommendation", styles["subtitle"]),
        Paragraph(f"<b>Project:</b> {_escape(analysis.get('project_name', 'Hospitality project'))}", styles["body"]),
        Paragraph("Executive summary", styles["h1"]),
        Paragraph(_escape(analysis.get("project_overview", "No overview identified.")), styles["body"]),
        Paragraph("Recommended SDLC model", styles["h1"]),
        Paragraph(
            f"<b>{_escape(recommendation.get('recommended_model', 'Not available'))}</b> - "
            f"{_escape(recommendation.get('justification', ''))}",
            styles["body"],
        ),
        Paragraph(
            (
                "<b>Optional hybrid:</b> "
                + _escape(" + ".join(recommendation["hybrid_approach"].get("models", [])))
                + " - "
                + _escape(recommendation["hybrid_approach"].get("reason", ""))
                if recommendation.get("hybrid_approach", {}).get("recommended")
                else "<b>Optional hybrid:</b> Not recommended. "
                + _escape(recommendation.get("hybrid_approach", {}).get("reason", ""))
            ),
            styles["body"],
        ),
        _scores_table(
            recommendation.get("ranked_comparison", []),
            palette, LongTable, TableStyle, Paragraph, styles, mm,
        ),
        Paragraph("Project objectives", styles["h1"]),
        *_bullets(analysis.get("project_objectives", []), styles["body"], Paragraph),
        Paragraph("Functional requirements", styles["h1"]),
        _requirement_table(analysis.get("functional_requirements", []), palette, LongTable, TableStyle, Paragraph, styles, mm),
        Paragraph("Non-functional requirements", styles["h1"]),
        _requirement_table(analysis.get("non_functional_requirements", []), palette, LongTable, TableStyle, Paragraph, styles, mm),
        Paragraph("Technical requirements", styles["h1"]),
        _requirement_table(analysis.get("technical_requirements", []), palette, LongTable, TableStyle, Paragraph, styles, mm),
        Paragraph("Constraints", styles["h1"]),
        _requirement_table(analysis.get("constraints", []), palette, LongTable, TableStyle, Paragraph, styles, mm),
        Paragraph("Requirement quality analysis", styles["h1"]),
    ]
    _append_quality_section(story, analysis, styles, Paragraph)
    story.extend([
        Paragraph("Project characteristics", styles["h1"]),
        *_bullets(
            [f"{key.replace('_', ' ').title()}: {value}" for key, value in recommendation.get("project_characteristics", {}).items()],
            styles["body"], Paragraph,
        ),
        Paragraph("Security and privacy screening", styles["h1"]),
        *_bullets(
            [
                f"Risk level: {recommendation.get('security_privacy_analysis', {}).get('risk_level', 'Not assessed')}",
                *recommendation.get("security_privacy_analysis", {}).get("review_items", []),
                recommendation.get("security_privacy_analysis", {}).get("scope_note", ""),
            ],
            styles["body"], Paragraph,
        ),
        Paragraph("Hospitality compliance screening", styles["h1"]),
        *_bullets(
            [
                f"{item.get('area', 'Area')}: {item.get('status', 'Not assessed')}"
                for item in recommendation.get("hospitality_compliance_assessment", {}).get("items", [])
            ] + [
                recommendation.get("hospitality_compliance_assessment", {}).get("limitations", "")
            ],
            styles["body"], Paragraph,
        ),
        Paragraph("Operational and technical risks", styles["h1"]),
        *_bullets(
            [
                f"{item.get('area')} ({item.get('level')}): {item.get('mitigation')}"
                for item in recommendation.get("operational_technical_risks", [])
            ],
            styles["body"], Paragraph,
        ),
        Paragraph("Retrieved hospitality guidance", styles["h1"]),
        *_bullets(
            [
                f"{item.get('topic')} [{item.get('source_id')}]: {item.get('content')}"
                for item in recommendation.get("retrieved_hospitality_knowledge", [])
            ],
            styles["body"], Paragraph,
        ),
        Paragraph("SDLC alternatives and rationale", styles["h1"]),
        _scores_table(
            recommendation.get("ranked_comparison", []),
            palette, LongTable, TableStyle, Paragraph, styles, mm,
            include_rationale=True,
        ),
        Paragraph("Customised SDLC workflow", styles["h1"]),
    ])
    for phase in recommendation.get("workflow", []):
        story.append(Paragraph(_escape(phase.get("phase", "Workflow phase")), styles["h2"]))
        for label, field in (
            ("Activities", "activities"),
            ("Responsible roles", "responsible_roles"),
            ("Deliverables", "deliverables"),
            ("Testing strategy", "testing_strategy"),
            ("Review checkpoints", "review_checkpoints"),
            ("Entry criteria", "entry_criteria"),
            ("Exit criteria", "exit_criteria"),
            ("Expected outcomes", "expected_outcomes"),
        ):
            value = phase.get(field, [])
            content = "; ".join(str(item) for item in value) if isinstance(value, list) else str(value)
            story.append(Paragraph(f"<b>{label}:</b> {_escape(content)}", styles["body"]))
    story.extend([
        Paragraph("Conclusion", styles["h1"]),
        Paragraph(
            f"The deterministic weighted comparison selected "
            f"{_escape(recommendation.get('recommended_model', 'an SDLC model'))}. "
            "Suitability scores are comparative decision-support estimates and should be validated "
            "with project stakeholders.",
            styles["body"],
        ),
    ])
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_page_chrome(canvas, doc, palette, mm),
        onLaterPages=lambda canvas, doc: _draw_page_chrome(canvas, doc, palette, mm),
    )
    return buffer.getvalue()


def _append_quality_section(story, analysis, styles, Paragraph) -> None:
    _append_labeled_items(story, "Ambiguities", analysis.get("ambiguities", []), "Finding", styles, Paragraph)
    _append_labeled_items(story, "Conflicts", analysis.get("conflicts", []), "Finding", styles, Paragraph)
    _append_labeled_items(story, "Missing requirements / gaps", analysis.get("missing_requirements", []), "Gap", styles, Paragraph)
    _append_labeled_items(
        story, "Recommendations for improvement",
        analysis.get("improvement_recommendations", []), "Recommendation", styles, Paragraph,
    )
    duplicates = [
        f"{item.get('description', '')} (observed {item.get('occurrences', 0)} times)"
        for item in analysis.get("duplicate_requirements", [])
    ]
    _append_labeled_items(story, "Possible duplicates", duplicates, "Review", styles, Paragraph)
    _append_labeled_items(
        story, "Clarification questions", analysis.get("clarification_questions", []),
        "Question", styles, Paragraph,
    )


def _append_labeled_items(story, title, items, label, styles, Paragraph) -> None:
    story.append(Paragraph(title, styles["h2"]))
    if not items:
        story.append(Paragraph("None identified.", styles["body"]))
        return
    for item in items:
        if isinstance(item, dict):
            description = item.get("description", "")
            reason = item.get("reason")
            evidence = item.get("source_evidence")
            details = [f"<b>{label}:</b> {_escape(description)}"]
            if reason:
                details.append(f"<b>Why flagged:</b> {_escape(reason)}")
            if evidence:
                details.append(f"<b>Source evidence:</b> {_escape(evidence)}")
            story.append(Paragraph("<br/>".join(details), styles["body"]))
        else:
            story.append(Paragraph(f"&bull; {_escape(str(item))}", styles["body"]))


def _scores_table(rows, palette, LongTable, TableStyle, Paragraph, styles, mm, include_rationale=False):
    headers = ["Rank", "SDLC model", "Suitability"]
    widths = [13, 63, 24]
    if include_rationale:
        headers.append("Fit and comparison rationale")
        widths.append(TABLE_WIDTH_MM - sum(widths))
    data = [[Paragraph(_escape(header), styles["table_header"]) for header in headers]]
    for index, item in enumerate(rows, 1):
        row = [
            Paragraph(str(index), styles["table_cell"]),
            Paragraph(_escape(item.get("model", "")), styles["table_cell"]),
            Paragraph(f"{item.get('score', 0):.1f}%", styles["table_cell"]),
        ]
        if include_rationale:
            fit_details = (
                f"<b>{_escape(item.get('suitability', ''))}</b><br/>"
                f"{_escape(item.get('explanation', ''))}<br/>"
                f"<b>Advantages:</b> {_escape('; '.join(item.get('advantages', [])))}<br/>"
                f"<b>Trade-offs:</b> {_escape('; '.join(item.get('disadvantages', [])))}"
            )
            row.append(Paragraph(fit_details, styles["table_small"]))
        data.append(row)
    table = LongTable(
        data,
        colWidths=[width * mm for width in widths],
        repeatRows=1,
        splitByRow=1,
        splitInRow=1,
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), palette["teal"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [palette["white"], palette["stripe"]]),
        ("GRID", (0, 0), (-1, -1), 0.35, palette["line"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _requirement_table(requirements, palette, LongTable, TableStyle, Paragraph, styles, mm):
    if not requirements:
        return Paragraph("None identified.", styles["body"])
    columns = [
        ("ID", 16),
        ("Requirement and source evidence", 99),
        ("Category", 29),
        ("Priority", 18),
        ("Page", 12),
    ]
    data = [[Paragraph(_escape(label), styles["table_header"]) for label, _ in columns]]
    for item in requirements:
        evidence = item.get("source_evidence") or item.get("description", "")
        page = f"p. {item['page_reference']}" if item.get("page_reference") is not None else "-"
        data.append([
            Paragraph(_escape(item.get("requirement_id", "")), styles["table_small"]),
            Paragraph(_escape(evidence), styles["table_cell"]),
            Paragraph(_escape(item.get("category", "")), styles["table_small"]),
            Paragraph(_escape(item.get("priority", "")), styles["table_small"]),
            Paragraph(_escape(page), styles["table_small"]),
        ])
    table = LongTable(
        data,
        colWidths=[width * mm for _, width in columns],
        repeatRows=1,
        splitByRow=1,
        splitInRow=1,
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), palette["navy"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [palette["white"], palette["stripe"]]),
        ("GRID", (0, 0), (-1, -1), 0.35, palette["line"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _bullets(items, style, Paragraph):
    if not items:
        return [Paragraph("None identified.", style)]
    return [Paragraph(f"- {_escape(str(item))}", style) for item in items]


def _draw_page_chrome(canvas, document, palette, mm) -> None:
    canvas.saveState()
    page_width, page_height = document.pagesize
    canvas.setStrokeColor(palette["line"])
    canvas.setLineWidth(0.55)
    canvas.line(LEFT_MARGIN_MM * mm, page_height - 15 * mm, page_width - RIGHT_MARGIN_MM * mm, page_height - 15 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(palette["muted"])
    canvas.drawString(LEFT_MARGIN_MM * mm, page_height - 12 * mm, "HOSPITALYTICS  |  REQUIREMENT & SDLC ANALYSIS")
    canvas.line(LEFT_MARGIN_MM * mm, 14 * mm, page_width - RIGHT_MARGIN_MM * mm, 14 * mm)
    canvas.drawString(LEFT_MARGIN_MM * mm, 9.5 * mm, "Confidential project analysis - validate findings with stakeholders")
    canvas.drawRightString(page_width - RIGHT_MARGIN_MM * mm, 9.5 * mm, f"Page {document.page}")
    canvas.restoreState()


def _escape(value: str) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
