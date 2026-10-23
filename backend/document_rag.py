# document_rag.py
import io
import requests

from pypdf import PdfReader

from backend.rag import search

from backend.fact_extractor import (
    extract_facts,
    facts_to_text
)

from backend.section_verifier import (
    verify_candidates
) 

from backend.output_validator import (
    validate_output
)

from backend.section_rules import (
    apply_section_rules
)


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b"


def ask_qwen(
    prompt,
    num_predict=900
):

    print(
        "Prompt characters:",
        len(prompt)
    )

    print(
        "Approx tokens:",
        len(prompt) // 4
    )

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.0,
                "num_predict": num_predict
            }
        },
        timeout=180
    )

    if response.status_code != 200:

        raise Exception(
            f"Ollama error {response.status_code}: "
            f"{response.text}"
        )

    return response.json()["response"]


# =========================================================
# DOCUMENT SUMMARIZATION
# =========================================================

def summarize_document_chunk(
    chunk,
    chunk_number,
    total_chunks
):

    prompt = f"""
You are analyzing part {chunk_number} of {total_chunks}
of a legal document.

DOCUMENT EXCERPT:

{chunk}

Summarize ONLY information explicitly present in this excerpt.

Focus on:

- case names
- parties
- facts
- legal issues
- arguments
- legal provisions
- court reasoning
- decisions
- important findings

Rules:

- Do not invent information.
- Do not assume the document is a judgment.
- Do not expand acronyms unless the excerpt defines them.
- Do not add information from general knowledge.
- Preserve important names, dates, courts, sections and decisions.
- If the excerpt contains little useful information, say so briefly.

Give a concise summary.
"""

    return ask_qwen(
        prompt,
        num_predict=500
    )


# =========================================================
# BNS RETRIEVAL
# =========================================================

