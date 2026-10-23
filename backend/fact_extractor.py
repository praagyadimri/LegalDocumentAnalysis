# # fact_extractor.py
# import json
# import re
# import requests


# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL_NAME = "qwen3:8b"


# FACT_FIELDS = [
#     "question_type",
#     "persons",
#     "actions",
#     "injuries",
#     "deaths",
#     "weapons",
#     "threats",
#     "property",
#     "intent_facts",
#     "knowledge_facts",
#     "public_servant_facts",
#     "orders_or_directions",
#     "public_place_facts",
#     "group_or_assembly_facts",
#     "relationship_facts",
#     "previous_conviction_facts",
#     "reputation_facts",
#     "publication_facts",
#     "obstruction_facts",
#     "caste_or_community_facts",
#     "other_facts"
# ]


# def empty_facts():
#     return {
#         "question_type": "UNKNOWN",
#         "persons": [],
#         "actions": [],
#         "injuries": [],
#         "deaths": [],
#         "weapons": [],
#         "threats": [],
#         "property": [],
#         "intent_facts": [],
#         "knowledge_facts": [],
#         "public_servant_facts": [],
#         "orders_or_directions": [],
#         "public_place_facts": [],
#         "group_or_assembly_facts": [],
#         "relationship_facts": [],
#         "previous_conviction_facts": [],
#         "reputation_facts": [],
#         "publication_facts": [],
#         "obstruction_facts": [],
#         "caste_or_community_facts": [],
#         "other_facts": []
#     }


# def ask_qwen(prompt, num_predict=900):

#     print(
#         "[FACT EXTRACTION] Prompt characters:",
#         len(prompt)
#     )

#     print(
#         "[FACT EXTRACTION] Approx tokens:",
#         len(prompt) // 4
#     )

#     response = requests.post(
#         OLLAMA_URL,
#         json={
#             "model": MODEL_NAME,
#             "prompt": prompt,
#             "stream": False,
#             "think": False,
#             "options": {
#                 "temperature": 0.0,
#                 "num_predict": num_predict
#             }
#         },
#         timeout=180
#     )

#     if response.status_code != 200:
#         raise Exception(
#             f"Ollama error {response.status_code}: "
#             f"{response.text}"
#         )

#     data = response.json()

#     return data.get(
#         "response",
#         ""
#     )


# def extract_json(text):

#     if not text:
#         return None

#     text = text.strip()

#     # Direct JSON
#     try:
#         return json.loads(text)
#     except Exception:
#         pass

#     # Remove markdown code fences
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

#     text = text.strip()

#     try:
#         return json.loads(text)
#     except Exception:
#         pass

#     # Find first JSON object
#     start = text.find("{")

#     if start == -1:
#         return None

#     depth = 0
#     in_string = False
#     escaped = False

#     for index in range(
#         start,
#         len(text)
#     ):

#         char = text[index]

#         if escaped:
#             escaped = False
#             continue

#         if char == "\\":
#             escaped = True
#             continue

#         if char == '"':
#             in_string = not in_string
#             continue

#         if in_string:
#             continue

#         if char == "{":
#             depth += 1

#         elif char == "}":
#             depth -= 1

#             if depth == 0:

#                 candidate = text[
#                     start:index + 1
#                 ]

#                 try:
#                     return json.loads(
#                         candidate
#                     )
#                 except Exception:
#                     return None

#     return None


# def normalize_facts(data):

#     result = empty_facts()

#     if not isinstance(
#         data,
#         dict
#     ):
#         return result

#     question_type = data.get(
#         "question_type"
#     )

#     if isinstance(
#         question_type,
#         str
#     ):
#         result["question_type"] = (
#             question_type.strip()
#             or "UNKNOWN"
#         )

#     for field in FACT_FIELDS:

#         if field == "question_type":
#             continue

#         value = data.get(
#             field,
#             []
#         )

#         if isinstance(
#             value,
#             str
#         ):

#             value = [value]

#         if not isinstance(
#             value,
#             list
#         ):
#             value = []

#         cleaned = []

#         for item in value:

#             if item is None:
#                 continue

#             item = str(item).strip()

#             if not item:
#                 continue

#             if item not in cleaned:
#                 cleaned.append(item)

#         result[field] = cleaned

#     return result


# def extract_facts_from_text(
#     text,
#     chunk_number=None,
#     total_chunks=None
# ):

#     if not text:
#         return empty_facts()

#     if chunk_number is None:
#         chunk_label = "the provided text"

#     else:
#         chunk_label = (
#             f"part {chunk_number} of "
#             f"{total_chunks}"
#         )

#     prompt = f"""
# You are a strict legal fact extraction system.

