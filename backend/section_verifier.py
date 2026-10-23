import json
import re
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b"

BATCH_SIZE = 8


# =========================================================
# QWEN
# =========================================================

def ask_qwen(prompt, num_predict=700):

    print(
        "[VERIFIER] Prompt characters:",
        len(prompt)
    )

    print(
        "[VERIFIER] Approx tokens:",
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

    return response.json().get(
        "response",
        ""
    )


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json(raw):

    if not raw:
        return None

    raw = raw.strip()

    # Remove markdown code fences.
    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        raw,
        re.DOTALL | re.IGNORECASE
    )

    if match:
        raw = match.group(1).strip()

    # Try direct JSON.
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Try JSON object.
    object_match = re.search(
        r"\{[\s\S]*\}",
        raw
    )

    if object_match:

        try:
            return json.loads(
                object_match.group(0)
            )
        except Exception:
            pass

    # Try JSON array.
    array_match = re.search(
        r"\[[\s\S]*\]",
        raw
    )

    if array_match:

        try:
            return json.loads(
                array_match.group(0)
            )
        except Exception:
            pass

    return None


def extract_batch_json(raw):

    data = extract_json(raw)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        if isinstance(
            data.get("results"),
            list
        ):
            return data["results"]

        if isinstance(
            data.get("sections"),
            list
        ):
            return data["sections"]

    return []


# =========================================================
# FACT TEXT
# =========================================================

def fact_field_text(
    facts,
    field
):

    if not isinstance(facts, dict):
        return ""

    values = facts.get(
        field,
        []
    )

    if not isinstance(values, list):
        return ""

    output = []

    for item in values:

        if isinstance(item, dict):

            value = (
                item.get("fact", "")
                or item.get("text", "")
            )

            if value:
                output.append(
                    str(value)
                )

        elif isinstance(item, str):

            if item.strip():
                output.append(
                    item.strip()
                )

    return " ".join(output)


def all_fact_text(facts):

    if not isinstance(facts, dict):
        return ""

    parts = []

    for key, values in facts.items():

        if key == "question_type":
            continue

        if not isinstance(values, list):
            continue

        for item in values:

            if isinstance(item, dict):

                value = (
                    item.get("fact", "")
                    or item.get("text", "")
                )

                if value:
                    parts.append(
                        f"{key}: {value}"
                    )

            elif isinstance(item, str):

                if item.strip():
                    parts.append(
                        f"{key}: {item.strip()}"
                    )

    return "\n".join(parts)


def factual_text_with_question(
    facts,
    question=""
):

    fact_text = all_fact_text(
        facts
    )

    if question:

        return (
            "USER QUESTION:\n"
            + question
            + "\n\n"
            + "EXPLICIT FACTS:\n"
            + fact_text
        )

    return (
        "EXPLICIT FACTS:\n"
        + fact_text
    )


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_decision(value):

    if not isinstance(
        value,
        str
    ):
        return "REJECT"

    value = value.strip().upper()

    if value in {
        "APPLICABLE",
        "POSSIBLE",
        "REJECT"
    }:
        return value

    return "REJECT"


def normalize_result(
    result,
    candidate
):

    try:
        section = int(
            result.get(
                "section",
                candidate.get("section")
            )
        )

    except Exception:

        section = int(
            candidate.get(
                "section"
            )
        )

    decision = normalize_decision(
        result.get(
            "decision",
            result.get(
                "result",
                "REJECT"
            )
        )
    )

    section_text = candidate.get(
        "text",
        ""
    )

    title = candidate.get(
        "title",
        ""
    )

    return {
        "section": section,
        "title": result.get(
            "title",
            title
        ),
        "section_type": result.get(
            "section_type",
            candidate.get(
                "section_type",
                "OTHER"
            )
        ),
        "decision": decision,
        "reason": str(
            result.get(
                "reason",
                ""
            )
        ).strip(),
        "supported_ingredients": (
            result.get(
                "supported_ingredients",
                []
            )
            if isinstance(
                result.get(
                    "supported_ingredients",
                    []
                ),
                list
            )
            else []
        ),
        "inferable_ingredients": (
            result.get(
                "inferable_ingredients",
                []
            )
            if isinstance(
                result.get(
                    "inferable_ingredients",
                    []
                ),
                list
            )
            else []
        ),
        "section_text": section_text
    }


# =========================================================
# DETERMINISTIC SAFETY CHECKS
# =========================================================

def has_completed_death(
    facts,
    question=""
):

    text = factual_text_with_question(
        facts,
        question
    ).lower()

    death_patterns = [
        "died",
        "death",
        "dead",
        "was killed",
        "were killed",
        "killed him",
        "killed her",
        "killed them",
        "caused his death",
        "caused her death",
        "caused their death",
        "resulting in death",
        "resulted in death",
        "murdered"
    ]

    return any(
        pattern in text
        for pattern in death_patterns
    )


def has_explicit_attempt_only(
    facts,
    question=""
):

    text = factual_text_with_question(
        facts,
        question
    ).lower()

    attempt_patterns = [
        "attempted to kill",
        "attempt to kill",
        "tried to kill",
        "attempted murder",
        "attempt to murder"
    ]

    completion_patterns = [
        "died",
        "death",
        "was killed",
        "were killed",
        "murdered",
        "caused his death",
        "caused her death",
        "caused their death"
    ]

    has_attempt = any(
        pattern in text
        for pattern in attempt_patterns
    )

    has_completion = any(
        pattern in text
        for pattern in completion_patterns
    )

    return (
        has_attempt
        and not has_completion
    )


def deterministic_reject(
    section,
    facts,
    candidate_text="",
    question=""
):

    text = factual_text_with_question(
        facts,
        question
    ).lower()

    candidate_text = (
        candidate_text or ""
    ).lower()

    # -----------------------------------------------------
    # IMPORTANT:
    # These are GENERAL safety gates.
    #
    # They do not determine an offence from keywords.
    # They only reject a candidate when its required
    # context is clearly absent.
    # -----------------------------------------------------

    # Attempt provisions should not be selected when the
    # facts clearly establish a completed death.
    if section in {
        109,
        110
    }:

        if has_completed_death(
            facts,
            question
        ):

            return (
                "REJECT",
                "The facts indicate a completed death, "
                "not merely an attempt."
            )

    # -----------------------------------------------------
    # Different-victim provisions
    # -----------------------------------------------------

    if section == 102:

        different_victim_patterns = [
            "person other than",
            "different person",
            "another person was killed",
            "another person died",
            "wrong person was killed",
            "wrong victim"
        ]

        if not any(
            pattern in text
            for pattern in different_victim_patterns
        ):

            return (
                "REJECT",
                "No fact establishes that a person "
                "other than the intended victim was killed."
            )

    # -----------------------------------------------------
    # Miscarriage / unborn child provisions
    # -----------------------------------------------------

    if section in {
        88,
        89,
        90,
        91,
        92
    }:

        pregnancy_patterns = [
            "pregnant",
            "pregnancy",
            "miscarriage",
            "unborn child",
            "quick unborn child",
            "foetus",
            "fetus"
        ]

        if not any(
            pattern in text
            for pattern in pregnancy_patterns
        ):

            return (
                "REJECT",
                "No pregnancy, miscarriage, "
                "or unborn-child facts are established."
            )

    # -----------------------------------------------------
    # Private defence provisions
    # -----------------------------------------------------

    if section in {
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
        43,
        44
    }:

        defence_patterns = [
            "private defence",
            "self defence",
            "self-defense",
            "defended himself",
            "defended herself",
            "defended themselves",
            "defending himself",
            "defending herself",
            "attacked first",
            "attack on him",
            "attack on her"
        ]

        if not any(
            pattern in text
            for pattern in defence_patterns
        ):

            return (
                "REJECT",
                "No private-defence facts are established."
            )

    # -----------------------------------------------------
    # Public-servant-specific provisions
    # -----------------------------------------------------

    if section in {
        198,
        199,
        200,
        201,
        202,
        203,
        204,
        205
    }:

        public_servant_patterns = [
            "public servant",
            "government officer",
            "government official",
            "police officer",
            "official duty",
            "government duty",
            "discharge of public functions"
        ]

        if not any(
            pattern in text
            for pattern in public_servant_patterns
        ):

            return (
                "REJECT",
                "No public-servant or official-duty "
                "context is established."
            )

    # -----------------------------------------------------
    # Completed offence vs attempt
    # -----------------------------------------------------

    if (
        section in {
            109,
            110
        }
        and not has_explicit_attempt_only(
            facts,
            question
        )
    ):

        if has_completed_death(
            facts,
            question
        ):

            return (
                "REJECT",
                "The facts indicate completion of the "
                "harm rather than merely an attempt."
            )

    return None


# =========================================================
# QWEN BATCH VERIFICATION
# =========================================================

