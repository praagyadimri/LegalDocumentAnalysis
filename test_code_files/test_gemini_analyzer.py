import json
from pathlib import Path

from backend.document_analysis.gemini_analyzer import (
    analyze_pdf_with_gemini
)


PDF_PATH = Path(r"test_docs\judgement.pdf")


def main():
    print("=" * 70)
    print("GEMINI DOCUMENT ANALYSIS TEST")
    print("=" * 70)

    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"Test PDF not found: {PDF_PATH}"
        )

    print(f"PDF: {PDF_PATH}")

    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    print(
        f"PDF size: "
        f"{len(pdf_bytes) / (1024 * 1024):.2f} MB"
    )

    print()
    print("Sending PDF to Gemini...")
    print()

    result = analyze_pdf_with_gemini(
        PDF_PATH
    )

    output_path = Path(
        "gemini_analyzer_result.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print("ANALYSIS COMPLETED")
    print("=" * 70)

    print(
        f"Document type: "
        f"{result.get('document_type', '')}"
    )

    print(
        f"Document subject: "
        f"{result.get('document_subject', '')}"
    )

    bns_relevance = result.get(
        "bns_relevance",
        {}
    )

    print(
        f"BNS relevance: "
        f"{bns_relevance.get('classification', '')}"
    )

    print(
        f"BNS reason: "
        f"{bns_relevance.get('reason', '')}"
    )

    bns_facts = result.get(
        "bns_relevant_facts",
        []
    )

    print(
        f"BNS-relevant facts: "
        f"{len(bns_facts)}"
    )

    present_case = result.get(
        "present_case",
        {}
    )

    print(
        f"Present-case facts: "
        f"{len(present_case.get('facts', []))}"
    )

    print(
        f"Procedural events: "
        f"{len(present_case.get('procedural_history', []))}"
    )

    print(
        f"Party allegations: "
        f"{len(present_case.get('party_allegations', []))}"
    )

    print(
        f"Party arguments: "
        f"{len(present_case.get('party_arguments', []))}"
    )

    print(
        f"Court findings: "
        f"{len(present_case.get('court_findings', []))}"
    )

    print(
        f"Court orders: "
        f"{len(present_case.get('court_orders', []))}"
    )

    document_content = result.get(
        "document_content",
        {}
    )

    print(
        f"Referenced cases: "
        f"{len(document_content.get('referenced_cases', []))}"
    )

    print(
        f"External examples: "
        f"{len(document_content.get('external_examples', []))}"
    )

    print(
        f"General observations: "
        f"{len(document_content.get('general_observations', []))}"
    )

    print(
        f"Publications: "
        f"{len(document_content.get('publications', []))}"
    )

    print(
        f"Background information: "
        f"{len(document_content.get('background_information', []))}"
    )

    metadata = result.get(
        "_metadata",
        {}
    )

    if metadata:
        print()
        print(
            f"Upload time: "
            f"{metadata.get('upload_time_seconds', 0):.2f} seconds"
        )

        print(
            f"Analysis time: "
            f"{metadata.get('analysis_time_seconds', 0):.2f} seconds"
        )

        print(
            f"Total time: "
            f"{metadata.get('total_time_seconds', 0):.2f} seconds"
        )

    print()
    print(
        f"Full result saved to: "
        f"{output_path}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()