def build_bns_candidates(question):
    """
    Build a larger legal candidate pool.

    Retrieval is only for candidate discovery.

    Retrieval NEVER makes a section legally applicable.
    Every candidate must still pass section_verifier.py.
    """

    query = (
        question or ""
    ).lower()

    candidates = []

    # -----------------------------------------------------
    # BASE SEMANTIC/HYBRID SEARCH
    # -----------------------------------------------------

    try:

        base_candidates = search(
            question,
            15
        )

        if base_candidates:
            candidates.extend(
                base_candidates
            )

    except Exception as e:

        print(
            f"[RAG] Base retrieval failed: {e}"
        )

    # -----------------------------------------------------
    # TARGETED LEGAL QUERIES
    # -----------------------------------------------------

    legal_queries = []

    # -----------------------------------------------------
    # THEFT
    # -----------------------------------------------------

    if any(
        phrase in query
        for phrase in [
            "stole",
            "stolen",
            "steal",
            "theft",
            "took the bag",
            "took property",
            "secretly took",
            "carried away",
            "dishonestly took"
        ]
    ):

        legal_queries.extend([
            "theft movable property dishonest taking possession consent",
            "dishonestly takes movable property out of possession theft",
            "theft property without consent dishonest intention"
        ])

    # -----------------------------------------------------
    # RECEIVING STOLEN PROPERTY
    # -----------------------------------------------------

    if any(
        phrase in query
        for phrase in [
            "received stolen",
            "receiving stolen",
            "retained stolen",
            "kept stolen property",
            "knowing it was stolen"
        ]
    ):

        legal_queries.append(
            "dishonestly receives or retains stolen property "
            "knowing or reason to believe stolen"
        )

    # -----------------------------------------------------
    # DISHONEST MISAPPROPRIATION
    # -----------------------------------------------------

    if any(
        phrase in query
        for phrase in [
            "misappropriated",
            "misappropriation",
            "converted property",
            "dishonestly converted"
        ]
    ):

        legal_queries.append(
            "dishonest misappropriation movable property"
        )

    # -----------------------------------------------------
    # DEFAMATION
    # -----------------------------------------------------

    if any(
        phrase in query
        for phrase in [
            "defamed",
            "defamation",
            "tarnishing image",
            "tarnished image",
            "reputation",
            "reputation damaged",
            "damage reputation",
            "social media",
            "false allegation",
            "published allegations",
            "lowered reputation"
        ]
    ):

        legal_queries.extend([
            "defamation imputation reputation publication",
            "makes or publishes imputation concerning person reputation",
            "defamatory statement publication reputation"
        ])

    # -----------------------------------------------------
    # CASTE / COMMUNITY / GROUP
    # -----------------------------------------------------

    if any(
        phrase in query
        for phrase in [
            "caste",
            "caste-based",
            "community",
            "religion",
            "religious",
            "enmity",
            "disharmony"
        ]
    ):

        legal_queries.extend([
            "promoting enmity between different groups caste religion",
            "caste community group enmity disharmony",
            "promoting feelings of enmity hatred ill-will groups"
        ])

    # -----------------------------------------------------
    # INTENTIONAL INSULT
    # -----------------------------------------------------

    if any(
        phrase in query
        for phrase in [
            "intentional insult",
            "insulted",
            "insult",
            "provoke",
            "provoked",
            "breach of peace"
        ]
    ):

        legal_queries.append(
            "intentional insult with intent to provoke breach "
            "of public peace"
        )

    # -----------------------------------------------------
    # PUBLIC SERVANT / OBSTRUCTION
    # -----------------------------------------------------

    if any(
        phrase in query
        for phrase in [
            "obstructing government duties",
            "obstructed government duties",
            "obstructing government work",
            "obstructed government work",
            "public servant",
            "government officer",
            "government duty",
            "obstructed an officer",
            "prevented government officer"
        ]
    ):

        legal_queries.extend([
            "obstruct public servant discharge public functions",
            "voluntarily obstructs public servant public functions",
            "resisting public servant discharge duty"
        ])

    # -----------------------------------------------------
    # HOUSE TRESPASS / HOUSE BREAKING
    # -----------------------------------------------------

    if any(
        phrase in query
        for phrase in [
            "entered house",
            "entered the house",
            "entered home",
            "house without permission",
            "entered without permission",
            "trespass",
            "house breaking",
            "house-breaking"
        ]
    ):

        legal_queries.extend([
            "criminal trespass house trespass entry house intent offence",
            "house trespass dwelling house criminal trespass",
            "house breaking lurking house trespass specific entry exit method"
        ])

    # -----------------------------------------------------
    # RUN TARGETED SEARCHES
    # -----------------------------------------------------

    for legal_query in legal_queries:

        try:

            extra = search(
                legal_query,
                7
            )

            if extra:
                candidates.extend(
                    extra
                )

        except Exception as e:

            print(
                f"[RAG] Additional legal retrieval failed: {e}"
            )

    # -----------------------------------------------------
    # DEDUPLICATE BY SECTION
    # -----------------------------------------------------

    unique = {}

    for item in candidates:

        if not isinstance(
            item,
            dict
        ):
            continue

        section = item.get(
            "section"
        )

        if section is None:
            continue

        try:

            section = int(
                section
            )

        except (
            ValueError,
            TypeError
        ):

            continue

        # Keep the first occurrence.
        # The verifier decides applicability later.
        if section not in unique:

            unique[
                section
            ] = item

    # -----------------------------------------------------
    # RETURN LARGER CANDIDATE POOL
    # -----------------------------------------------------

    final_candidates = list(
        unique.values()
    )[:30]

    return final_candidates


# =========================================================
# FINAL LEGAL ANSWER
# =========================================================

