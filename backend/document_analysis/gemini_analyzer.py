# gemini_analyzer.py
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set in the .env file."
    )


MODEL_NAME = "gemini-3.8-flash"

client = genai.Client(
    api_key=GEMINI_API_KEY
)


DOCUMENT_ANALYSIS_PROMPT = """
You are a high-precision legal document analysis system.

Analyze the supplied legal PDF and return ONLY valid JSON.

Your primary objective is factual accuracy.

Do NOT decide BNS sections.
Do NOT invent facts.
Do NOT infer facts that are not supported by the document.
Do NOT treat referenced cases, hypothetical examples, legal commentary,
or party arguments as facts of the present case.

==================================================
1. DOCUMENT IDENTIFICATION
==================================================

Identify:

- document_type
- document_subject

Possible document types include:

Judgment
Court Order
Petition
Appeal
Complaint
Charge Sheet
Legal Notice
Agreement
Contract
Affidavit
Application
Tribunal Order
Arbitration Award
Corporate Document
Other

==================================================
2. PRESENT CASE VS OTHER MATERIAL
==================================================

This distinction is extremely important.

The document may contain:

- facts of the present case
- procedural history
- party allegations
- party arguments
- court findings
- court orders
- cited judgments
- referenced cases
- hypothetical examples
- external examples
- legal commentary
- publications
- general observations
- background information

Never mix these categories.

A fact from a cited case is NOT a fact of the present case.

A hypothetical example is NOT a fact of the present case.

A party allegation is NOT automatically an established fact.

A legal proposition is NOT a factual event.

==================================================
3. PRESENT CASE
==================================================

Extract:

- case_name
- court
- case_number
- parties
- facts
- procedural_history
- party_allegations
- party_arguments
- court_findings
- court_orders

Only put facts that belong to the actual matter being decided into
present_case.facts.

==================================================
4. FACT EVIDENCE
==================================================

Every extracted factual item must contain:

- fact
- role
- page
- evidence
- confidence

"page" must identify the page where the information appears.

"evidence" must be a short faithful quotation or close textual support
from the document.

Never fabricate evidence.

Confidence must be between 0.0 and 1.0.

==================================================
5. FACT ROLES
==================================================

Use one of these roles:

CASE_FACT
PROCEDURAL_EVENT
PARTY_ALLEGATION
PARTY_ARGUMENT
COURT_FINDING
COURT_ORDER
LEGAL_PROPOSITION
REFERENCED_CASE
EXTERNAL_EXAMPLE
GENERAL_OBSERVATION
PUBLICATION
BACKGROUND
OTHER

==================================================
6. BNS RELEVANCE
==================================================

Determine whether the PRESENT CASE contains facts relevant to offences
under the Bharatiya Nyaya Sanhita.

Use exactly one:

HIGH
MEDIUM
LOW
NONE

HIGH:
The present case contains concrete facts that could materially support
BNS criminal analysis.

MEDIUM:
The present case contains potentially relevant criminal facts, but they
are incomplete, disputed, indirect, or insufficient.

LOW:
There is only a weak or incidental connection to criminal law.

NONE:
The present case contains no meaningful BNS-relevant facts.

IMPORTANT:

Do NOT classify a document as BNS-relevant merely because it mentions:

- BNS
- IPC
- criminal law
- criminal cases
- offences in cited judgments
- hypothetical criminal examples
- criminal law publications
- criminal law commentary

The classification must primarily concern the PRESENT CASE.

==================================================
7. BNS-RELEVANT FACTS
==================================================

Return bns_relevant_facts ONLY when the present case contains concrete
facts that could genuinely be useful for later BNS analysis.

Do NOT include:

- referenced cases
- hypothetical examples
- legal propositions
- publications
- general observations
- unrelated procedural events
- unsupported assumptions
- facts belonging to another case

Each BNS-relevant fact must contain:

- fact
- category
- role
- page
- evidence
- confidence

If there are no genuine BNS-relevant facts:

"bns_relevant_facts": []

==================================================
8. PARTIES
==================================================

Only identify actual parties to the present case.

Do not list every person mentioned in the judgment as a party.

==================================================
9. PROCEDURAL HISTORY
==================================================

Extract important procedural events.

Examples:

- filing
- admission
- appointment
- appeal
- dismissal
- remand
- restoration
- final order

Keep these separate from substantive facts.

==================================================
10. COURT FINDINGS
==================================================

Only record conclusions actually reached by the deciding court.

Do not convert arguments into findings.

==================================================
11. COURT ORDERS
==================================================

Record operative directions made by the court.

==================================================
12. OTHER CONTENT
==================================================

Separate non-present-case material into:

- legal_propositions
- referenced_cases
- external_examples
- general_observations
- publications
- background_information

==================================================
13. OUTPUT FORMAT
==================================================

Return exactly this structure:

{
  "document_type": "",
  "document_subject": "",

  "bns_relevance": {
    "classification": "HIGH | MEDIUM | LOW | NONE",
    "reason": ""
  },

  "present_case": {
    "case_name": "",
    "court": "",
    "case_number": "",

    "parties": [
      {
        "name": "",
        "role": "",
        "description": ""
      }
    ],

    "facts": [
      {
        "fact": "",
        "role": "CASE_FACT",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "procedural_history": [
      {
        "fact": "",
        "role": "PROCEDURAL_EVENT",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "party_allegations": [
      {
        "fact": "",
        "role": "PARTY_ALLEGATION",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "party_arguments": [
      {
        "fact": "",
        "role": "PARTY_ARGUMENT",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "court_findings": [
      {
        "fact": "",
        "role": "COURT_FINDING",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "court_orders": [
      {
        "fact": "",
        "role": "COURT_ORDER",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ]
  },

  "document_content": {
    "legal_propositions": [
      {
        "fact": "",
        "role": "LEGAL_PROPOSITION",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "referenced_cases": [
      {
        "fact": "",
        "role": "REFERENCED_CASE",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "external_examples": [
      {
        "fact": "",
        "role": "EXTERNAL_EXAMPLE",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "general_observations": [
      {
        "fact": "",
        "role": "GENERAL_OBSERVATION",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "publications": [
      {
        "fact": "",
        "role": "PUBLICATION",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ],

    "background_information": [
      {
        "fact": "",
        "role": "BACKGROUND",
        "page": 0,
        "evidence": "",
        "confidence": 0.0
      }
    ]
  },

  "bns_relevant_facts": [
    {
      "fact": "",
      "category": "",
      "role": "CASE_FACT",
      "page": 0,
      "evidence": "",
      "confidence": 0.0
    }
  ]
}
"""


