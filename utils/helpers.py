"""Serialization helpers for downloadable analysis results."""

import csv
import io
import json


def analysis_json(analysis: dict) -> bytes:
    return json.dumps(analysis, ensure_ascii=False, indent=2).encode("utf-8")


def requirements_csv(analysis: dict) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=[
        "requirement_id", "type", "description", "category", "priority",
        "source_evidence", "page_reference", "confidence_score", "origin",
    ])
    writer.writeheader()
    counter = 1
    for kind, key in (
        ("Functional", "functional_requirements"),
        ("Non-functional", "non_functional_requirements"),
        ("Technical", "technical_requirements"),
    ):
        for requirement in analysis.get(key, []):
            writer.writerow({
                "requirement_id": f"REQ-{counter:03d}",
                "type": kind,
                **{field: requirement.get(field, "") for field in writer.fieldnames if field not in {"requirement_id", "type"}},
            })
            counter += 1
    return stream.getvalue().encode("utf-8-sig")