def generate_final_legal_answer(
    question,
    facts,
    applicable_sections,
    verified_results
):

    facts_text = facts_to_text(
        facts
    )

    applicable = applicable_sections

    possible = [
        result
        for result in verified_results
        if result.get("decision") == "POSSIBLE"
    ]

    # -----------------------------------------------------
    # AUTHORIZED SECTION NUMBERS
    # -----------------------------------------------------

    allowed_section_numbers = [
        int(result["section"])
        for result in applicable
    ]

    allowed_section_text = ", ".join(
        str(section)
        for section in allowed_section_numbers
    )

    if not allowed_section_text:
        allowed_section_text = "NONE"

    # -----------------------------------------------------
    # APPLICABLE TEXT
    # -----------------------------------------------------

    applicable_text = ""

    for result in applicable:

        applicable_text += f"""
BNS SECTION {result['section']}
Title: {result.get('title', '')}
Section type: {result.get('section_type', 'OTHER')}

Section text:
{result.get('section_text', result.get('text', ''))}

Verification reason:
{result.get('reason', '')}

Supported ingredients:
{result.get('supported_ingredients', [])}
"""

        if result.get(
            "punishment_subsection"
        ):

            applicable_text += f"""
Relevant punishment subsection:
{result.get('punishment_subsection')}

"""

        applicable_text += """
--------------------------------
"""

    # -----------------------------------------------------
    # POSSIBLE TEXT
    # -----------------------------------------------------

    possible_text = ""

    for result in possible:

        possible_text += f"""
BNS SECTION {result['section']}
Title: {result.get('title', '')}

Section text:
{result.get('section_text', result.get('text', ''))}

Reason:
{result.get('reason', '')}

Missing ingredients:
{result.get('missing_ingredients', [])}

--------------------------------
"""

    # -----------------------------------------------------
    # FINAL PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are the final legal answer generator for an Indian
Bharatiya Nyaya Sanhita (BNS) legal-analysis system.

The system has already:

1. extracted explicit facts;
2. retrieved candidate BNS sections;
3. verified candidate sections;
4. applied deterministic legal rules.

You MUST rely only on the verified information supplied below.

==================================================
USER QUESTION
==================================================

{question}

==================================================
EXPLICIT FACTS
==================================================

{facts_text}

==================================================
AUTHORIZED BNS SECTION NUMBERS
==================================================

The ONLY BNS section numbers you are authorized to mention are:

{allowed_section_text}

You MUST NOT mention ANY other BNS section number.

Do not introduce sections from general legal knowledge.

Do not infer new sections.

Do not mention a section merely because it is legally related.

==================================================
CONCLUSIVELY VERIFIED SECTIONS
==================================================

{applicable_text}

==================================================
POSSIBLE BUT NOT CONCLUSIVE
==================================================

{possible_text}

==================================================
STRICT FINAL ANSWER RULES
==================================================

1. Mention ONLY sections under CONCLUSIVELY VERIFIED SECTIONS.

2. NEVER introduce another BNS section from your own knowledge.

3. NEVER mention a section under POSSIBLE BUT NOT CONCLUSIVE
   as an applicable section.

4. Do not invent facts.

5. Do not assume missing ingredients.

6. Do not convert allegations into established legal facts.

7. Do not use sections excluded by deterministic rules.

8. Do not add sections simply to make the answer comprehensive.

9. Clearly distinguish:

- offence/definition sections;
- punishment sections;
- other verified provisions.

10. Do not state punishment under a section that only defines
the offence.

11. State punishment only from the supplied statutory text.

12. For Section 101, explain why the supplied facts satisfy
the murder definition. Do not assign a specific clause unless
the verified facts support it.

13. For Section 103, explain that it is the punishment provision
for murder and use the supplied statutory punishment.

14. Do not require aggravated circumstances when ordinary
ingredients are already satisfied.

15. Do not invent aggravated circumstances.

16. Do not mention a completed offence as an attempt when
the completed result actually occurred.

17. Do not independently report a broader offence when the
specific completed offence has already been conclusively
established, where the deterministic rules have excluded it.

18. If no section is conclusively verified, answer exactly:

No BNS section can be conclusively identified from the provided facts.

19. If the facts are insufficient, do not guess.

20. Keep the answer concise and legally precise.

21. Do not mention:

- RAG;
- verifier;
- model;
- retrieval;
- prompts;
- system architecture;
- internal rules.

22. Do not mention unauthorized section numbers even as
examples or alternatives.