# Extract ONLY facts explicitly stated in {chunk_label}.

# TEXT:

# {text}

# Return ONLY valid JSON.

# Required JSON structure:

# {{
#   "question_type": "CASE_ANALYSIS",
#   "persons": [],
#   "actions": [],
#   "injuries": [],
#   "deaths": [],
#   "weapons": [],
#   "threats": [],
#   "property": [],
#   "intent_facts": [],
#   "knowledge_facts": [],
#   "public_servant_facts": [],
#   "orders_or_directions": [],
#   "public_place_facts": [],
#   "group_or_assembly_facts": [],
#   "relationship_facts": [],
#   "previous_conviction_facts": [],
#   "reputation_facts": [],
#   "publication_facts": [],
#   "obstruction_facts": [],
#   "caste_or_community_facts": [],
#   "other_facts": []
# }}

# STRICT RULES:

# 1. Extract only information explicitly present.

# 2. Do NOT infer facts.

# 3. Do NOT infer intention merely because an action looks intentional.

# 4. Do NOT infer knowledge unless knowledge is explicitly stated.

# 5. Do NOT infer public-servant status.

# 6. Do NOT infer caste, religion or community identity.

# 7. Do NOT infer robbery, theft, entrustment, cheating,
#    trespass, conspiracy or any other legal ingredient.

# 8. If a person is merely accused of something, preserve that
#    as an allegation rather than treating it as an established fact.

# 9. Put explicit instructions, commands or directions in
#    orders_or_directions.

# 10. Put explicit statements about intention or purpose only
#     in intent_facts.

# 11. Put explicit statements about awareness or knowledge only
#     in knowledge_facts.

# 12. If the text says that an event caused death, record the
#     death in deaths.

# 13. Preserve important names and relationships.

# 14. Do not add BNS section numbers.

# 15. Do not provide legal conclusions.

# 16. Every item must be short and factual.

# 17. If a field has no explicit information, return [].

# Return JSON only.
# """

#     try:

#         raw = ask_qwen(
#             prompt,
#             num_predict=900
#         )

#         parsed = extract_json(
#             raw
#         )

#         return normalize_facts(
#             parsed
#         )

#     except Exception as error:

#         print(
#             f"[FACT EXTRACTION] "
#             f"Chunk failed: {error}"
#         )

#         return empty_facts()


# def split_text_for_fact_extraction(
#     text,
#     chunk_size=6000,
#     overlap=500
# ):

#     if not text:
#         return []

#     text = text.strip()

#     if len(text) <= chunk_size:
#         return [text]

#     chunks = []

#     start = 0
#     text_length = len(text)

#     while start < text_length:

#         end = min(
#             start + chunk_size,
#             text_length
#         )

#         chunk = text[
#             start:end
#         ].strip()

#         if chunk:
#             chunks.append(
#                 chunk
#             )

#         if end >= text_length:
#             break

#         start = max(
#             end - overlap,
#             start + 1
#         )

#     return chunks


# def merge_facts(
#     fact_sets
# ):

#     merged = empty_facts()

#     for facts in fact_sets:

#         if not isinstance(
#             facts,
#             dict
#         ):
#             continue

#         question_type = facts.get(
#             "question_type",
#             "UNKNOWN"
#         )

#         if (
#             merged["question_type"]
#             == "UNKNOWN"
#             and question_type
#             != "UNKNOWN"
#         ):
#             merged["question_type"] = (
#                 question_type
#             )

#         for field in FACT_FIELDS:

#             if field == "question_type":
#                 continue

#             values = facts.get(
#                 field,
#                 []
#             )

#             if isinstance(
#                 values,
#                 str
#             ):
#                 values = [values]

#             if not isinstance(
#                 values,
#                 list
#             ):
#                 continue

#             for value in values:

#                 value = str(
#                     value
#                 ).strip()

#                 if not value:
#                     continue

#                 if value not in merged[field]:
#                     merged[field].append(
#                         value
#                     )

#     return merged


# def extract_facts(
#     question,
#     document_text=""
# ):

#     question = (
#         question or ""
#     ).strip()

#     document_text = (
#         document_text or ""
#     ).strip()

#     combined = ""

#     if question:
#         combined += (
#             "USER QUESTION:\n"
#             + question
#         )

#     if document_text:

#         if combined:
#             combined += "\n\n"

#         combined += (
#             "DOCUMENT TEXT:\n"
#             + document_text
#         )

#     if not combined:
#         return empty_facts()

#     chunks = split_text_for_fact_extraction(
#         combined
#     )

#     print(
#         "\n[FACT EXTRACTION] "
#         f"Total chunks: {len(chunks)}"
#     )

