# document_service.py
import json
import tempfile
from pathlib import Path

from backend.document_analysis.gemini_analyzer import (
    analyze_pdf_with_gemini
)

from backend.document_analysis.bns_adapter import (
    adapt_gemini_to_bns
)


def analyze_uploaded_pdf(file_content, filename):
    """
    Analyze an uploaded PDF using Gemini and convert
    the result into the existing BNS fact schema.

    Returns
    -------
    tuple
        (gemini_result, bns_result)
    """

    if not file_content:
        raise ValueError("Uploaded PDF is empty.")

    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False
        ) as temp_file:

            temp_file.write(file_content)
            temp_path = Path(temp_file.name)

        gemini_result = analyze_pdf_with_gemini(
            temp_path
        )

        bns_result = adapt_gemini_to_bns(
            gemini_result
        )

        return gemini_result, bns_result

    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


def format_document_analysis(gemini_result):
    """
    Convert Gemini's structured document analysis
    into a readable answer.

    This is used when the document itself is being
    analyzed rather than sent through the BNS pipeline.
    """

    document_type = gemini_result.get(
        "document_type",
        "Unknown"
    )

    document_subject = gemini_result.get(
        "document_subject",
        ""
    )

    bns_relevance = gemini_result.get(
        "bns_relevance",
        {}
    )

    classification = bns_relevance.get(
        "classification",
        "NONE"
    )

    reason = bns_relevance.get(
        "reason",
        ""
    )

    present_case = gemini_result.get(
        "present_case",
        {}
    )

    lines = []

    lines.append(
        f"Document Type: {document_type}"
    )

    if document_subject:
        lines.append(
            f"Subject: {document_subject}"
        )

    case_name = present_case.get(
        "case_name",
        ""
    )

    court = present_case.get(
        "court",
        ""
    )

    case_number = present_case.get(
        "case_number",
        ""
    )

    if case_name:
        lines.append(
            f"Case: {case_name}"
        )

    if court:
        lines.append(
            f"Court: {court}"
        )

    if case_number:
        lines.append(
            f"Case Number: {case_number}"
        )

    lines.append("")
    lines.append("Present Case Facts:")

    facts = present_case.get(
        "facts",
        []
    )

    if facts:
        for item in facts:
            fact = item.get("fact", "")

            if fact:
                lines.append(
                    f"- {fact}"
                )
    else:
        lines.append(
            "- No substantive present-case facts were identified."
        )

    procedural_history = present_case.get(
        "procedural_history",
        []
    )

    if procedural_history:
        lines.append("")
        lines.append("Procedural History:")

        for item in procedural_history:
            fact = item.get("fact", "")

            if fact:
                lines.append(
                    f"- {fact}"
                )

    allegations = present_case.get(
        "party_allegations",
        []
    )

    if allegations:
        lines.append("")
        lines.append("Party Allegations:")

        for item in allegations:
            fact = item.get("fact", "")

            if fact:
                lines.append(
                    f"- {fact}"
                )

    arguments = present_case.get(
        "party_arguments",
        []
    )

    if arguments:
        lines.append("")
        lines.append("Party Arguments:")

        for item in arguments:
            fact = item.get("fact", "")

            if fact:
                lines.append(
                    f"- {fact}"
                )

    findings = present_case.get(
        "court_findings",
        []
    )

    if findings:
        lines.append("")
        lines.append("Court Findings:")

        for item in findings:
            fact = item.get("fact", "")

            if fact:
                lines.append(
                    f"- {fact}"
                )

    orders = present_case.get(
        "court_orders",
        []
    )

    if orders:
        lines.append("")
        lines.append("Court Orders:")

        for item in orders:
            fact = item.get("fact", "")

            if fact:
                lines.append(
                    f"- {fact}"
                )

    lines.append("")
    lines.append(
        f"BNS Relevance: {classification}"
    )

    if reason:
        lines.append(
            f"Reason: {reason}"
        )

    return "\n".join(lines)


def save_analysis_result(result, output_path):
    """
    Optional helper for debugging/testing.
    """

    output_path = Path(output_path)

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False
        )