==================================================
ZERO SECTION RULE
==================================================

If the authorized section list is NONE:

Output exactly:

No BNS section can be conclusively identified from the provided facts.

Do not add anything else.

==================================================
ANSWER FORMAT
==================================================

For each conclusively applicable section:

BNS Section X — Title

Why it applies:
Brief explanation based only on the supplied facts.

If it is a punishment provision:
State the punishment only from the supplied statutory text.

Do not mention any unauthorized section number.
"""

    return ask_qwen(
        prompt,
        num_predict=900
    )


# =========================================================
# MAIN CASE ANALYSIS PIPELINE
# =========================================================

def analyze_case(
    question,
    document_text=""
):

    print(
        "\n" + "=" * 70
    )

    print(
        "STEP 1: FACT EXTRACTION"
    )

    print(
        "=" * 70
    )

    facts = extract_facts(
        question,
        document_text
    )

    print(
        "\nExtracted facts:"
    )

    print(
        facts
    )

    # -----------------------------------------------------
    # STEP 2
    # -----------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "STEP 2: BNS RETRIEVAL"
    )

    print(
        "=" * 70
    )

    candidates = build_bns_candidates(
        question
    )

    print(
        "\nRetrieved candidates:"
    )

    for candidate in candidates:

        score = candidate.get(
            "score",
            0
        )

        try:
            score = float(score)
        except (
            ValueError,
            TypeError
        ):
            score = 0

        print(
            f"Section {candidate['section']} | "
            f"{candidate.get('title', '')} | "
            f"Score: {score:.4f}"
        )

    # -----------------------------------------------------
    # STEP 3
    # -----------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "STEP 3: SECTION VERIFICATION"
    )

    print(
        "=" * 70
    )

    verified_results = verify_candidates(
        candidates,
        facts,
        question
    )

    for result in verified_results:

        print(
            f"Section {result['section']} "
            f"→ {result['decision']}"
        )

        print(
            f"Reason: {result.get('reason', '')}"
        )

    # -----------------------------------------------------
    # DETERMINISTIC RULES
    # -----------------------------------------------------

    applicable_sections = apply_section_rules(
        verified_results,
        facts
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "CONCLUSIVELY APPLICABLE SECTIONS"
    )

    print(
        "=" * 70
    )

    for result in applicable_sections:

        print(
            f"Section {result['section']} - "
            f"{result.get('title', '')}"
        )

    # -----------------------------------------------------
    # ZERO SECTION SAFEGUARD
    # -----------------------------------------------------

    if not applicable_sections:

        print(
            "None"
        )

        return (
            "No BNS section can be conclusively identified "
            "from the provided facts."
        )

    # -----------------------------------------------------
    # ATTACH SECTION TEXT
    # -----------------------------------------------------

    for result in verified_results:

        matching_candidate = next(
            (
                candidate
                for candidate in candidates
                if int(candidate["section"])
                == int(result["section"])
            ),
            None
        )

        if matching_candidate:

            result["section_text"] = (
                matching_candidate.get(
                    "text",
                    ""
                )
            )

    # -----------------------------------------------------
    # STEP 4
    # -----------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "STEP 4: FINAL ANSWER"
    )

    print(
        "=" * 70
    )

    answer = generate_final_legal_answer(
        question,
        facts,
        applicable_sections,
        verified_results
    )

    print(
        "\nGenerated answer:"
    )

    print(
        answer
    )

    # -----------------------------------------------------
    # STEP 5
    # -----------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "STEP 5: OUTPUT VALIDATION"
    )

    print(
        "=" * 70
    )

    allowed_sections = [
        result["section"]
        for result in applicable_sections
    ]

    validation = validate_output(
        answer,
        allowed_sections
    )

    if validation["valid"]:

        print(
            "Output validation: PASSED"
        )

        return answer

    print(
        "Output validation: FAILED"
    )

    print(
        "Unauthorized sections:",
        validation["unauthorized_sections"]
    )

    # -----------------------------------------------------
    # STRICT CORRECTION
    # -----------------------------------------------------

    allowed_text = ", ".join(
        str(section)
        for section in allowed_sections
    )

    if not allowed_text:

        return (
            "No BNS section can be conclusively identified "
            "from the provided facts."
        )

    correction_prompt = f"""