#     all_facts = []

#     for index, chunk in enumerate(
#         chunks,
#         start=1
#     ):

#         print(
#             f"[FACT EXTRACTION] "
#             f"Processing chunk {index}/{len(chunks)}"
#         )

#         facts = extract_facts_from_text(
#             chunk,
#             index,
#             len(chunks)
#         )

#         all_facts.append(
#             facts
#         )

#     merged = merge_facts(
#         all_facts
#     )

#     print(
#         "[FACT EXTRACTION] "
#         "Merged fact extraction completed."
#     )

#     return merged


# def facts_to_text(
#     facts
# ):

#     if not isinstance(
#         facts,
#         dict
#     ):
#         return ""

#     lines = []

#     for field in FACT_FIELDS:

#         if field == "question_type":
#             value = facts.get(
#                 field,
#                 "UNKNOWN"
#             )

#             if value:
#                 lines.append(
#                     f"Question type: {value}"
#                 )

#             continue

#         values = facts.get(
#             field,
#             []
#         )

#         if not values:
#             continue

#         if isinstance(
#             values,
#             str
#         ):
#             values = [values]

#         lines.append(
#             f"{field}: "
#             + "; ".join(
#                 str(value)
#                 for value in values
#             )
#         )

#     return "\n".join(
#         lines
#     )




import json
import re
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b"


FACT_FIELDS = [
    "question_type",
    "persons",
    "actions",
    "injuries",
    "deaths",
    "weapons",
    "threats",
    "property",
    "intent_facts",
    "knowledge_facts",
    "public_servant_facts",
    "orders_or_directions",
    "public_place_facts",
    "group_or_assembly_facts",
    "relationship_facts",
    "previous_conviction_facts",
    "reputation_facts",
    "publication_facts",
    "obstruction_facts",
    "caste_or_community_facts",
    "other_facts"
]


def empty_facts():

    return {
        "question_type": "UNKNOWN",
        "persons": [],
        "actions": [],
        "injuries": [],
        "deaths": [],
        "weapons": [],
        "threats": [],
        "property": [],
        "intent_facts": [],
        "knowledge_facts": [],
        "public_servant_facts": [],
        "orders_or_directions": [],
        "public_place_facts": [],
        "group_or_assembly_facts": [],
        "relationship_facts": [],
        "previous_conviction_facts": [],
        "reputation_facts": [],
        "publication_facts": [],
        "obstruction_facts": [],
        "caste_or_community_facts": [],
        "other_facts": []
    }


def ask_qwen(
    prompt,
    num_predict=550
):

    print(
        "[FACT EXTRACTION] Prompt characters:",
        len(prompt)
    )

    print(
        "[FACT EXTRACTION] Approx tokens:",
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


def extract_json(text):

    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    text = re.sub(
        r"```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```\s*",
        "",
        text
    )

    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")

    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(
        start,
        len(text)
    ):

        char = text[index]

        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":

            depth += 1

        elif char == "}":

            depth -= 1

            if depth == 0:

                candidate = text[
                    start:index + 1
                ]

                try:
                    return json.loads(
                        candidate
                    )
                except Exception:
                    return None

    return None


def normalize_facts(data):

    result = empty_facts()

    if not isinstance(
        data,
        dict
    ):
        return result

    question_type = data.get(
        "question_type"
    )

    if isinstance(
        question_type,
        str
    ):

        result["question_type"] = (
            question_type.strip()
            or "UNKNOWN"
        )

    for field in FACT_FIELDS:

        if field == "question_type":
            continue

        value = data.get(
            field,
            []
        )

        if isinstance(
            value,
            str
        ):
            value = [value]

        if not isinstance(
            value,
            list
        ):
            value = []

        cleaned = []

        for item in value:

            if item is None:
                continue

            item = str(
                item
            ).strip()

            if not item:
                continue

            if item not in cleaned:

                cleaned.append(
                    item
                )

        result[field] = cleaned

    return result


def extract_facts_from_text(
    text,
    chunk_number=None,
    total_chunks=None
):

    if not text:
        return empty_facts()

    if chunk_number is None:

        chunk_label = "the provided text"

    else:

        chunk_label = (
            f"part {chunk_number} "
            f"of {total_chunks}"
        )

    prompt = f"""
You are a strict legal fact extraction system.

Extract ONLY facts explicitly stated in {chunk_label}.

TEXT:

{text}

Return ONLY valid JSON using exactly this structure:

{{
 "question_type": "CASE_ANALYSIS",
 "persons": [],
 "actions": [],
 "injuries": [],
 "deaths": [],
 "weapons": [],
 "threats": [],
 "property": [],
 "intent_facts": [],
 "knowledge_facts": [],
 "public_servant_facts": [],
 "orders_or_directions": [],
 "public_place_facts": [],
 "group_or_assembly_facts": [],
 "relationship_facts": [],
 "previous_conviction_facts": [],
 "reputation_facts": [],
 "publication_facts": [],
 "obstruction_facts": [],
 "caste_or_community_facts": [],
 "other_facts": []
}}

STRICT RULES:

1. Extract only information explicitly present.

2. Do NOT infer facts.

3. Do NOT infer intention merely because an action appears intentional.

4. Do NOT infer knowledge unless explicitly stated.

5. Do NOT infer public-servant status.

6. Do NOT infer caste, religion or community identity.

7. Do NOT infer robbery, theft, entrustment, cheating,
trespass, conspiracy or any other legal ingredient.

8. Preserve allegations as allegations.

9. Put explicit instructions or commands in
orders_or_directions.

10. Put explicit intention or purpose in intent_facts.

11. Put explicit awareness or knowledge in knowledge_facts.

12. If the text explicitly says an event caused death,
record that in deaths.

13. Preserve important persons and relationships.

14. Do not add BNS section numbers.

15. Do not provide legal conclusions.

16. Keep every item short and factual.

17. Empty fields must be [].

Return JSON only.
"""

    try:

        raw = ask_qwen(
            prompt,
            num_predict=550
        )

        parsed = extract_json(
            raw
        )

        return normalize_facts(
            parsed
        )

    except Exception as error:

        print(
            "[FACT EXTRACTION] "
            f"Chunk failed: {error}"
        )

        return empty_facts()


def split_text_for_fact_extraction(
    text,
    chunk_size=6000,
    overlap=500
):

    if not text:
        return []

    text = text.strip()

    if len(text) <= chunk_size:
        return [text]

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length
        )

        chunk = text[
            start:end
        ].strip()

        if chunk:

            chunks.append(
                chunk
            )

        if end >= text_length:
            break

        start = max(
            end - overlap,
            start + 1
        )

    return chunks