def verify_batch(
    candidates,
    facts,
    question=""
):

    if not candidates:
        return []

    fact_text = factual_text_with_question(
        facts,
        question
    )

    candidate_blocks = []

    for index, candidate in enumerate(
        candidates,
        start=1
    ):

        section = candidate.get(
            "section"
        )

        title = candidate.get(
            "title",
            ""
        )

        section_text = candidate.get(
            "text",
            ""
        )

        # Keep enough statutory text for ingredient
        # verification, but avoid unnecessarily huge prompts.
        section_text = section_text[:5000]

        candidate_blocks.append(
            f"""
CANDIDATE {index}

BNS SECTION: {section}

TITLE:
{title}

STATUTORY TEXT:
{section_text}
"""
        )

    candidates_text = "\n".join(
        candidate_blocks
    )

    prompt = f"""
You are a conservative legal-section verifier.

Your task is to determine whether each candidate BNS
provision is supported by the explicit facts.

{fact_text}

CANDIDATE BNS PROVISIONS:

{candidates_text}

IMPORTANT RULES:

1. Evaluate every candidate independently.

2. Use the statutory text only to identify the legal
   ingredients of the candidate provision.

3. The statutory text is NOT evidence that the facts
   occurred.

4. Facts must come only from the user question or the
   explicitly extracted facts.

5. Do not invent facts.

6. Do not assume intention, knowledge, consent, ownership,
   possession, relationship, injury, death, or any other
   fact unless it is supported.

7. Do not select a section merely because its wording
   resembles another section.

8. A section is APPLICABLE only when its essential
   ingredients are supported by the supplied facts.

9. Use POSSIBLE only when the facts strongly indicate
   the provision but an essential factual element is
   genuinely unclear.

10. Otherwise use REJECT.

11. Do not use general legal knowledge to invent facts.

12. Do not classify an offence solely because another
    candidate provision appears applicable.

13. Evaluate all candidates.

14. Return exactly one result for EVERY candidate.

15. The "section" field must contain the candidate's
    section number.

16. Return ONLY valid JSON.

JSON FORMAT:

[
  {{
    "section": 123,
    "decision": "APPLICABLE",
    "reason": "Short explanation based only on the facts.",
    "supported_ingredients": [
      "ingredient supported by facts"
    ],
    "inferable_ingredients": []
  }}
]

Return one object for every candidate.
"""

    try:

        raw = ask_qwen(
            prompt,
            num_predict=max(
                600,
                min(
                    1200,
                    100 * len(candidates)
                )
            )
        )

        parsed = extract_batch_json(
            raw
        )

    except Exception as error:

        print(
            f"[VERIFIER] Qwen batch failed: {error}"
        )

        parsed = []

    # -----------------------------------------------------
    # INDEX QWEN RESULTS BY SECTION
    # -----------------------------------------------------

    qwen_by_section = {}

    for item in parsed:

        if not isinstance(
            item,
            dict
        ):
            continue

        try:

            section = int(
                item.get(
                    "section"
                )
            )

        except Exception:

            continue

        qwen_by_section[
            section
        ] = item

    # -----------------------------------------------------
    # IMPORTANT FIX:
    #
    # A missing Qwen result is NOT REJECT.
    #
    # It becomes VERIFICATION_ERROR so the caller knows
    # that the model failed to evaluate the candidate.
    # -----------------------------------------------------

    results = []

    for candidate in candidates:

        try:

            section = int(
                candidate.get(
                    "section"
                )
            )

        except Exception:

            continue

        candidate_text = candidate.get(
            "text",
            ""
        )

        # First apply deterministic safety gates.
        deterministic = deterministic_reject(
            section,
            facts,
            candidate_text,
            question
        )

        if deterministic is not None:

            decision, reason = deterministic

            results.append(
                {
                    "section": section,
                    "title": candidate.get(
                        "title",
                        ""
                    ),
                    "section_type": candidate.get(
                        "section_type",
                        "OTHER"
                    ),
                    "decision": decision,
                    "reason": reason,
                    "supported_ingredients": [],
                    "inferable_ingredients": [],
                    "section_text": candidate_text
                }
            )

            continue

        # -------------------------------------------------
        # QWEN RESULT EXISTS
        # -------------------------------------------------

        qwen_result = qwen_by_section.get(
            section
        )

        if qwen_result is not None:

            result = normalize_result(
                qwen_result,
                candidate
            )

            results.append(
                result
            )

            continue

        # -------------------------------------------------
        # QWEN DID NOT RETURN THIS SECTION
        #
        # DO NOT CALL IT REJECT.
        # -------------------------------------------------

        results.append(
            {
                "section": section,
                "title": candidate.get(
                    "title",
                    ""
                ),
                "section_type": candidate.get(
                    "section_type",
                    "OTHER"
                ),
                "decision": "VERIFICATION_ERROR",
                "reason": (
                    "The verifier did not return a "
                    "result for this section."
                ),
                "supported_ingredients": [],
                "inferable_ingredients": [],
                "section_text": candidate_text,
                "verification_error": True
            }
        )

    return results


# =========================================================
# VERIFY ALL CANDIDATES
# =========================================================

def verify_candidates(
    candidates,
    facts,
    question=""
):

    if not candidates:
        return []

    # Remove duplicate sections while preserving order.
    unique_candidates = []
    seen_sections = set()

    for candidate in candidates:

        try:

            section = int(
                candidate.get(
                    "section"
                )
            )

        except Exception:

            continue

        if section in seen_sections:
            continue

        seen_sections.add(
            section
        )

        unique_candidates.append(
            candidate
        )

    deterministic_count = 0
    qwen_candidates = []

    # -----------------------------------------------------
    # Run deterministic gates first.
    # -----------------------------------------------------

    preliminary_results = []

    for candidate in unique_candidates:

        try:

            section = int(
                candidate.get(
                    "section"
                )
            )

        except Exception:

            continue

        deterministic = deterministic_reject(
            section,
            facts,
            candidate.get(
                "text",
                ""
            ),
            question
        )

        if deterministic is not None:

            decision, reason = deterministic

            preliminary_results.append(
                {
                    "section": section,
                    "title": candidate.get(
                        "title",
                        ""
                    ),
                    "section_type": candidate.get(
                        "section_type",
                        "OTHER"
                    ),
                    "decision": decision,
                    "reason": reason,
                    "supported_ingredients": [],
                    "inferable_ingredients": [],
                    "section_text": candidate.get(
                        "text",
                        ""
                    )
                }
            )

            deterministic_count += 1

        else:

            qwen_candidates.append(
                candidate
            )

    print(
        f"[VERIFIER] Deterministic: "
        f"{deterministic_count} | "
        f"Qwen candidates: "
        f"{len(qwen_candidates)}"
    )

    # -----------------------------------------------------
    # Batch Qwen verification.
    # -----------------------------------------------------

    qwen_results = []

    for start in range(
        0,
        len(qwen_candidates),
        BATCH_SIZE
    ):

        batch = qwen_candidates[
            start:
            start + BATCH_SIZE
        ]

        print(
            f"[VERIFIER] Qwen batch "
            f"{(start // BATCH_SIZE) + 1}: "
            f"{len(batch)} sections"
        )

        batch_start = __import__(
            "time"
        ).perf_counter()

        batch_results = verify_batch(
            batch,
            facts,
            question
        )

        batch_time = (
            __import__(
                "time"
            ).perf_counter()
            - batch_start
        )

        print(
            f"[VERIFIER] Qwen call: "
            f"{batch_time:.2f}s"
        )

        qwen_results.extend(
            batch_results
        )

    # -----------------------------------------------------
    # Merge.
    # -----------------------------------------------------

    all_results = (
        preliminary_results
        + qwen_results
    )

    result_by_section = {}

    for result in all_results:

        try:

            section = int(
                result["section"]
            )

        except Exception:

            continue

        result_by_section[
            section
        ] = result

    # Preserve original RAG candidate order.
    final_results = []

    for candidate in unique_candidates:

        try:

            section = int(
                candidate["section"]
            )

        except Exception:

            continue

        result = result_by_section.get(
            section
        )

        if result is None:

            result = {
                "section": section,
                "title": candidate.get(
                    "title",
                    ""
                ),
                "section_type": candidate.get(
                    "section_type",
                    "OTHER"
                ),
                "decision": "VERIFICATION_ERROR",
                "reason": (
                    "No verification result was "
                    "available for this section."
                ),
                "supported_ingredients": [],
                "inferable_ingredients": [],
                "section_text": candidate.get(
                    "text",
                    ""
                ),
                "verification_error": True
            }

        final_results.append(
            result
        )

    applicable_count = sum(
        1
        for result in final_results
        if result.get(
            "decision"
        ) == "APPLICABLE"
    )

    possible_count = sum(
        1
        for result in final_results
        if result.get(
            "decision"
        ) == "POSSIBLE"
    )

    reject_count = sum(
        1
        for result in final_results
        if result.get(
            "decision"
        ) == "REJECT"
    )

    verification_error_count = sum(
        1
        for result in final_results
        if result.get(
            "decision"
        ) == "VERIFICATION_ERROR"
    )

    print(
        f"[VERIFIER] Final: "
        f"APPLICABLE={applicable_count}, "
        f"POSSIBLE={possible_count}, "
        f"REJECT={reject_count}, "
        f"VERIFICATION_ERROR={verification_error_count}"
    )

    return final_results


# =========================================================
# GET APPLICABLE SECTIONS
# =========================================================

def get_applicable_sections(
    verified_results
):

    return [
        result
        for result in verified_results
        if result.get(
            "decision"
        ) == "APPLICABLE"
    ]




# import json
# import re
# import time
# import requests


# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL_NAME = "qwen3:8b"

# BATCH_SIZE = 8