def extract_json(response):
    text = getattr(response, "text", None)

    if not text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    text = text.strip()

    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

        try:
            result = json.loads(cleaned)

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        try:
            result = json.loads(
                text[start:end + 1]
            )

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Gemini response could not be parsed as JSON."
    )


def validate_result(result):
    if not isinstance(result, dict):
        raise ValueError(
            "Gemini result is not a JSON object."
        )

    required_keys = [
        "document_type",
        "document_subject",
        "bns_relevance",
        "present_case",
        "document_content",
        "bns_relevant_facts"
    ]

    for key in required_keys:
        if key not in result:
            raise ValueError(
                f"Gemini result is missing required field: {key}"
            )

    bns_relevance = result.get(
        "bns_relevance"
    )

    if not isinstance(bns_relevance, dict):
        raise ValueError(
            "bns_relevance must be an object."
        )

    classification = str(
        bns_relevance.get(
            "classification",
            ""
        )
    ).upper().strip()

    allowed = {
        "HIGH",
        "MEDIUM",
        "LOW",
        "NONE"
    }

    if classification not in allowed:
        raise ValueError(
            f"Invalid BNS relevance classification: "
            f"{classification}"
        )

    bns_relevance["classification"] = classification

    if not isinstance(
        result.get("bns_relevant_facts"),
        list
    ):
        raise ValueError(
            "bns_relevant_facts must be a list."
        )

    return result


def analyze_pdf_with_gemini(pdf_path):
    """
    Analyze a PDF using Gemini.

    Parameters
    ----------
    pdf_path : str or pathlib.Path
        Path to the PDF file.

    Returns
    -------
    dict
        Structured legal document analysis.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    if not pdf_path.is_file():
        raise ValueError(
            f"Path is not a file: {pdf_path}"
        )

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF file: {pdf_path}"
        )

    print("=" * 70)
    print("GEMINI DOCUMENT ANALYSIS")
    print("=" * 70)

    print(f"PDF: {pdf_path}")
    print(
        f"Size: "
        f"{pdf_path.stat().st_size / (1024 * 1024):.2f} MB"
    )

    total_start = time.time()

    print()
    print("Uploading PDF to Gemini...")

    upload_start = time.time()

    uploaded_file = client.files.upload(
        file=str(pdf_path),
        config={
            "mime_type": "application/pdf"
        }
    )

    upload_time = time.time() - upload_start

    print(
        f"Upload completed in "
        f"{upload_time:.2f} seconds."
    )

    print()
    print("Analyzing document...")

    analysis_start = time.time()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            uploaded_file,
            DOCUMENT_ANALYSIS_PROMPT
        ],
        config={
            "temperature": 0.0,
            "response_mime_type": "application/json"
        }
    )

    analysis_time = time.time() - analysis_start

    print(
        f"Gemini analysis completed in "
        f"{analysis_time:.2f} seconds."
    )

    result = extract_json(response)

    result = validate_result(result)

    total_time = time.time() - total_start

    result["_metadata"] = {
        "model": MODEL_NAME,
        "filename": pdf_path.name,
        "upload_time_seconds": round(
            upload_time,
            2
        ),
        "analysis_time_seconds": round(
            analysis_time,
            2
        ),
        "total_time_seconds": round(
            total_time,
            2
        )
    }

    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

    print(
        f"Document type: "
        f"{result['document_type']}"
    )

    print(
        f"BNS relevance: "
        f"{result['bns_relevance']['classification']}"
    )

    print(
        f"BNS-relevant facts: "
        f"{len(result['bns_relevant_facts'])}"
    )

    print(
        f"Total time: "
        f"{total_time:.2f} seconds"
    )

    print("=" * 70)

    return result


if __name__ == "__main__":

    test_pdf = Path(
        r"test_docs\judgement.pdf"
    )

    result = analyze_pdf_with_gemini(
        test_pdf
    )

    output_path = Path(
        "gemini_document_analysis.json"
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
    print(
        f"Full result saved to: "
        f"{output_path}"
    )