def merge_facts(
    fact_sets
):

    merged = empty_facts()

    for facts in fact_sets:

        if not isinstance(
            facts,
            dict
        ):
            continue

        question_type = facts.get(
            "question_type",
            "UNKNOWN"
        )

        if (
            merged["question_type"]
            == "UNKNOWN"
            and question_type
            != "UNKNOWN"
        ):

            merged["question_type"] = (
                question_type
            )

        for field in FACT_FIELDS:

            if field == "question_type":
                continue

            values = facts.get(
                field,
                []
            )

            if isinstance(
                values,
                str
            ):
                values = [values]

            if not isinstance(
                values,
                list
            ):
                continue

            for value in values:

                value = str(
                    value
                ).strip()

                if not value:
                    continue

                if value not in merged[field]:

                    merged[field].append(
                        value
                    )

    return merged


def extract_facts(
    question,
    document_text=""
):

    question = (
        question or ""
    ).strip()

    document_text = (
        document_text or ""
    ).strip()

    combined_parts = []

    if question:

        combined_parts.append(
            "USER QUESTION:\n"
            + question
        )

    if document_text:

        combined_parts.append(
            "DOCUMENT TEXT:\n"
            + document_text
        )

    if not combined_parts:

        return empty_facts()

    combined = "\n\n".join(
        combined_parts
    )

    chunks = split_text_for_fact_extraction(
        combined
    )

    print(
        "\n[FACT EXTRACTION] "
        f"Total chunks: {len(chunks)}"
    )

    all_facts = []

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        print(
            "[FACT EXTRACTION] "
            f"Processing chunk "
            f"{index}/{len(chunks)}"
        )

        facts = extract_facts_from_text(
            chunk,
            index,
            len(chunks)
        )

        all_facts.append(
            facts
        )

    merged = merge_facts(
        all_facts
    )

    print(
        "[FACT EXTRACTION] "
        "Merged fact extraction completed."
    )

    return merged


def facts_to_text(
    facts
):

    if not isinstance(
        facts,
        dict
    ):
        return ""

    lines = []

    for field in FACT_FIELDS:

        if field == "question_type":

            value = facts.get(
                field,
                "UNKNOWN"
            )

            if value:

                lines.append(
                    f"Question type: {value}"
                )

            continue

        values = facts.get(
            field,
            []
        )

        if not values:
            continue

        if isinstance(
            values,
            str
        ):
            values = [values]

        lines.append(
            f"{field}: "
            + "; ".join(
                str(value)
                for value in values
            )
        )

    return "\n".join(
        lines
    )