# # ============================================================
# # QWEN
# # ============================================================

# def ask_qwen(prompt, num_predict=500):
#     start = time.time()

#     try:
#         response = requests.post(
#             OLLAMA_URL,
#             json={
#                 "model": MODEL_NAME,
#                 "prompt": prompt,
#                 "stream": False,
#                 "think": False,
#                 "options": {
#                     "temperature": 0.0,
#                     "num_predict": num_predict
#                 }
#             },
#             timeout=180
#         )

#         response.raise_for_status()

#         elapsed = time.time() - start
#         print(f"[QWEN] {elapsed:.2f} sec")

#         data = response.json()
#         return data.get("response", "")

#     except Exception as e:
#         elapsed = time.time() - start
#         print(f"[QWEN ERROR] {elapsed:.2f} sec | {e}")
#         return ""


# # ============================================================
# # JSON HELPERS
# # ============================================================

# def extract_json(text):
#     if not text:
#         return None

#     text = text.strip()

#     try:
#         return json.loads(text)
#     except Exception:
#         pass

#     text = re.sub(
#         r"```json\s*",
#         "",
#         text,
#         flags=re.IGNORECASE
#     )

#     text = re.sub(
#         r"```\s*",
#         "",
#         text
#     )

#     try:
#         return json.loads(text.strip())
#     except Exception:
#         pass

#     start = text.find("{")

#     if start != -1:

#         depth = 0
#         in_string = False
#         escape = False

#         for i in range(
#             start,
#             len(text)
#         ):

#             ch = text[i]

#             if in_string:

#                 if escape:
#                     escape = False

#                 elif ch == "\\":
#                     escape = True

#                 elif ch == '"':
#                     in_string = False

#                 continue

#             if ch == '"':
#                 in_string = True

#             elif ch == "{":
#                 depth += 1

#             elif ch == "}":

#                 depth -= 1

#                 if depth == 0:

#                     candidate = text[
#                         start:i + 1
#                     ]

#                     try:
#                         return json.loads(
#                             candidate
#                         )
#                     except Exception:
#                         break

#     return None


# def extract_batch_json(text):
#     if not text:
#         return None

#     text = text.strip()

#     try:

#         data = json.loads(text)

#         if isinstance(
#             data,
#             list
#         ):
#             return data

#         if isinstance(
#             data,
#             dict
#         ):

#             if isinstance(
#                 data.get("results"),
#                 list
#             ):
#                 return data["results"]

#             return [data]

#     except Exception:
#         pass

#     text = re.sub(
#         r"```json\s*",
#         "",
#         text,
#         flags=re.IGNORECASE
#     )

#     text = re.sub(
#         r"```\s*",
#         "",
#         text
#     )

#     # --------------------------------------------------------
#     # Balanced JSON array
#     # --------------------------------------------------------

#     start = text.find("[")

#     if start != -1:

#         depth = 0
#         in_string = False
#         escape = False

#         for i in range(
#             start,
#             len(text)
#         ):

#             ch = text[i]

#             if in_string:

#                 if escape:
#                     escape = False

#                 elif ch == "\\":
#                     escape = True

#                 elif ch == '"':
#                     in_string = False

#                 continue

#             if ch == '"':
#                 in_string = True

#             elif ch == "[":
#                 depth += 1

#             elif ch == "]":

#                 depth -= 1

#                 if depth == 0:

#                     candidate = text[
#                         start:i + 1
#                     ]

#                     try:

#                         data = json.loads(
#                             candidate
#                         )

#                         if isinstance(
#                             data,
#                             list
#                         ):
#                             return data

#                     except Exception:
#                         break

#     # --------------------------------------------------------
#     # Multiple JSON objects
#     # --------------------------------------------------------

#     objects = []

#     for match in re.finditer(
#         r"\{",
#         text
#     ):

#         start = match.start()

#         depth = 0
#         in_string = False
#         escape = False

#         for i in range(
#             start,
#             len(text)
#         ):

#             ch = text[i]

#             if in_string:

#                 if escape:
#                     escape = False

#                 elif ch == "\\":
#                     escape = True

#                 elif ch == '"':
#                     in_string = False

#                 continue

#             if ch == '"':
#                 in_string = True

#             elif ch == "{":
#                 depth += 1

#             elif ch == "}":

#                 depth -= 1

#                 if depth == 0:

#                     candidate = text[
#                         start:i + 1
#                     ]

#                     try:

#                         obj = json.loads(
#                             candidate
#                         )

#                         if isinstance(
#                             obj,
#                             dict
#                         ):
#                             objects.append(
#                                 obj
#                             )

#                     except Exception:
#                         pass

#                     break

#     if objects:
#         return objects

#     return None


# # ============================================================
# # FACT HELPERS
# # ============================================================

# def facts_to_compact_text(facts):

#     if not isinstance(
#         facts,
#         dict
#     ):
#         return ""

#     parts = []

#     for key, value in facts.items():

#         if value is None:
#             continue

#         if isinstance(
#             value,
#             list
#         ):

#             values = []

#             for item in value:

#                 if item is None:
#                     continue

#                 if isinstance(
#                     item,
#                     dict
#                 ):

#                     values.append(
#                         json.dumps(
#                             item,
#                             ensure_ascii=False
#                         )
#                     )

#                 else:

#                     values.append(
#                         str(item)
#                     )

#             if values:

#                 parts.append(
#                     f"{key}: "
#                     + "; ".join(values)
#                 )

#         elif isinstance(
#             value,
#             dict
#         ):

#             parts.append(
#                 f"{key}: "
#                 + json.dumps(
#                     value,
#                     ensure_ascii=False
#                 )
#             )

#         else:

#             value_text = str(
#                 value
#             ).strip()

#             if value_text:

#                 parts.append(
#                     f"{key}: "
#                     + value_text
#                 )

#     return "\n".join(parts)


# def all_fact_text(facts):

#     if not isinstance(
#         facts,
#         dict
#     ):
#         return ""

#     parts = []

#     for key, value in facts.items():

#         if value is None:
#             continue

#         if isinstance(
#             value,
#             list
#         ):

#             for item in value:

#                 if item is not None:

#                     parts.append(
#                         str(item)
#                     )

#         elif isinstance(
#             value,
#             dict
#         ):

#             parts.append(
#                 json.dumps(
#                     value,
#                     ensure_ascii=False
#                 )
#             )

#         else:

#             parts.append(
#                 str(value)
#             )

#     return " ".join(
#         parts
#     ).lower()


# def fact_field_text(
#     facts,
#     field
# ):

#     if not isinstance(
#         facts,
#         dict
#     ):
#         return ""

#     value = facts.get(
#         field,
#         ""
#     )

#     if isinstance(
#         value,
#         list
#     ):

#         return " ".join(
#             str(x)
#             for x in value
#             if x is not None
#         ).lower()

#     if isinstance(
#         value,
#         dict
#     ):

#         return json.dumps(
#             value,
#             ensure_ascii=False
#         ).lower()

#     return str(
#         value
#     ).lower()


# # ============================================================
# # GENERAL FACTUAL DETECTION
# # ============================================================

# def contains_any(
#     text,
#     patterns
# ):

#     text = (
#         text or ""
#     ).lower()

#     return any(
#         pattern.lower() in text
#         for pattern in patterns
#     )


# def facts_indicate_different_victim(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     patterns = [
#         "different victim",
#         "mistaken identity",
#         "another person",
#         "another victim",
#         "unintended victim",
#         "wrong person",
#         "intended to kill",
#         "intended victim",
#         "instead killed"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# # ============================================================
# # MURDER / DEATH
# # ============================================================

# def has_completed_murder_pattern(
#     facts,
#     question=""
# ):

#     facts_text = all_fact_text(
#         facts
#     )

#     if not facts_text:
#         return False

#     death_patterns = [
#         "died",
#         "death",
#         "dead",
#         "deceased",
#         "resulting in death",
#         "resulted in death",
#         "causing death",
#         "caused death",
#         "killed"
#     ]

#     lethal_patterns = [
#         "stabbed",
#         "stabbing",
#         "stab",
#         "knife",
#         "sword",
#         "gun",
#         "firearm",
#         "pistol",
#         "shot",
#         "shooting",
#         "repeated blows",
#         "repeatedly struck",
#         "struck with",
#         "hit with",
#         "blow with",
#         "weapon",
#         "choked",
#         "strangled"
#     ]

#     kill_patterns = [
#         "kill",
#         "killing",
#         "murder",
#         "murdered",
#         "intended to kill",
#         "intention to kill"
#     ]

#     has_death = contains_any(
#         facts_text,
#         death_patterns
#     )

#     has_lethal = contains_any(
#         facts_text,
#         lethal_patterns
#     )

#     has_kill = contains_any(
#         facts_text,
#         kill_patterns
#     )

#     return (
#         has_death
#         and
#         (
#             has_lethal
#             or
#             has_kill
#         )
#     )


# # ============================================================
# # PROPERTY OFFENCE FACTUAL HELPERS
# # ============================================================

# def facts_indicate_direct_taking(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     taking_patterns = [
#         "takes",
#         "took",
#         "take",
#         "taken",
#         "stole",
#         "stolen",
#         "steals",
#         "removed",
#         "removes",
#         "carried away",
#         "carried off",
#         "secretly takes",
#         "secretly took",
#         "dishonestly takes",
#         "dishonestly took",
#         "grabbed",
#         "grab",
#         "snatched",
#         "snatched away",
#         "pulled the chain",
#         "pulled it with force",
#         "forcibly removed",
#         "forcibly took"
#     ]

#     return contains_any(
#         text,
#         taking_patterns
#     )


# def facts_indicate_without_consent(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     patterns = [
#         "without consent",
#         "without b's consent",
#         "without his consent",
#         "without her consent",
#         "without their consent",
#         "without permission",
#         "without the owner's consent",
#         "without permission of"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_indicate_dishonest_intent(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     patterns = [
#         "dishonest intention",
#         "dishonestly",
#         "intends to permanently keep",
#         "intend to permanently keep",
#         "intended to permanently keep",
#         "intention to permanently keep",
#         "intends to keep",
#         "intended to keep",
#         "permanently keep",
#         "permanently keeping",
#         "wrongfully retain",
#         "wrongfully retaining",
#         "intended to keep and escape",
#         "keep it and escape"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_indicate_prior_possession(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     prior_possession_patterns = [
#         "was given",
#         "was entrusted",
#         "entrusted with",
#         "given to a",
#         "given to him",
#         "given to her",
#         "given to them",
#         "received",
#         "received the property",
#         "received the phone",
#         "received the mobile",
#         "already possessed",
#         "already had",
#         "was in his possession",
#         "was in her possession",
#         "was in their possession",
#         "had possession",
#         "had custody",
#         "kept safely",
#         "asked to keep",
#         "given for safekeeping",
#         "found",
#         "found the property",
#         "found the phone",
#         "found the mobile",
#         "lawfully possessed",
#         "lawfully obtained",
#         "lawfully received",
#         "came into his possession",
#         "came into her possession",
#         "came into their possession"
#     ]

#     return contains_any(
#         text,
#         prior_possession_patterns
#     )


# def facts_indicate_misappropriation_after_possession(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     conversion_patterns = [
#         "misappropriated",
#         "misappropriation",
#         "converted to his own use",
#         "converted to her own use",
#         "converted to their own use",
#         "dishonestly converted",
#         "dishonestly converts",
#         "refused to return",
#         "refuses to return",
#         "kept it despite",
#         "kept the property despite",
#         "kept the phone despite",
#         "kept the mobile despite",
#         "used it as his own",
#         "used it as her own",
#         "used the property as his own",
#         "used the property as her own",
#         "appropriated it",
#         "appropriated the property"
#     ]

#     return contains_any(
#         text,
#         conversion_patterns
#     )


# def facts_indicate_dwelling_house(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     dwelling_patterns = [
#         "dwelling house",
#         "dwelling",
#         "house",
#         "residence",
#         "residential house",
#         "home",
#         "his house",
#         "her house",
#         "their house",
#         "b's house",
#         "a's house",
#         "human dwelling",
#         "place of residence"
#     ]

#     return contains_any(
#         text,
#         dwelling_patterns
#     )


# def facts_indicate_clerk_or_servant(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     patterns = [
#         "clerk",
#         "servant",
#         "employee",
#         "domestic servant",
#         "servant of",
#         "employee of",
#         "works for b",
#         "worked for b",
#         "works as a clerk",
#         "worked as a clerk"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_indicate_stolen_property_received_or_retained(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     receive_patterns = [
#         "received stolen property",
#         "received the stolen",
#         "received stolen goods",
#         "retained stolen property",
#         "retained the stolen",
#         "kept stolen property",
#         "kept the stolen",
#         "possessed stolen property",
#         "possessed the stolen",
#         "sold stolen property",
#         "disposed of stolen property",
#         "bought stolen property",
#         "purchased stolen property",
#         "received it knowing it was stolen",
#         "knew it was stolen",
#         "knowing it to be stolen",
#         "believed it to be stolen",
#         "reason to believe it was stolen"
#     ]

#     return contains_any(
#         text,
#         receive_patterns
#     )


# def facts_indicate_force_during_theft(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     force_patterns = [
#         "grabbed",
#         "grab",
#         "snatched",
#         "pulled with force",
#         "pulled it with force",
#         "forcibly",
#         "used force",
#         "physical force",
#         "criminal force",
#         "pushed",
#         "struck",
#         "hit",
#         "restrained",
#         "wrestled",
#         "dragged"
#     ]

#     return contains_any(
#         text,
#         force_patterns
#     )


# def facts_indicate_property_worn_or_carried(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     patterns = [
#         "around her neck",
#         "around his neck",
#         "around their neck",
#         "worn",
#         "wearing",
#         "carrying",
#         "carried by",
#         "in her hand",
#         "in his hand",
#         "in their hand",
#         "held by her",
#         "held by him",
#         "held by them",
#         "on her person",
#         "on his person",
#         "on their person",
#         "attached to her",
#         "attached to him",
#         "attached to them",
#         "necklace",
#         "gold chain around"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_indicate_theft_force_carried_property(
#     facts
# ):

#     return (
#         facts_indicate_direct_taking(
#             facts
#         )
#         and
#         facts_indicate_force_during_theft(
#             facts
#         )
#         and
#         facts_indicate_property_worn_or_carried(
#             facts
#         )
#     )


# def facts_indicate_separate_323_conduct(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     patterns = [
#         "concealed the property",
#         "concealed property",
#         "hid the property",
#         "hid the stolen property",
#         "hidden the property",
#         "assisted in concealment",
#         "assisted in the concealment",
#         "assisted in removal",
#         "fraudulently released a demand",
#         "fraudulently released a claim",
#         "dishonestly released a demand",
#         "dishonestly released a claim",
#         "released the demand",
#         "released the claim"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_contain_robbery_or_dacoity(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     patterns = [
#         "robbery",
#         "robbed",
#         "dacoity",
#         "dacoits",
#         "rob",
#         "extortion",
#         "fear of instant death",
#         "fear of instant hurt",
#         "fear of instant wrongful restraint",
#         "used force while taking",
#         "used violence while taking",
#         "threatened while taking",
#         "threatened immediate harm"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# # ============================================================
# # TRESPASS / HOUSE-TRESPASS FACTUAL HELPERS
# # ============================================================

# def facts_indicate_explicit_entry(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     entry_patterns = [
#         "entered the room",
#         "entered b's room",
#         "entered the house",
#         "entered b's house",
#         "entered the dwelling",
#         "entered the residence",
#         "went into the room",
#         "went inside the room",
#         "went into b's room",
#         "went inside b's room",
#         "went into the house",
#         "went inside the house",
#         "went into b's house",
#         "went inside b's house",
#         "entered the premises",
#         "entered the property",
#         "entered the building",
#         "entered the dwelling",
#         "came inside",
#         "came into the room",
#         "came into the house",
#         "was inside the room",
#         "was inside b's room",
#         "was inside the house",
#         "was inside b's house",
#         "trespassed",
#         "trespass",
#         "made entry",
#         "gained entry",
#         "unlawfully entered"
#     ]

#     return contains_any(
#         text,
#         entry_patterns
#     )


# def facts_indicate_trespass(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     trespass_patterns = [
#         "criminal trespass",
#         "house trespass",
#         "house-trespass",
#         "unlawfully entered",
#         "entered without permission",
#         "entered without consent",
#         "entered the property without permission",
#         "entered the house without permission",
#         "entered the room without permission",
#         "entered b's room without permission",
#         "entered b's house without permission",
#         "entered with intent to commit an offence",
#         "entered in order to commit an offence",
#         "entered intending to commit an offence",
#         "entered to commit theft",
#         "entered to commit robbery",
#         "entered to commit an offence",
#         "remained unlawfully",
#         "remained after permission was withdrawn"
#     ]

#     return contains_any(
#         text,
#         trespass_patterns
#     )


# def facts_indicate_intent_for_trespass(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     intent_patterns = [
#         "entered with intent to commit",
#         "entered intending to commit",
#         "entered in order to commit",
#         "entered to commit",
#         "entered for the purpose of committing",
#         "entered with the intention of committing",
#         "entered intending to steal",
#         "entered with intent to steal",
#         "entered in order to steal",
#         "entered to steal",
#         "entered for the purpose of stealing",
#         "entered with intention to steal"
#     ]

#     return contains_any(
#         text,
#         intent_patterns
#     )


# def facts_indicate_preparation_for_hurt_assault_restraint(
#     facts
# ):

#     text = all_fact_text(
#         facts
#     )

#     patterns = [
#         "prepared to cause hurt",
#         "prepared to cause assault",
#         "prepared to cause wrongful restraint",
#         "made preparation for hurt",
#         "made preparation for assault",
#         "made preparation for wrongful restraint",
#         "prepared for assault",
#         "prepared for hurt",
#         "prepared for wrongful restraint",
#         "carried a weapon to threaten",
#         "carried a weapon for assault",
#         "carried a weapon intending to assault",
#         "armed himself to assault",
#         "armed herself to assault",
#         "armed themselves to assault",
#         "prepared to attack",
#         "prepared to assault"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# # ============================================================
# # CONSERVATIVE UNRELATED-OFFENCE FACTUAL HELPERS
# # ============================================================

# def factual_text_with_question(
#     facts,
#     question=""
# ):

#     facts_text = all_fact_text(
#         facts
#     )

#     question_text = str(
#         question or ""
#     ).strip().lower()

#     return (
#         facts_text
#         + " "
#         + question_text
#     ).strip()


# def facts_indicate_public_servant_context(
#     facts,
#     question=""
# ):

#     text = factual_text_with_question(
#         facts,
#         question
#     )

#     patterns = [
#         "public servant",
#         "public officer",
#         "government officer",
#         "government official",
#         "government employee",
#         "government servant",
#         "civil servant",
#         "police officer",
#         "police inspector",
#         "police constable",
#         "police official",
#         "magistrate",
#         "judge",
#         "court officer",
#         "official duty",
#         "official capacity",
#         "government duty",
#         "government department",
#         "public office",
#         "government office",
#         "hospital",
#         "doctor",
#         "medical officer",
#         "medical practitioner",
#         "nurse",
#         "treatment of victim",
#         "refused treatment",
#         "denied treatment",
#         "non-treatment",
#         "police station",
#         "fir",
#         "first information report",
#         "uniform",
#         "badge",
#         "insignia",
#         "personated a police officer",
#         "pretended to be a police officer",
#         "pretended to be a public servant",
#         "pretended to be an officer"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_indicate_unlawful_assembly_context(
#     facts,
#     question=""
# ):

#     text = factual_text_with_question(
#         facts,
#         question
#     )

#     patterns = [
#         "unlawful assembly",
#         "assembly of five or more",
#         "five or more persons",
#         "five or more people",
#         "five persons",
#         "group of persons",
#         "group of people",
#         "group assembled",
#         "assembled together",
#         "assembly",
#         "assembled",
#         "members of the assembly",
#         "member of the assembly",
#         "common object",
#         "common purpose",
#         "rioting",
#         "riot",
#         "rioters",
#         "armed group",
#         "crowd",
#         "mob",
#         "hired persons",
#         "hired to join",
#         "engaged to join",
#         "commanded to disperse",
#         "ordered to disperse",
#         "failed to disperse",
#         "disperse the assembly",
#         "disperse the crowd"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_indicate_miscarriage_context(
#     facts,
#     question=""
# ):

#     text = factual_text_with_question(
#         facts,
#         question
#     )

#     patterns = [
#         "miscarriage",
#         "miscarried",
#         "cause miscarriage",
#         "caused miscarriage",
#         "causing miscarriage",
#         "pregnant",
#         "pregnancy",
#         "woman with child",
#         "with child",
#         "quick with child",
#         "foetus",
#         "fetus",
#         "foetal",
#         "fetal",
#         "unborn child",
#         "unborn baby",
#         "death of the foetus",
#         "death of the fetus",
#         "termination of pregnancy",
#         "abortion",
#         "aborted pregnancy",
#         "attempted abortion",
#         "intent to cause miscarriage"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_indicate_property_mark_context(
#     facts,
#     question=""
# ):

#     text = factual_text_with_question(
#         facts,
#         question
#     )

#     patterns = [
#         "property mark",
#         "property marks",
#         "false property mark",
#         "false property marks",
#         "counterfeit property mark",
#         "counterfeit property marks",
#         "counterfeiting a property mark",
#         "tampering with property mark",
#         "tampered with property mark",
#         "goods marked with",
#         "goods bearing a counterfeit mark",
#         "counterfeit mark on goods",
#         "counterfeit mark on property",
#         "mark on goods",
#         "mark on property",
#         "mark denoting ownership",
#         "mark denoting that property belongs",
#         "label on goods",
#         "counterfeit label",
#         "false label on goods",
#         "counterfeit brand",
#         "counterfeit branding",
#         "forged brand mark",
#         "package bearing a false mark",
#         "receptacle bearing a false mark",
#         "false mark on a package",
#         "false mark on a receptacle",
#         "goods with counterfeit",
#         "sold goods with counterfeit mark"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# def facts_indicate_private_defence_context(
#     facts,
#     question=""
# ):

#     text = factual_text_with_question(
#         facts,
#         question
#     )

#     patterns = [
#         "private defence",
#         "right of private defence",
#         "self defence",
#         "self-defense",
#         "self defence",
#         "defended himself",
#         "defended herself",
#         "defended themselves",
#         "defend himself",
#         "defend herself",
#         "defend themselves",
#         "defending himself",
#         "defending herself",
#         "defending themselves",
#         "acted in self defence",
#         "acted in self-defense",
#         "acted in private defence",
#         "to protect himself",
#         "to protect herself",
#         "to protect themselves",
#         "protecting himself",
#         "protecting herself",
#         "protecting themselves",
#         "protect another person",
#         "protecting another person",
#         "protect his property",
#         "protect her property",
#         "protect their property",
#         "defend his property",
#         "defend her property",
#         "defend their property",
#         "attack",
#         "attacked",
#         "attacking",
#         "assaulted",
#         "assaulting",
#         "threatened",
#         "threatening",
#         "threat of injury",
#         "threat of death",
#         "apprehension of danger",
#         "apprehension of death",
#         "apprehension of grievous hurt",
#         "reasonable apprehension",
#         "attempted to attack",
#         "attempted assault"
#     ]

#     return contains_any(
#         text,
#         patterns
#     )


# # ============================================================
# # DETERMINISTIC REJECTION
# # ============================================================

# def deterministic_reject(
#     section,
#     facts,
#     candidate_text="",
#     question="",
#     available_sections=None
# ):

#     try:
#         section = int(
#             section
#         )

#     except Exception:
#         return None

#     facts_text = all_fact_text(
#         facts
#     )

#     available_sections = set(
#         available_sections or []
#     )

#     # ========================================================
#     # 34-44 — RIGHT OF PRIVATE DEFENCE
#     # ========================================================

#     if 34 <= section <= 44:

#         if not facts_indicate_private_defence_context(
#             facts,
#             question
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish a defensive situation, attack, threat, or protection of person or property required for the private-defence provisions."
#             }

#         return None

#     # ========================================================
#     # 88-92 — MISCARRIAGE / UNBORN CHILD
#     # ========================================================

#     if 88 <= section <= 92:

#         if not facts_indicate_miscarriage_context(
#             facts,
#             question
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish pregnancy, miscarriage, an unborn child, or another factual circumstance required for the miscarriage-related provision."
#             }

#         return None

#     # ========================================================
#     # 189-193 — UNLAWFUL ASSEMBLY / RIOT
#     # ========================================================

#     if 189 <= section <= 193:

#         if not facts_indicate_unlawful_assembly_context(
#             facts,
#             question
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish an assembly, group, riot, common object, or other factual circumstance required for the unlawful-assembly or riot-related provision."
#             }

#         return None

#     # ========================================================
#     # 198-205 — PUBLIC SERVANT / RELATED
#     # ========================================================

#     if 198 <= section <= 205:

#         if not facts_indicate_public_servant_context(
#             facts,
#             question
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish a public-servant, official-duty, hospital, or personation-related factual context required for this provision."
#             }

#         return None

#     # ========================================================
#     # 345-350 — PROPERTY MARKS
#     # ========================================================

#     if 345 <= section <= 350:

#         if not facts_indicate_property_mark_context(
#             facts,
#             question
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish a property mark, false or counterfeit mark, marked goods, or a related property-mark circumstance required for this provision."
#             }

#         return None

#     # ========================================================
#     # 303 — THEFT
#     # ========================================================

#     if section == 303:

#         direct_taking = facts_indicate_direct_taking(
#             facts
#         )

#         if contains_any(
#             facts_text,
#             [
#                 "with consent",
#                 "with his consent",
#                 "with her consent",
#                 "with their consent",
#                 "with permission",
#                 "owner gave permission"
#             ]
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts indicate that the property was taken with consent or permission."
#             }

#         if (
#             facts_indicate_prior_possession(
#                 facts
#             )
#             and
#             facts_indicate_misappropriation_after_possession(
#                 facts
#             )
#             and
#             not direct_taking
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts describe prior possession followed by subsequent misappropriation rather than direct taking from another's possession."
#             }

#         return None

#     # ========================================================
#     # 305 — THEFT IN QUALIFYING LOCATION
#     # ========================================================

#     if section == 305:

#         if not facts_indicate_dwelling_house(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not explicitly establish a qualifying location required for Section 305."
#             }

#         return None

#     # ========================================================
#     # 306 — THEFT BY CLERK OR SERVANT
#     # ========================================================

#     if section == 306:

#         if not facts_indicate_clerk_or_servant(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish the required clerk, servant, employee, or employment relationship."
#             }

#         return None

#     # ========================================================
#     # 314 — DISHONEST MISAPPROPRIATION
#     # ========================================================

#     if section == 314:

#         prior_possession = facts_indicate_prior_possession(
#             facts
#         )

#         subsequent_conversion = facts_indicate_misappropriation_after_possession(
#             facts
#         )

#         direct_taking = facts_indicate_direct_taking(
#             facts
#         )

#         if not prior_possession:

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish prior possession or control of the property before the alleged misappropriation."
#             }

#         if not subsequent_conversion:

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish subsequent dishonest misappropriation or conversion."
#             }

#         if (
#             direct_taking
#             and
#             facts_indicate_without_consent(
#                 facts
#             )
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts describe direct taking from another's possession without consent rather than subsequent dishonest misappropriation."
#             }

#         return None

#     # ========================================================
#     # 317 — STOLEN PROPERTY
#     # ========================================================

#     if section == 317:

#         if facts_indicate_direct_taking(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts describe the accused directly taking the property rather than subsequently receiving or retaining stolen property."
#             }

#         if not facts_indicate_stolen_property_received_or_retained(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish receiving, retaining, possessing, buying, or disposing of stolen property with the required knowledge or reason to believe it was stolen."
#             }

#         return None

#     # ========================================================
#     # 323 — DISHONEST / FRAUDULENT REMOVAL OR CONCEALMENT
#     # ========================================================

#     if section == 323:

#         direct_theft = (
#             facts_indicate_direct_taking(
#                 facts
#             )
#             and
#             facts_indicate_without_consent(
#                 facts
#             )
#             and
#             facts_indicate_dishonest_intent(
#                 facts
#             )
#         )

#         separate_conduct = facts_indicate_separate_323_conduct(
#             facts
#         )

#         if (
#             direct_theft
#             and
#             not separate_conduct
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts establish direct theft from another's possession. Mere physical removal of the stolen property does not independently establish the separate dishonest or fraudulent removal, concealment, assistance, or release conduct contemplated by Section 323."
#             }

#         return None

#     # ========================================================
#     # 311 — ROBBERY / DACOITY
#     # ========================================================

#     if section == 311:

#         if not facts_contain_robbery_or_dacoity(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The extracted facts do not establish robbery, dacoity, or the required accompanying force, threat, or fear."
#             }

#         return None

#     # ========================================================
#     # 329 — CRIMINAL TRESPASS
#     # ========================================================

#     if section == 329:

#         if not (
#             facts_indicate_explicit_entry(
#                 facts
#             )
#             or
#             facts_indicate_trespass(
#                 facts
#             )
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not explicitly establish entry or remaining on another's property in a manner supporting criminal trespass or house-trespass."
#             }

#         return None

#     # ========================================================
#     # 330 — HOUSE-TRESPASS / HOUSE-BREAKING
#     # ========================================================

#     if section == 330:

#         if not facts_indicate_explicit_entry(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not explicitly establish entry into the relevant house, building, or premises."
#             }

#         return None

#     # ========================================================
#     # 331 — HOUSE-TRESPASS / HOUSE-BREAKING
#     # ========================================================

#     if section == 331:

#         if not facts_indicate_explicit_entry(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish the underlying house-trespass or house-breaking conduct required for Section 331."
#             }

#         return None

#     # ========================================================
#     # 332 — HOUSE-TRESPASS TO COMMIT OFFENCE
#     # ========================================================

#     if section == 332:

#         if not facts_indicate_explicit_entry(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not explicitly establish entry into the premises."
#             }

#         if not facts_indicate_intent_for_trespass(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish the required intention at the time of entry."
#             }

#         return None

#     # ========================================================
#     # 333 — HOUSE-TRESPASS AFTER PREPARATION
#     # ========================================================

#     if section == 333:

#         if not facts_indicate_explicit_entry(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish the required entry into the premises."
#             }

#         if not facts_indicate_preparation_for_hurt_assault_restraint(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish preparation for causing hurt, assault, or wrongful restraint."
#             }

#         return None

#     # ========================================================
#     # 102 — DIFFERENT / UNINTENDED VICTIM
#     # ========================================================

#     if section == 102:

#         if not facts_indicate_different_victim(
#             facts
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish that the death or injury was caused to a different or unintended victim."
#             }

#         return None

#     # ========================================================
#     # 109 / 110 — ATTEMPT
#     # ========================================================

#     if section in (
#         109,
#         110
#     ):

#         if has_completed_murder_pattern(
#             facts,
#             question
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts indicate completed death resulting from lethal conduct, so an attempt provision is not appropriate."
#             }

#         return None

#     # ========================================================
#     # 105 — CULPABLE HOMICIDE NOT AMOUNTING TO MURDER
#     # ========================================================

#     if section == 105:

#         if has_completed_murder_pattern(
#             facts,
#             question
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts indicate a completed lethal act consistent with the murder pattern; Section 105 should not be retained when murder is established."
#             }

#         return None

#     # ========================================================
#     # 57 — GROUP / COMMON PURPOSE
#     # ========================================================

#     if section == 57:

#         group_text = fact_field_text(
#             facts,
#             "group_or_assembly_facts"
#         )

#         if not group_text:

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts do not establish an independent factual basis for the group-related provision."
#             }

#         return None

#     # ========================================================
#     # 49 — ABETMENT / INSTRUCTION
#     # ========================================================

#     if section == 49:

#         orders_text = fact_field_text(
#             facts,
#             "orders_or_directions"
#         )

#         if (
#             orders_text
#             and
#             not contains_any(
#                 orders_text,
#                 [
#                     "abet",
#                     "abetted",
#                     "instigated",
#                     "instigation",
#                     "intentionally aided",
#                     "aided",
#                     "conspired",
#                     "encouraged the offence"
#                 ]
#             )
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts show an order or direction but do not independently establish the required abetment conduct."
#             }

#         return None

#     # ========================================================
#     # 131 — GENERAL ASSAULT / CRIMINAL FORCE
#     # ========================================================
#     #
#     # Only reject deterministically when the facts clearly
#     # establish the more specific Section 134 pattern AND
#     # Section 134 is actually among the retrieved candidates.
#     #
#     # This avoids hardcoding Section 131 out of ordinary assault
#     # cases where Section 134 is not relevant.
#     # ========================================================

#     if section == 131:

#         if (
#             134 in available_sections
#             and
#             facts_indicate_theft_force_carried_property(
#                 facts
#             )
#         ):

#             return {
#                 "section": section,
#                 "decision": "REJECT",
#                 "reason": "The facts establish the more specific pattern of force used during theft of property being worn or carried by the victim; Section 134 addresses that specific conduct."
#             }

#         return None

#     # ========================================================
#     # 103 — PUNISHMENT FOR MURDER
#     # ========================================================

#     if section == 103:

#         return None

#     # ========================================================
#     # 101 — MURDER
#     # ========================================================

#     if section == 101:

#         if has_completed_murder_pattern(
#             facts,
#             question
#         ):

#             return {
#                 "section": section,
#                 "decision": "APPLICABLE",
#                 "confidence": 0.90,
#                 "reason": "The facts explicitly establish death together with lethal conduct, providing a strong factual basis for the murder provision.",
#                 "missing_ingredients": [],
#                 "infer_murder_mental_element": True
#             }

#         return None

#     return None


# # ============================================================
# # NORMALIZATION
# # ============================================================

# def normalize_result(
#     result,
#     section
# ):

#     if not isinstance(
#         result,
#         dict
#     ):

#         return {
#             "section": section,
#             "decision": "REJECT",
#             "confidence": 0.0,
#             "reason": "Invalid verifier response.",
#             "missing_ingredients": []
#         }

#     decision = str(
#         result.get(
#             "decision",
#             "REJECT"
#         )
#     ).upper().strip()

#     if decision not in {
#         "APPLICABLE",
#         "POSSIBLE",
#         "REJECT"
#     }:

#         decision = "REJECT"

#     try:

#         confidence = float(
#             result.get(
#                 "confidence",
#                 0.0
#             )
#         )

#     except Exception:

#         confidence = 0.0

#     confidence = max(
#         0.0,
#         min(
#             1.0,
#             confidence
#         )
#     )

#     missing = result.get(
#         "missing_ingredients",
#         []
#     )

#     if not isinstance(
#         missing,
#         list
#     ):

#         missing = [
#             str(missing)
#         ]

#     reason = str(
#         result.get(
#             "reason",
#             ""
#         )
#     ).strip()

#     normalized = {
#         "section": section,
#         "decision": decision,
#         "confidence": confidence,
#         "reason": reason,
#         "missing_ingredients": missing
#     }

#     if result.get(
#         "infer_murder_mental_element"
#     ):

#         normalized[
#             "infer_murder_mental_element"
#         ] = True

#     return normalized


# def finalize_result(
#     result,
#     section
# ):

#     result = normalize_result(
#         result,
#         section
#     )

#     # --------------------------------------------------------
#     # IMPORTANT:
#     # Do NOT downgrade APPLICABLE merely because Qwen
#     # returned a self-reported confidence below an arbitrary
#     # threshold.
#     #
#     # Decision is determined by legal element reasoning.
#     # Confidence is metadata only.
#     # --------------------------------------------------------

#     if result["decision"] == "APPLICABLE":

#         result["missing_ingredients"] = []

#     elif result["decision"] == "POSSIBLE":

#         if not result["missing_ingredients"]:

#             result["missing_ingredients"] = [
#                 "One or more material elements remain genuinely uncertain."
#             ]

#     return result


# # ============================================================
# # DETERMINISTIC RESULT
# # ============================================================

# def deterministic_result(
#     section,
#     facts,
#     candidate_text="",
#     question="",
#     available_sections=None
# ):

#     return deterministic_reject(
#         section,
#         facts,
#         candidate_text,
#         question,
#         available_sections
#     )


# # ============================================================
# # BATCH QWEN PROMPT
# # ============================================================

# def build_batch_prompt(
#     candidates,
#     facts,
#     question=""
# ):

#     facts_text = facts_to_compact_text(
#         facts
#     )

#     candidate_blocks = []

#     for candidate in candidates:

#         section = candidate.get(
#             "section",
#             candidate.get(
#                 "section_number",
#                 ""
#             )
#         )

#         title = candidate.get(
#             "title",
#             candidate.get(
#                 "section_title",
#                 ""
#             )
#         )

#         text = candidate.get(
#             "text",
#             candidate.get(
#                 "content",
#                 candidate.get(
#                     "statutory_text",
#                     ""
#                 )
#             )
#         )

#         candidate_blocks.append(
#             f"""
# SECTION: {section}
# TITLE: {title}

# STATUTORY TEXT:
# {text[:4500]}
# """
#         )

#     candidates_text = "\n".join(
#         candidate_blocks
#     )

#     prompt = f"""
# You are a strict BNS legal-section verification engine.

# Determine whether each retrieved section is legally supported by the FACTS.

# The task is element-based legal reasoning, not keyword matching.

# FACT SOURCES
# ------------
# Only the ORIGINAL QUESTION and EXTRACTED FACTS establish what happened.

# The statutory text tells you what the law requires.
# It is NEVER evidence that an event occurred.

# Never invent a fact.

# QUESTION
# --------
# {question}

# EXTRACTED FACTS
# ---------------
# {facts_text}

# LEGAL ELEMENT METHOD
# --------------------
# For each candidate:

# 1. Identify the material legal elements from its statutory text.
# 2. Identify the concrete conduct actually established by the facts.
# 3. Match facts to each material element.
# 4. If a material element is clearly absent or contradicted, REJECT.
# 5. If all material elements are supported, APPLICABLE.
# 6. Use POSSIBLE only when a material element is genuinely uncertain.

# Do not use POSSIBLE merely because the wording is imperfect.

# Concrete factual language must be translated into its legal meaning.

# Examples:

# "grabbed the chain around her neck and pulled it with force"
# = physical force applied to a person while removing property.

# "chain around her neck"
# = property being worn/carried by the person.

# "took the phone without consent and intended to keep it"
# = direct dishonest taking without consent.

# "entered the house"
# = factual entry.

# "was entrusted with the property"
# = prior possession/control.

# COMPARATIVE REASONING
# ---------------------
# Compare candidates where provisions overlap.

# A general provision must not automatically defeat a more specific provision.

# A specific provision must not be rejected merely because a general offence also appears possible.

# However, do not retain a general offence when the facts clearly establish a more specific provision that covers the same conduct and the statutory relationship indicates the specific provision governs.

# Do not automatically assume every overlapping offence is cumulative.

# PROPERTY OFFENCES
# -----------------
# Distinguish:

# - direct taking from another's possession;
# - prior possession followed by dishonest conversion;
# - receiving or retaining stolen property;
# - theft involving a special circumstance such as force or property worn/carried by a person;
# - dishonest or fraudulent removal/concealment provisions requiring their own factual circumstances.

# SECTION 303
# -----------
# Direct dishonest taking of movable property from another's possession without consent supports theft.

# SECTION 314
# -----------
# Requires prior possession/control followed by dishonest misappropriation or conversion.

# A direct taking from another's possession is not Section 314 merely because the accused later keeps the property.

# SECTION 317
# -----------
# Requires receiving, retaining, possessing, buying, or disposing of stolen property with the required knowledge/reason to believe.

# The original thief is not automatically a receiver of stolen property.

# SECTION 323
# -----------
# Do NOT treat every physical removal of another person's property as an independent Section 323 offence.

# For a direct theft scenario, require a distinct factual basis for the dishonest/fraudulent removal, concealment, assistance in concealment/removal, or dishonest release of a demand/claim contemplated by the provision.

# Do not simply reason:

# "property was removed -> Section 323."

# FORCE / PROPERTY CARRIED BY PERSON
# ----------------------------------
# If facts show:

# - force or physical contact,
# - during taking/attempted theft,
# - and the property was being worn or carried by the victim,

# recognize that this can satisfy the factual elements of the specific provision concerning theft of property worn or carried by a person.

# Do not require the exact phrase "criminal force".

# Do not require injury for force.

# Do not reject a specific force-during-theft provision merely because the general theft provision also applies.

# SECTION 131
# -----------
# Section 131 is a general assault/criminal-force punishment provision.

# If the facts instead clearly establish the more specific factual pattern of force used during theft of property worn/carried by the victim, compare Section 131 with the specific theft-related provision rather than automatically retaining both.

# Do not reject Section 131 in an ordinary assault case merely because there is no theft.

# TRESPASS
# --------
# Do not infer entry merely because property was taken "from a room" or "from a house".

# Later theft does not automatically prove intent at the time of entry.

# Later weapon use does not automatically prove preparation before entry.

# MURDER
# ------
# Explicit death plus clearly lethal conduct can support the murder provision when the facts establish the required mental element.

# If death is completed, do not classify the same completed lethal act as an attempt.

# OUTPUT RULES
# ------------
# Return ONLY a JSON array.

# Return EXACTLY ONE object for EVERY candidate.

# Do not omit candidates.

# Keep reasons short.

# For APPLICABLE:
# - missing_ingredients MUST be [].

# For REJECT:
# - identify the absent or contradicted material element.

# For POSSIBLE:
# - identify the genuinely uncertain material element.

# Schema:

# [
#   {{
#     "section": <number>,
#     "decision": "APPLICABLE" | "POSSIBLE" | "REJECT",
#     "confidence": <0.0 to 1.0>,
#     "reason": "<short reason>",
#     "missing_ingredients": []
#   }}
# ]

# Candidates
# ----------
# {candidates_text}
# """

#     return prompt


# # ============================================================
# # MISSING RESULT RETRY
# # ============================================================

# def build_retry_prompt(
#     candidates,
#     facts,
#     question=""
# ):

#     facts_text = facts_to_compact_text(
#         facts
#     )

#     candidate_blocks = []

#     for candidate in candidates:

#         section = candidate.get(
#             "section",
#             candidate.get(
#                 "section_number",
#                 ""
#             )
#         )

#         title = candidate.get(
#             "title",
#             candidate.get(
#                 "section_title",
#                 ""
#             )
#         )

#         text = candidate.get(
#             "text",
#             candidate.get(
#                 "content",
#                 candidate.get(
#                     "statutory_text",
#                     ""
#                 )
#             )
#         )

#         candidate_blocks.append(
#             f"""
# SECTION {section}
# TITLE: {title}
# LAW:
# {text[:4500]}
# """
#         )

#     prompt = f"""
# Return one JSON object for EACH candidate section below.

# Use only the question and extracted facts as evidence.

# Question:
# {question}

# Facts:
# {facts_text}

# Rules:
# - APPLICABLE = all material elements supported.
# - POSSIBLE = a material element is genuinely uncertain.
# - REJECT = a material element is clearly absent or contradicted.
# - Never invent facts.
# - Do not use statutory text as evidence.
# - For direct theft, do not automatically classify the same removal as Section 323.
# - Force used while taking property worn or carried by a victim supports the specific theft-related force provision.
# - A general assault provision should not replace a more specific theft-with-force provision when the specific elements are established.

# Return ONLY:

# [
#   {{
#     "section": <number>,
#     "decision": "APPLICABLE" | "POSSIBLE" | "REJECT",
#     "confidence": <0.0 to 1.0>,
#     "reason": "<short reason>",
#     "missing_ingredients": []
#   }}
# ]

# Candidates:
# {''.join(candidate_blocks)}
# """

#     return prompt


# # ============================================================
# # BATCH VERIFICATION
# # ============================================================

# def verify_batch(
#     candidates,
#     facts,
#     question="",
#     retry_missing=True
# ):

#     if not candidates:
#         return []

#     prompt = build_batch_prompt(
#         candidates,
#         facts,
#         question
#     )

#     num_predict = min(
#         900,
#         max(
#             400,
#             100 * len(candidates)
#         )
#     )

#     response = ask_qwen(
#         prompt,
#         num_predict=num_predict
#     )

#     parsed = extract_batch_json(
#         response
#     )

#     if not parsed:

#         print(
#             "[VERIFIER] Qwen batch returned invalid JSON."
#         )

#         if retry_missing:

#             print(
#                 "[VERIFIER] Retrying invalid batch."
#             )

#             retry_prompt = build_retry_prompt(
#                 candidates,
#                 facts,
#                 question
#             )

#             retry_response = ask_qwen(
#                 retry_prompt,
#                 num_predict=min(
#                     700,
#                     max(
#                         350,
#                         90 * len(candidates)
#                     )
#                 )
#             )

#             parsed = extract_batch_json(
#                 retry_response
#             )

#         if not parsed:

#             return [
#                 {
#                     "section": candidate.get(
#                         "section",
#                         candidate.get(
#                             "section_number",
#                             0
#                         )
#                     ),
#                     "decision": "REJECT",
#                     "confidence": 0.0,
#                     "reason": "Verifier response could not be parsed after retry.",
#                     "missing_ingredients": [],
#                     "verification_error": True
#                 }
#                 for candidate in candidates
#             ]

#     results_by_section = {}

#     for item in parsed:

#         if not isinstance(
#             item,
#             dict
#         ):
#             continue

#         try:

#             section = int(
#                 item.get(
#                     "section"
#                 )
#             )

#         except Exception:

#             continue

#         results_by_section[
#             section
#         ] = item

#     # --------------------------------------------------------
#     # Retry ONLY missing sections
#     # --------------------------------------------------------

#     missing_candidates = []

#     for candidate in candidates:

#         try:

#             section = int(
#                 candidate.get(
#                     "section",
#                     candidate.get(
#                         "section_number"
#                     )
#                 )
#             )

#         except Exception:

#             continue

#         if section not in results_by_section:

#             missing_candidates.append(
#                 candidate
#             )

#     if (
#         missing_candidates
#         and
#         retry_missing
#     ):

#         print(
#             "[VERIFIER] Missing Qwen results: "
#             + ", ".join(
#                 str(
#                     candidate.get(
#                         "section",
#                         candidate.get(
#                             "section_number"
#                         )
#                     )
#                 )
#                 for candidate in missing_candidates
#             )
#         )

#         print(
#             "[VERIFIER] Retrying missing sections."
#         )

#         retry_prompt = build_retry_prompt(
#             missing_candidates,
#             facts,
#             question
#         )

#         retry_response = ask_qwen(
#             retry_prompt,
#             num_predict=min(
#                 700,
#                 max(
#                     350,
#                     90 * len(
#                         missing_candidates
#                     )
#                 )
#             )
#         )

#         retry_parsed = extract_batch_json(
#             retry_response
#         )

#         if retry_parsed:

#             for item in retry_parsed:

#                 if not isinstance(
#                     item,
#                     dict
#                 ):
#                     continue

#                 try:

#                     section = int(
#                         item.get(
#                             "section"
#                         )
#                     )

#                 except Exception:

#                     continue

#                 results_by_section[
#                     section
#                 ] = item

#     results = []

#     for candidate in candidates:

#         try:

#             section = int(
#                 candidate.get(
#                     "section",
#                     candidate.get(
#                         "section_number"
#                     )
#                 )
#             )

#         except Exception:

#             continue

#         if section in results_by_section:

#             result = finalize_result(
#                 results_by_section[
#                     section
#                 ],
#                 section
#             )

#         else:

#             result = {
#                 "section": section,
#                 "decision": "REJECT",
#                 "confidence": 0.0,
#                 "reason": "The verifier failed to return a result for this candidate after retry.",
#                 "missing_ingredients": [],
#                 "verification_error": True
#             }

#         results.append(
#             result
#         )

#     return results


# # ============================================================
# # SINGLE CANDIDATE COMPATIBILITY
# # ============================================================

# def verify_candidate(
#     candidate,
#     facts,
#     question=""
# ):

#     section = candidate.get(
#         "section",
#         candidate.get(
#             "section_number"
#         )
#     )

#     candidate_text = candidate.get(
#         "text",
#         candidate.get(
#             "content",
#             candidate.get(
#                 "statutory_text",
#                 ""
#             )
#         )
#     )

#     deterministic = deterministic_result(
#         section,
#         facts,
#         candidate_text,
#         question,
#         {int(section)}
#         if str(section).isdigit()
#         else set()
#     )

#     if deterministic is not None:

#         if deterministic.get(
#             "decision"
#         ) == "APPLICABLE":

#             return deterministic

#         return normalize_result(
#             deterministic,
#             section
#         )

#     results = verify_batch(
#         [candidate],
#         facts,
#         question
#     )

#     if results:
#         return results[0]

#     return {
#         "section": section,
#         "decision": "REJECT",
#         "confidence": 0.0,
#         "reason": "No verification result.",
#         "missing_ingredients": [],
#         "verification_error": True
#     }


# # ============================================================
# # VERIFY ALL CANDIDATES
# # ============================================================

# def verify_candidates(
#     candidates,
#     facts,
#     question=""
# ):

#     start = time.time()

#     print(
#         "[VERIFIER] ========================================"
#     )

#     print(
#         f"[VERIFIER] Candidates received: "
#         f"{len(candidates)}"
#     )

#     # --------------------------------------------------------
#     # Determine all retrieved sections first.
#     #
#     # This lets deterministic rules perform limited
#     # comparative reasoning, such as Section 131 vs 134.
#     # --------------------------------------------------------

#     available_sections = set()

#     for candidate in candidates:

#         section = candidate.get(
#             "section",
#             candidate.get(
#                 "section_number"
#             )
#         )

#         try:

#             available_sections.add(
#                 int(section)
#             )

#         except Exception:
#             pass

#     deterministic_results = []
#     qwen_candidates = []

#     # --------------------------------------------------------
#     # Deterministic filtering
#     # --------------------------------------------------------

#     for candidate in candidates:

#         section = candidate.get(
#             "section",
#             candidate.get(
#                 "section_number"
#             )
#         )

#         candidate_text = candidate.get(
#             "text",
#             candidate.get(
#                 "content",
#                 candidate.get(
#                     "statutory_text",
#                     ""
#                 )
#             )
#         )

#         deterministic = deterministic_result(
#             section,
#             facts,
#             candidate_text,
#             question,
#             available_sections
#         )

#         if deterministic is not None:

#             deterministic_results.append(
#                 normalize_result(
#                     deterministic,
#                     section
#                 )
#             )

#         else:

#             qwen_candidates.append(
#                 candidate
#             )

#     print(
#         f"[VERIFIER] Deterministic results: "
#         f"{len(deterministic_results)}"
#     )

#     print(
#         f"[VERIFIER] Remaining for Qwen: "
#         f"{len(qwen_candidates)}"
#     )

#     # --------------------------------------------------------
#     # Batch Qwen verification
#     # --------------------------------------------------------

#     qwen_results = []

#     batches = [
#         qwen_candidates[
#             i:i + BATCH_SIZE
#         ]
#         for i in range(
#             0,
#             len(qwen_candidates),
#             BATCH_SIZE
#         )
#     ]

#     for index, batch in enumerate(
#         batches,
#         start=1
#     ):

#         print(
#             f"[VERIFIER] Qwen batch {index}: "
#             f"{len(batch)} candidates"
#         )

#         batch_results = verify_batch(
#             batch,
#             facts,
#             question,
#             retry_missing=True
#         )

#         qwen_results.extend(
#             batch_results
#         )

#     # --------------------------------------------------------
#     # Combine
#     # --------------------------------------------------------

#     all_results = (
#         deterministic_results
#         + qwen_results
#     )

#     # --------------------------------------------------------
#     # Remove duplicates by section
#     # --------------------------------------------------------

#     unique = {}

#     for result in all_results:

#         section = result.get(
#             "section"
#         )

#         if section is None:
#             continue

#         if section not in unique:

#             unique[
#                 section
#             ] = result

#             continue

#         existing = unique[
#             section
#         ]

#         # Deterministic result should win.
#         if existing.get(
#             "decision"
#         ) == "REJECT":

#             if result.get(
#                 "decision"
#             ) != "REJECT":

#                 unique[
#                     section
#                 ] = result

#     final_results = list(
#         unique.values()
#     )

#     # --------------------------------------------------------
#     # Sort according to original candidate order
#     # --------------------------------------------------------

#     candidate_order = {}

#     for index, candidate in enumerate(
#         candidates
#     ):

#         section = candidate.get(
#             "section",
#             candidate.get(
#                 "section_number"
#             )
#         )

#         try:

#             section = int(
#                 section
#             )

#         except Exception:

#             continue

#         candidate_order[
#             section
#         ] = index

#     final_results.sort(
#         key=lambda x:
#             candidate_order.get(
#                 x.get("section"),
#                 999999
#             )
#     )

#     # --------------------------------------------------------
#     # Statistics
#     # --------------------------------------------------------

#     applicable = sum(
#         1
#         for r in final_results
#         if r.get(
#             "decision"
#         ) == "APPLICABLE"
#     )

#     possible = sum(
#         1
#         for r in final_results
#         if r.get(
#             "decision"
#         ) == "POSSIBLE"
#     )

#     rejected = sum(
#         1
#         for r in final_results
#         if r.get(
#             "decision"
#         ) == "REJECT"
#     )

#     verification_errors = sum(
#         1
#         for r in final_results
#         if r.get(
#             "verification_error"
#         )
#     )

#     elapsed = time.time() - start

#     print("")
#     print(
#         "[VERIFIER] RESULTS"
#     )

#     print(
#         f"[VERIFIER] Applicable: "
#         f"{applicable}"
#     )

#     print(
#         f"[VERIFIER] Possible: "
#         f"{possible}"
#     )

#     print(
#         f"[VERIFIER] Rejected: "
#         f"{rejected}"
#     )

#     print(
#         f"[VERIFIER] Verification errors: "
#         f"{verification_errors}"
#     )

#     print(
#         f"[VERIFIER] Qwen batches: "
#         f"{len(batches)}"
#     )

#     print(
#         f"[VERIFIER] Verification time: "
#         f"{elapsed:.2f} sec"
#     )

#     print(
#         "[VERIFIER] ========================================"
#     )

#     return final_results


# # ============================================================
# # GET APPLICABLE SECTIONS
# # ============================================================

# def get_applicable_sections(
#     verified_results
# ):

#     return [
#         result
#         for result in verified_results
#         if result.get(
#             "decision"
#         ) == "APPLICABLE"
#     ]