Rewrite the following legal answer.

ONLY these BNS section numbers are authorized:

{allowed_text}

Remove every mention of every other BNS section.

Do not add a new legal provision.

Do not add new facts.

Do not use general legal knowledge to introduce another
BNS section.

Return only the corrected answer.

ORIGINAL ANSWER:

{answer}
"""

    corrected_answer = ask_qwen(
        correction_prompt,
        num_predict=700
    )

    second_validation = validate_output(
        corrected_answer,
        allowed_sections
    )

    if second_validation["valid"]:

        return corrected_answer

    # -----------------------------------------------------
    # ABSOLUTE SAFE FALLBACK
    # -----------------------------------------------------

    section_list = ", ".join(
        f"BNS Section {section}"
        for section in allowed_sections
    )

    return (
        f"Based on the provided facts, the conclusively "
        f"identified provision(s) are: {section_list}. "
        f"The available facts should be reviewed further "
        f"before drawing additional legal conclusions."
    )


# =========================================================
# MAIN API FUNCTION
# =========================================================

def ask_ai(
    question,
    document_text="",
    filename=""
):

    question = (
        question or ""
    ).strip()

    # -----------------------------------------------------
    # QUESTION + DOCUMENT
    # -----------------------------------------------------

    if document_text and question:

        from backend.document_rag import (
            retrieve_document_chunks
        )

        document_results = retrieve_document_chunks(
            document_text,
            question,
            top_k=5
        )

        document_context = ""

        for result in document_results:

            document_context += f"""
{result['text']}

--------------------
"""

        combined_text = (
            f"User question:\n"
            f"{question}\n\n"
            f"Relevant document excerpts:\n"
            f"{document_context}"
        )

        return analyze_case(
            combined_text,
            document_text
        )

    # -----------------------------------------------------
    # DOCUMENT ONLY
    # -----------------------------------------------------

    elif document_text:

        from backend.document_rag import (
            get_document_chunks
        )

        chunks = get_document_chunks(
            document_text
        )

        chunk_summaries = []

        for i, chunk in enumerate(
            chunks,
            start=1
        ):

            summary = summarize_document_chunk(
                chunk,
                i,
                len(chunks)
            )

            chunk_summaries.append(
                summary
            )

        document_context = (
            "\n\n".join(
                chunk_summaries
            )
        )

        prompt = f"""
You are analyzing a legal document.

Below are summaries of different parts of the document.

{document_context}

Provide a concise overall analysis.

Cover:

- parties
- facts
- legal issues
- important legal provisions explicitly mentioned
- arguments
- court reasoning, if present
- decision or outcome, if present
- important findings

Rules:

- Do not invent information.
- Do not introduce legal sections that are not present
  in the document summaries.
- Clearly distinguish facts from legal conclusions.
- If the document is not a judgment, do not describe it
  as a judgment.

Give a structured but concise analysis.
"""

        return ask_qwen(
            prompt,
            num_predict=1200
        )

    # -----------------------------------------------------
    # QUESTION ONLY
    # -----------------------------------------------------

    else:

        return analyze_case(
            question
        )


# =========================================================
# PDF EXTRACTION
# =========================================================

def extract_pdf_text(
    file_content
):

    reader = PdfReader(
        io.BytesIO(
            file_content
        )
    )

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:

            text += (
                page_text
                + "\n"
            )

    text = text.strip()

    if not text:

        raise ValueError(
            "No readable text was found in the PDF."
        )

    return text


def get_document_chunks(
    document_text,
    chunk_size=2000,
    overlap=200
):
    """
    Split uploaded document text into overlapping chunks.
    """

    if not document_text:
        return []

    chunks = []

    start = 0
    text_length = len(document_text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length
        )

        chunk = document_text[
            start:end
        ].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks