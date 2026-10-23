# # analyzer.py
# import io
# import requests

# from pypdf import PdfReader

# from backend.rag import search

# from backend.fact_extractor import (
#     extract_facts,
#     facts_to_text
# )

# from backend.section_verifier import (
#     verify_candidates
# )

# from backend.output_validator import (
#     validate_output
# )

# from backend.section_rules import (
#     apply_section_rules
# )


# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL_NAME = "qwen3:8b"


# # =========================================================
# # QWEN
# # =========================================================

# def ask_qwen(
#     prompt,
#     num_predict=900
# ):

#     print(
#         "Prompt characters:",
#         len(prompt)
#     )

#     print(
#         "Approx tokens:",
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

#     return response.json().get(
#         "response",
#         ""
#     )


# # =========================================================
# # STRUCTURED FACTS → TEXT
# # =========================================================

# def structured_facts_to_text(facts):
#     """
#     Convert either the normal fact-extractor schema or the
#     Gemini BNS-adapter schema into readable text.

#     This is used only for retrieval/concept generation.

#     The original structured facts themselves are passed
#     unchanged to the verifier and section rules.
#     """

#     if not isinstance(facts, dict):
#         return ""

#     sections = [
#         "persons",
#         "actions",
#         "injuries",
#         "deaths",
#         "weapons",
#         "threats",
#         "property",
#         "intent_facts",
#         "knowledge_facts",
#         "other_facts",
#         "orders_or_directions",
#         "group_or_assembly_facts"
#     ]

#     lines = []

#     for section in sections:

#         values = facts.get(
#             section,
#             []
#         )

#         if not isinstance(
#             values,
#             list
#         ):
#             continue

#         for item in values:

#             if isinstance(
#                 item,
#                 dict
#             ):

#                 fact = (
#                     item.get("fact", "")
#                     or item.get("text", "")
#                 )

#                 if fact:
#                     lines.append(
#                         f"{section}: {fact}"
#                     )

#             elif isinstance(
#                 item,
#                 str
#             ):

#                 item = item.strip()

#                 if item:
#                     lines.append(
#                         f"{section}: {item}"
#                     )

#     return "\n".join(
#         lines
#     )


# # =========================================================
# # DOCUMENT SUMMARIZATION
# # =========================================================

# def summarize_document_chunk(
#     chunk,
#     chunk_number,
#     total_chunks
# ):

#     prompt = f"""
# You are analyzing part {chunk_number} of {total_chunks}
# of a legal document.

# DOCUMENT EXCERPT:

# {chunk}

# Summarize ONLY information explicitly present in this excerpt.

# Focus on:

# - case names
# - parties
# - facts
# - legal issues
# - arguments
# - legal provisions
# - court reasoning
# - decisions
# - important findings

# Rules:

# - Do not invent information.
# - Do not assume the document is a judgment.
# - Do not expand acronyms unless the excerpt defines them.
# - Do not add information from general knowledge.
# - Preserve important names, dates, courts, sections and decisions.
# - If the excerpt contains little useful information, say so briefly.

# Give a concise summary.
# """

#     return ask_qwen(
#         prompt,
#         num_predict=500
#     )


# # =========================================================
# # LEGAL CONCEPT GENERATION
# # =========================================================

# def generate_legal_concepts(
#     question,
#     facts
# ):

#     facts_text = structured_facts_to_text(
#         facts
#     )

#     prompt = f"""
# You are generating legal retrieval concepts for an Indian
# Bharatiya Nyaya Sanhita (BNS) analysis system.

# The purpose is ONLY to improve retrieval from a BNS section
# database.

# USER INPUT:

# {question}

# EXPLICIT FACTS:

# {facts_text}

# Generate a short list of legal concepts that are directly
# supported by the explicit facts.

# IMPORTANT:

# - Do NOT output BNS section numbers.
# - Do NOT choose the final legal sections.
# - Do NOT invent facts.
# - Do NOT introduce legal ingredients that are absent.
# - Concepts may be legal phrases such as:
#   "causing death by knife attack"
#   "murder / intentional killing"
#   "instruction to kill"
#   "armed group acting together"
#   "dishonest taking of movable property"
#   "publication affecting reputation"
# - Only generate concepts supported by the facts.
# - Prefer 3 to 8 concepts.
# - Avoid generic concepts such as "crime", "violence" or "illegal act".

# Return ONLY a JSON array of strings.

# Example:

# [
#   "causing death by repeated knife blows",
#   "instruction to kill",
#   "armed group acting together"
# ]
# """

#     try:

#         raw = ask_qwen(
#             prompt,
#             num_predict=450
#         )

#         import json
#         import re

#         match = re.search(
#             r"\[[\s\S]*\]",
#             raw
#         )

#         if not match:
#             return []

#         data = json.loads(
#             match.group(0)
#         )

#         if not isinstance(
#             data,
#             list
#         ):
#             return []

#         concepts = []

#         for item in data:

#             if not isinstance(
#                 item,
#                 str
#             ):
#                 continue

#             item = item.strip()

#             if (
#                 item
#                 and item not in concepts
#             ):
#                 concepts.append(
#                     item
#                 )

#         return concepts[:8]

#     except Exception as error:

#         print(
#             f"[LEGAL CONCEPTS] Failed: {error}"
#         )

#         return []


# def deterministic_legal_concepts(
#     facts,
#     raw_text=""
# ):

#     concepts = []

#     deaths = facts.get(
#         "deaths",
#         []
#     )

#     weapons = facts.get(
#         "weapons",
#         []
#     )

#     actions = facts.get(
#         "actions",
#         []
#     )

#     orders = facts.get(
#         "orders_or_directions",
#         []
#     )

#     groups = facts.get(
#         "group_or_assembly_facts",
#         []
#     )

#     combined_parts = []

#     for field in [
#         deaths,
#         weapons,
#         actions,
#         orders,
#         groups
#     ]:

#         for item in field:

#             if isinstance(
#                 item,
#                 dict
#             ):

#                 combined_parts.append(
#                     str(
#                         item.get(
#                             "fact",
#                             ""
#                         )
#                     ).lower()
#                 )

#             else:

#                 combined_parts.append(
#                     str(item).lower()
#                 )

#     combined = " ".join(
#         combined_parts
#     )

#     # Raw input is used only as a fallback for routing when
#     # fact extraction fails or misses an important phrase.
#     raw_lower = (
#         raw_text or ""
#     ).lower()

#     routing_text = (
#         combined
#         + " "
#         + raw_lower
#     )

#     has_death = bool(
#         deaths
#     ) or any(
#         phrase in raw_lower
#         for phrase in [
#             "causing his death",
#             "causing her death",
#             "causing their death",
#             "resulting in his death",
#             "resulting in her death",
#             "resulting in death",
#             "died",
#             "was killed",
#             "were killed",
#             "death"
#         ]
#     )

#     has_weapon = bool(
#         weapons
#     ) or any(
#         word in routing_text
#         for word in [
#             "knife",
#             "sword",
#             "firearm",
#             "gun",
#             "pistol",
#             "weapon",
#             "stab",
#             "stabbing",
#             "stabbed",
#             "shot",
#             "shooting",
#             "struck",
#             "blow"
#         ]
#     )

#     # -----------------------------------------------------
#     # DEATH
#     # -----------------------------------------------------

#     if has_death:

#         concepts.append(
#             "causing death"
#         )

#     # -----------------------------------------------------
#     # WEAPON + DEATH
#     # -----------------------------------------------------

#     if has_weapon:

#         concepts.append(
#             "causing injury or death with a weapon"
#         )

#     if has_weapon and has_death:

#         concepts.append(
#             "causing death by weapon attack"
#         )

#     # -----------------------------------------------------
#     # MURDER / INTENTIONAL KILLING
#     # -----------------------------------------------------

#     if has_death and any(
#         phrase in routing_text
#         for phrase in [
#             "kill",
#             "killing",
#             "murder",
#             "murdered",
#             "intended to kill",
#             "instruction to kill",
#             "ordered to kill"
#         ]
#     ):

#         concepts.append(
#             "murder / intentional killing"
#         )

#     # A completed lethal weapon attack is also a strong
#     # retrieval signal for murder provisions.
#     if has_death and has_weapon:

#         concepts.append(
#             "completed lethal attack causing death"
#         )

#     # -----------------------------------------------------
#     # INSTRUCTION TO KILL
#     # -----------------------------------------------------

#     if (
#         orders
#         and any(
#             word in " ".join(
#                 str(
#                     x.get(
#                         "fact",
#                         ""
#                     )
#                 )
#                 if isinstance(x, dict)
#                 else str(x)
#                 for x in orders
#             )
#             for word in [
#                 "kill",
#                 "murder"
#             ]
#         )
#     ):

#         concepts.append(
#             "instruction or command to kill"
#         )

#     elif any(
#         phrase in routing_text
#         for phrase in [
#             "instructed the group to kill",
#             "ordered the group to kill",
#             "told them to kill",
#             "ordered him to kill",
#             "ordered her to kill",
#             "instructed him to kill",
#             "instructed her to kill"
#         ]
#     ):

#         concepts.append(
#             "instruction or command to kill"
#         )

#     # -----------------------------------------------------
#     # GROUP
#     # -----------------------------------------------------

#     if groups:

#         concepts.append(
#             "group acting together"
#         )

#     return concepts


# # =========================================================
# # BNS RETRIEVAL
# # =========================================================

# def build_bns_candidates(
#     question,
#     facts=None,
#     legal_concepts=None
# ):

#     facts = facts or {}
#     legal_concepts = legal_concepts or []

#     query_parts = []

#     if question:
#         query_parts.append(
#             question
#         )

#     if facts:

#         fact_text = structured_facts_to_text(
#             facts
#         )

#         if fact_text:
#             query_parts.append(
#                 fact_text
#             )

#     if legal_concepts:

#         query_parts.append(
#             "\n".join(
#                 legal_concepts
#             )
#         )

#     retrieval_query = "\n".join(
#         query_parts
#     )

#     candidates = []

#     # -----------------------------------------------------
#     # BASE SEARCH
#     # -----------------------------------------------------

#     try:

#         base_candidates = search(
#             retrieval_query,
#             20
#         )

#         if base_candidates:
#             candidates.extend(
#                 base_candidates
#             )

#     except Exception as error:

#         print(
#             f"[RAG] Base retrieval failed: {error}"
#         )

#     # -----------------------------------------------------
#     # TARGETED LEGAL CONCEPT SEARCH
#     # -----------------------------------------------------

#     query_lower = (
#         retrieval_query.lower()
#     )

#     legal_queries = []

#     # -----------------------------------------------------
#     # MURDER ROUTING
#     # -----------------------------------------------------

#     death_indicators = [
#         "death",
#         "died",
#         "dead",
#         "killed",
#         "murdered",
#         "causing his death",
#         "causing her death",
#         "resulting in his death",
#         "resulting in her death",
#         "resulting in death"
#     ]

#     lethal_indicators = [
#         "knife",
#         "stab",
#         "stabbing",
#         "stabbed",
#         "gun",
#         "firearm",
#         "pistol",
#         "shoot",
#         "shot",
#         "sword",
#         "weapon",
#         "repeatedly struck",
#         "repeated blows",
#         "hit on the head",
#         "struck on the head",
#         "blow"
#     ]

#     has_death = any(
#         phrase in query_lower
#         for phrase in death_indicators
#     )

#     has_lethal_conduct = any(
#         phrase in query_lower
#         for phrase in lethal_indicators
#     )

#     has_kill_language = any(
#         phrase in query_lower
#         for phrase in [
#             "kill",
#             "killing",
#             "murder",
#             "murdered",
#             "intended to kill",
#             "instructed to kill",
#             "ordered to kill"
#         ]
#     )

#     if has_death and (
#         has_lethal_conduct
#         or has_kill_language
#     ):

#         legal_queries.extend([
#             "BNS Section 101 murder",
#             "Section 101 murder causing death",
#             "BNS Section 101 definition murder",
#             "BNS Section 103 punishment for murder",
#             "Section 103 punishment murder"
#         ])

#     elif has_death:

#         legal_queries.extend([
#             "BNS causing death homicide",
#             "BNS punishment for causing death"
#         ])

#     # -----------------------------------------------------
#     # ORDER / ABETMENT ROUTING
#     # -----------------------------------------------------

#     if (
#         "kill" in query_lower
#         and any(
#             phrase in query_lower
#             for phrase in [
#                 "instructed",
#                 "ordered",
#                 "instigated",
#                 "commanded",
#                 "told"
#             ]
#         )
#     ):

#         legal_queries.append(
#             "BNS abetment instigation order instruction to commit offence"
#         )

#     # -----------------------------------------------------
#     # GROUP ROUTING
#     # -----------------------------------------------------

#     if facts.get(
#         "group_or_assembly_facts"
#     ):

#         legal_queries.append(
#             "BNS group persons acting together common intention"
#         )

#     # -----------------------------------------------------
#     # EXISTING TARGETED SEARCHES
#     # -----------------------------------------------------

#     if any(
#         phrase in query_lower
#         for phrase in [
#             "stole",
#             "stolen",
#             "steal",
#             "theft",
#             "took the bag",
#             "took property",
#             "secretly took",
#             "carried away",
#             "dishonestly took"
#         ]
#     ):

#         legal_queries.extend([
#             "theft movable property dishonest taking possession consent",
#             "dishonestly takes movable property out of possession theft",
#             "theft property without consent dishonest intention"
#         ])

#     if any(
#         phrase in query_lower
#         for phrase in [
#             "received stolen",
#             "receiving stolen",
#             "retained stolen",
#             "kept stolen property",
#             "knowing it was stolen"
#         ]
#     ):

#         legal_queries.append(
#             "dishonestly receives or retains stolen property knowing or reason to believe stolen"
#         )

#     if any(
#         phrase in query_lower
#         for phrase in [
#             "misappropriated",
#             "misappropriation",
#             "converted property",
#             "dishonestly converted"
#         ]
#     ):

#         legal_queries.append(
#             "dishonest misappropriation movable property"
#         )

#     if any(
#         phrase in query_lower
#         for phrase in [
#             "defamed",
#             "defamation",
#             "tarnishing image",
#             "tarnished image",
#             "reputation",
#             "social media",
#             "false allegation",
#             "published allegations",
#             "lowered reputation"
#         ]
#     ):

#         legal_queries.extend([
#             "defamation imputation reputation publication",
#             "makes or publishes imputation concerning person reputation",
#             "defamatory statement publication reputation"
#         ])

#     if any(
#         phrase in query_lower
#         for phrase in [
#             "caste",
#             "caste-based",
#             "community",
#             "religion",
#             "religious",
#             "enmity",
#             "disharmony"
#         ]
#     ):

#         legal_queries.extend([
#             "promoting enmity between different groups caste religion",
#             "caste community group enmity disharmony",
#             "promoting feelings of enmity hatred ill-will groups"
#         ])

#     if any(
#         phrase in query_lower
#         for phrase in [
#             "intentional insult",
#             "insulted",
#             "insult",
#             "provoke",
#             "provoked",
#             "breach of peace"
#         ]
#     ):

#         legal_queries.append(
#             "intentional insult with intent to provoke breach of public peace"
#         )

#     if any(
#         phrase in query_lower
#         for phrase in [
#             "obstructing government duties",
#             "obstructed government duties",
#             "obstructing government work",
#             "obstructed government work",
#             "public servant",
#             "government officer",
#             "government duty",
#             "obstructed an officer",
#             "prevented government officer"
#         ]
#     ):

#         legal_queries.extend([
#             "obstruct public servant discharge public functions",
#             "voluntarily obstructs public servant public functions",
#             "resisting public servant discharge duty"
#         ])

#     if any(
#         phrase in query_lower
#         for phrase in [
#             "entered house",
#             "entered the house",
#             "entered home",
#             "house without permission",
#             "entered without permission",
#             "trespass",
#             "house breaking",
#             "house-breaking"
#         ]
#     ):

#         legal_queries.extend([
#             "criminal trespass house trespass entry house intent offence",
#             "house trespass dwelling house criminal trespass",
#             "house breaking lurking house trespass specific entry exit method"
#         ])

#     # -----------------------------------------------------
#     # TARGETED SEARCH
#     # -----------------------------------------------------

#     for legal_query in legal_queries:

#         try:

#             extra = search(
#                 legal_query,
#                 8
#             )

#             if extra:
#                 candidates.extend(
#                     extra
#                 )

#         except Exception as error:

#             print(
#                 f"[RAG] Additional search failed: {error}"
#             )

#     # -----------------------------------------------------
#     # DEDUPLICATION
#     # -----------------------------------------------------

#     unique = {}

#     for item in candidates:

#         if not isinstance(
#             item,
#             dict
#         ):
#             continue

#         section = item.get(
#             "section"
#         )

#         try:

#             section = int(
#                 section
#             )

#         except (
#             ValueError,
#             TypeError
#         ):

#             continue

#         if section < 1 or section > 358:
#             continue

#         if section not in unique:

#             unique[section] = item

#         else:

#             old_score = unique[
#                 section
#             ].get(
#                 "score",
#                 0
#             )

#             new_score = item.get(
#                 "score",
#                 0
#             )

#             try:
#                 old_score = float(
#                     old_score
#                 )
#             except Exception:
#                 old_score = 0

#             try:
#                 new_score = float(
#                     new_score
#                 )
#             except Exception:
#                 new_score = 0

#             if new_score > old_score:

#                 unique[
#                     section
#                 ] = item

#     final_candidates = list(
#         unique.values()
#     )

#     final_candidates.sort(
#         key=lambda item: float(
#             item.get(
#                 "score",
#                 0
#             )
#         ),
#         reverse=True
#     )

#     return final_candidates[:40]


# # =========================================================
# # FINAL ANSWER
# # =========================================================

# def generate_final_legal_answer(
#     question,
#     facts,
#     applicable_sections,
#     verified_results
# ):

#     facts_text = structured_facts_to_text(
#         facts
#     )

#     possible = [
#         result
#         for result in verified_results
#         if result.get(
#             "decision"
#         ) == "POSSIBLE"
#     ]

#     allowed_numbers = [
#         int(result["section"])
#         for result in applicable_sections
#     ]

#     if not allowed_numbers:

#         return (
#             "No BNS section can be conclusively identified "
#             "from the provided facts."
#         )

#     allowed_text = ", ".join(
#         str(section)
#         for section in allowed_numbers
#     )

#     applicable_text = ""

#     for result in applicable_sections:

#         applicable_text += f"""
# BNS SECTION {result['section']}
# Title: {result.get('title', '')}
# Section type: {result.get('section_type', 'OTHER')}

# Section text:
# {result.get('section_text', result.get('text', ''))}

# Verification reason:
# {result.get('reason', '')}

# Supported ingredients:
# {result.get('supported_ingredients', [])}

# Inferable ingredients:
# {result.get('inferable_ingredients', [])}

# --------------------------------
# """

#     possible_text = ""

#     for result in possible:

#         possible_text += f"""
# BNS SECTION {result['section']}
# Title: {result.get('title', '')}

# Reason:
# {result.get('reason', '')}

# Missing ingredients:
# {result.get('missing_ingredients', [])}

# --------------------------------
# """

#     prompt = f"""
# You are the final legal answer generator for an Indian
# Bharatiya Nyaya Sanhita (BNS) legal-analysis system.

# Only use the verified information supplied below.

# USER QUESTION:

# {question}

# EXPLICIT FACTS:

# {facts_text}

# AUTHORIZED BNS SECTION NUMBERS:

# {allowed_text}

# CONCLUSIVELY VERIFIED SECTIONS:

# {applicable_text}

# POSSIBLE BUT NOT CONCLUSIVE:

# {possible_text}

# STRICT RULES:

# 1. Mention ONLY authorized BNS section numbers.

# 2. Do not introduce any other section.

# 3. Do not invent facts.

# 4. Do not turn allegations into established facts.

# 5. Do not use general legal knowledge to add sections.

# 6. Do not mention the possible sections as applicable.

# 7. For BNS Section 101, explain the murder definition using
# the supplied facts.

# 8. For BNS Section 103, treat the ordinary punishment
# provision as punishment for murder unless the supplied
# verification explicitly establishes a special subsection.

# 9. Do not invent aggravated circumstances.

# 10. Do not call a completed killing an attempt.

# 11. State punishment only from the supplied section text.

# 12. Keep the answer concise.

# 13. Do not mention RAG, retrieval, verifier, model,
# prompt or system architecture.

# 14. Do NOT treat arrest, police arrival, seizure, fleeing,
# investigation or other procedural events as proof of an
# offence ingredient unless that ingredient is independently
# established by the supplied facts.

# 15. Do NOT say that an arrest confirms guilt or confirms
# the statutory ingredients of an offence.

# 16. Clearly distinguish factual allegations from legal
# conclusions.

# FORMAT:

# BNS Section X — Title

# Why it applies:
# Brief explanation based only on the supplied facts.

# If applicable, state the punishment from the supplied
# statutory text.

# Do not mention unauthorized section numbers.
# """

#     return ask_qwen(
#         prompt,
#         num_predict=900
#     )


# # =========================================================
# # MAIN CASE ANALYSIS
# # =========================================================

# def analyze_case(
#     question,
#     document_text="",
#     pre_extracted_facts=None
# ):

#     print(
#         "\n" + "=" * 70
#     )

#     print(
#         "STEP 1: FACT EXTRACTION"
#     )

#     print(
#         "=" * 70
#     )

#     # -----------------------------------------------------
#     # GEMINI FACTS OR NORMAL QWEN FACT EXTRACTION
#     # -----------------------------------------------------

#     if pre_extracted_facts is not None:

#         print(
#             "Using pre-extracted document facts."
#         )

#         facts = pre_extracted_facts

#     else:

#         facts = extract_facts(
#             question,
#             document_text
#         )

#     print(
#         "\nExtracted facts:"
#     )

#     print(
#         facts
#     )

#     # -----------------------------------------------------
#     # FACT EXTRACTION FALLBACK
#     # -----------------------------------------------------

#     extracted_fact_text = structured_facts_to_text(
#         facts
#     )

#     if not extracted_fact_text.strip():

#         print(
#             "[WARNING] Fact extraction returned no usable facts."
#         )

#         print(
#             "[WARNING] Raw input will be retained for "
#             "deterministic legal routing."
#         )

#     # -----------------------------------------------------
#     # LEGAL CONCEPTS
#     # -----------------------------------------------------

#     print(
#         "\n" + "=" * 70
#     )

#     print(
#         "STEP 1B: LEGAL CONCEPT GENERATION"
#     )

#     print(
#         "=" * 70
#     )

#     llm_concepts = generate_legal_concepts(
#         question,
#         facts
#     )

#     deterministic_concepts = (
#         deterministic_legal_concepts(
#             facts,
#             question
#         )
#     )

#     legal_concepts = []

#     for concept in (
#         deterministic_concepts
#         + llm_concepts
#     ):

#         if (
#             concept
#             and concept not in legal_concepts
#         ):
#             legal_concepts.append(
#                 concept
#             )

#     print(
#         "\nLegal concepts:"
#     )

#     for concept in legal_concepts:

#         print(
#             "-",
#             concept
#         )

#     # -----------------------------------------------------
#     # RETRIEVAL
#     # -----------------------------------------------------

#     print(
#         "\n" + "=" * 70
#     )

#     print(
#         "STEP 2: BNS RETRIEVAL"
#     )

#     print(
#         "=" * 70
#     )

#     candidates = build_bns_candidates(
#         question,
#         facts,
#         legal_concepts
#     )

#     print(
#         "\nRetrieved candidates:"
#     )

#     for candidate in candidates:

#         try:
#             score = float(
#                 candidate.get(
#                     "score",
#                     0
#                 )
#             )
#         except Exception:
#             score = 0

#         print(
#             f"Section {candidate['section']} | "
#             f"{candidate.get('title', '')} | "
#             f"Score: {score:.4f}"
#         )

#     # -----------------------------------------------------
#     # VERIFICATION
#     # -----------------------------------------------------

#     print(
#         "\n" + "=" * 70
#     )

#     print(
#         "STEP 3: SECTION VERIFICATION"
#     )

#     print(
#         "=" * 70
#     )

#     verified_results = verify_candidates(
#         candidates,
#         facts,
#         question
#     )

#     for result in verified_results:

#         print(
#             f"Section {result['section']} "
#             f"→ {result['decision']}"
#         )

#         print(
#             f"Reason: {result.get('reason', '')}"
#         )

#     # -----------------------------------------------------
#     # DETERMINISTIC RULES
#     # -----------------------------------------------------

#     applicable_sections = apply_section_rules(
#         verified_results,
#         facts,
#         question
#     )

#     print(
#         "\n" + "=" * 70
#     )

#     print(
#         "CONCLUSIVELY APPLICABLE SECTIONS"
#     )

#     print(
#         "=" * 70
#     )

#     for result in applicable_sections:

#         print(
#             f"Section {result['section']} - "
#             f"{result.get('title', '')}"
#         )

#     if not applicable_sections:

#         print("None")

#         return (
#             "No BNS section can be conclusively identified "
#             "from the provided facts."
#         )

#     # -----------------------------------------------------
#     # ATTACH SECTION TEXT
#     # -----------------------------------------------------

#     for result in verified_results:

#         matching_candidate = next(
#             (
#                 candidate
#                 for candidate in candidates
#                 if int(candidate["section"])
#                 == int(result["section"])
#             ),
#             None
#         )

#         if matching_candidate:

#             result["section_text"] = (
#                 matching_candidate.get(
#                     "text",
#                     ""
#                 )
#             )

#     # -----------------------------------------------------
#     # FINAL ANSWER
#     # -----------------------------------------------------

#     print(
#         "\n" + "=" * 70
#     )

#     print(
#         "STEP 4: FINAL ANSWER"
#     )

#     print(
#         "=" * 70
#     )

#     answer = generate_final_legal_answer(
#         question,
#         facts,
#         applicable_sections,
#         verified_results
#     )

#     print(
#         "\nGenerated answer:"
#     )

#     print(
#         answer
#     )

#     # -----------------------------------------------------
#     # OUTPUT VALIDATION
#     # -----------------------------------------------------

#     print(
#         "\n" + "=" * 70
#     )

#     print(
#         "STEP 5: OUTPUT VALIDATION"
#     )

#     print(
#         "=" * 70
#     )

#     allowed_sections = [
#         result["section"]
#         for result in applicable_sections
#     ]

#     validation = validate_output(
#         answer,
#         allowed_sections
#     )

#     if validation["valid"]:

#         print(
#             "Output validation: PASSED"
#         )

#         return answer

#     print(
#         "Output validation: FAILED"
#     )

#     print(
#         "Unauthorized sections:",
#         validation["unauthorized_sections"]
#     )

#     allowed_text = ", ".join(
#         str(section)
#         for section in allowed_sections
#     )

#     correction_prompt = f"""
# Rewrite the following answer.

# ONLY these BNS section numbers are authorized:

# {allowed_text}

# Remove every mention of every other BNS section.

# Do not introduce new sections.
# Do not introduce new facts.
# Do not use general legal knowledge.

# Return only the corrected answer.

# ORIGINAL ANSWER:

# {answer}
# """

#     corrected_answer = ask_qwen(
#         correction_prompt,
#         num_predict=700
#     )

#     second_validation = validate_output(
#         corrected_answer,
#         allowed_sections
#     )

#     if second_validation["valid"]:

#         return corrected_answer

#     return (
#         "Based on the provided facts, the conclusively "
#         "identified provision(s) are: "
#         + ", ".join(
#             f"BNS Section {section}"
#             for section in allowed_sections
#         )
#         + ". The available facts should be reviewed "
#           "further before drawing additional legal conclusions."
#     )


# # =========================================================
# # MAIN API FUNCTION
# # =========================================================

# def ask_ai(
#     question,
#     document_text="",
#     filename="",
#     pre_extracted_facts=None
# ):

#     question = (
#         question or ""
#     ).strip()

#     # -----------------------------------------------------
#     # GEMINI DOCUMENT FACTS
#     # -----------------------------------------------------
#     # This branch is used ONLY when the uploaded-document
#     # layer has already analyzed the PDF and produced
#     # structured BNS facts.
#     #
#     # The existing BNS pipeline remains unchanged after
#     # analyze_case() receives these facts.
#     # -----------------------------------------------------

#     if pre_extracted_facts is not None:

#         if not question:

#             question = (
#                 "Analyze the present case under the "
#                 "Bharatiya Nyaya Sanhita based only on "
#                 "the established facts provided."
#             )

#         return analyze_case(
#             question,
#             document_text,
#             pre_extracted_facts=pre_extracted_facts
#         )

#     # -----------------------------------------------------
#     # QUESTION + DOCUMENT
#     # -----------------------------------------------------

#     if document_text and question:

#         from backend.document_rag import (
#             retrieve_document_chunks
#         )

#         document_results = (
#             retrieve_document_chunks(
#                 document_text,
#                 question,
#                 top_k=5
#             )
#         )

#         document_context = ""

#         for result in document_results:

#             document_context += f"""
# {result['text']}

# --------------------
# """

#         combined_text = (
#             f"User question:\n"
#             f"{question}\n\n"
#             f"Relevant document excerpts:\n"
#             f"{document_context}"
#         )

#         return analyze_case(
#             combined_text,
#             document_text
#         )

#     # -----------------------------------------------------
#     # DOCUMENT ONLY
#     # -----------------------------------------------------

#     elif document_text:

#         from backend.document_rag import (
#             get_document_chunks
#         )

#         chunks = get_document_chunks(
#             document_text
#         )

#         chunk_summaries = []

#         for i, chunk in enumerate(
#             chunks,
#             start=1
#         ):

#             summary = summarize_document_chunk(
#                 chunk,
#                 i,
#                 len(chunks)
#             )

#             chunk_summaries.append(
#                 summary
#             )

#         document_context = (
#             "\n\n".join(
#                 chunk_summaries
#             )
#         )

#         prompt = f"""
# You are analyzing a legal document.

# Below are summaries of different parts of the document.

# {document_context}

# Provide a concise overall analysis.

# Cover:

# - parties
# - facts
# - legal issues
# - important legal provisions explicitly mentioned
# - arguments
# - court reasoning, if present
# - decision or outcome, if present
# - important findings

# Rules:

# - Do not invent information.
# - Do not introduce legal sections that are not present
#   in the document summaries.
# - Clearly distinguish facts from legal conclusions.
# - If the document is not a judgment, do not describe it
#   as a judgment.

# Give a structured but concise analysis.
# """

#         return ask_qwen(
#             prompt,
#             num_predict=1200
#         )

#     # -----------------------------------------------------
#     # QUESTION ONLY
#     # -----------------------------------------------------

#     return analyze_case(
#         question
#     )


# # =========================================================
# # PDF EXTRACTION
# # =========================================================

# def extract_pdf_text(
#     file_content
# ):

#     reader = PdfReader(
#         io.BytesIO(
#             file_content
#         )
#     )

#     text = ""

#     for page in reader.pages:

#         page_text = page.extract_text()

#         if page_text:

#             text += (
#                 page_text
#                 + "\n"
#             )

#     text = text.strip()

#     if not text:

#         raise ValueError(
#             "No readable text was found in the PDF."
#         )

#     return text



import io
import json
import re
import requests
import time

from pypdf import PdfReader

from backend.rag import search

from backend.fact_extractor import (
    extract_facts
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


# =========================================================
# QWEN
# =========================================================

def ask_qwen(
    prompt,
    num_predict=700
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

    return response.json().get(
        "response",
        ""
    )


# =========================================================
# STRUCTURED FACTS → TEXT
# =========================================================

def structured_facts_to_text(
    facts
):

    if not isinstance(
        facts,
        dict
    ):
        return ""

    sections = [
        "persons",
        "actions",
        "injuries",
        "deaths",
        "weapons",
        "threats",
        "property",
        "intent_facts",
        "knowledge_facts",
        "other_facts",
        "orders_or_directions",
        "group_or_assembly_facts",
        "public_servant_facts",
        "public_place_facts",
        "relationship_facts",
        "reputation_facts",
        "publication_facts",
        "obstruction_facts",
        "caste_or_community_facts"
    ]

    lines = []

    for section in sections:

        values = facts.get(
            section,
            []
        )

        if not isinstance(
            values,
            list
        ):
            continue

        for item in values:

            if isinstance(
                item,
                dict
            ):

                fact = (
                    item.get("fact", "")
                    or item.get("text", "")
                )

                if fact:

                    lines.append(
                        f"{section}: {fact}"
                    )

            elif isinstance(
                item,
                str
            ):

                item = item.strip()

                if item:

                    lines.append(
                        f"{section}: {item}"
                    )

    return "\n".join(
        lines
    )


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

Summarize ONLY information explicitly present.

Focus on:

- parties
- facts
- legal issues
- legal provisions
- arguments
- court reasoning
- decisions
- important findings

Rules:

- Do not invent information.
- Do not assume the document is a judgment.
- Preserve names, dates, courts, sections and decisions.
- If little useful information is present, say so briefly.

Give a concise summary.
"""

    return ask_qwen(
        prompt,
        num_predict=400
    )


# =========================================================
# LEGAL CONCEPT GENERATION
# =========================================================

def generate_legal_concepts(
    question,
    facts
):

    facts_text = structured_facts_to_text(
        facts
    )

    prompt = f"""
Generate legal retrieval concepts for BNS retrieval.

USER INPUT:

{question}

EXPLICIT FACTS:

{facts_text}

Rules:

- Do not output BNS section numbers.
- Do not make final legal decisions.
- Do not invent facts.
- Only use concepts directly supported by the facts.
- Prefer precise concepts.
- Return 3 to 6 concepts.

Return ONLY a JSON array of strings.
"""

    try:

        raw = ask_qwen(
            prompt,
            num_predict=300
        )

        match = re.search(
            r"\[[\s\S]*\]",
            raw
        )

        if not match:
            return []

        data = json.loads(
            match.group(0)
        )

        if not isinstance(
            data,
            list
        ):
            return []

        concepts = []

        for item in data:

            if not isinstance(
                item,
                str
            ):
                continue

            item = item.strip()

            if (
                item
                and item not in concepts
            ):

                concepts.append(
                    item
                )

        return concepts[:6]

    except Exception as error:

        print(
            f"[LEGAL CONCEPTS] Failed: {error}"
        )

        return []


# =========================================================
# DETERMINISTIC LEGAL CONCEPTS
# =========================================================

def deterministic_legal_concepts(
    facts,
    raw_text=""
):

    concepts = []

    deaths = facts.get(
        "deaths",
        []
    )

    weapons = facts.get(
        "weapons",
        []
    )

    actions = facts.get(
        "actions",
        []
    )

    orders = facts.get(
        "orders_or_directions",
        []
    )

    groups = facts.get(
        "group_or_assembly_facts",
        []
    )

    combined_parts = []

    for field in [
        deaths,
        weapons,
        actions,
        orders,
        groups
    ]:

        for item in field:

            if isinstance(
                item,
                dict
            ):

                combined_parts.append(
                    str(
                        item.get(
                            "fact",
                            ""
                        )
                    ).lower()
                )

            else:

                combined_parts.append(
                    str(item).lower()
                )

    combined = " ".join(
        combined_parts
    )

    raw_lower = (
        raw_text or ""
    ).lower()

    routing_text = (
        combined
        + " "
        + raw_lower
    )

    has_death = bool(
        deaths
    ) or any(
        phrase in raw_lower
        for phrase in [
            "causing his death",
            "causing her death",
            "causing their death",
            "resulting in his death",
            "resulting in her death",
            "resulting in death",
            "died",
            "was killed",
            "were killed",
            "death"
        ]
    )

    has_weapon = bool(
        weapons
    ) or any(
        word in routing_text
        for word in [
            "knife",
            "sword",
            "firearm",
            "gun",
            "pistol",
            "weapon",
            "stab",
            "stabbing",
            "stabbed",
            "shot",
            "shooting",
            "struck",
            "blow"
        ]
    )

    if has_death:

        concepts.append(
            "causing death"
        )

    if has_weapon:

        concepts.append(
            "causing injury or death with a weapon"
        )

    if has_weapon and has_death:

        concepts.append(
            "causing death by weapon attack"
        )

    if has_death and any(
        phrase in routing_text
        for phrase in [
            "kill",
            "killing",
            "murder",
            "murdered",
            "intended to kill",
            "instruction to kill",
            "ordered to kill"
        ]
    ):

        concepts.append(
            "murder / intentional killing"
        )

    if has_death and has_weapon:

        concepts.append(
            "completed lethal attack causing death"
        )

    order_text = " ".join(
        str(
            x.get("fact", "")
        )
        if isinstance(x, dict)
        else str(x)
        for x in orders
    ).lower()

    if (
        orders
        and any(
            word in order_text
            for word in [
                "kill",
                "murder"
            ]
        )
    ):

        concepts.append(
            "instruction or command to kill"
        )

    elif any(
        phrase in routing_text
        for phrase in [
            "instructed the group to kill",
            "ordered the group to kill",
            "told them to kill",
            "ordered him to kill",
            "ordered her to kill",
            "instructed him to kill",
            "instructed her to kill"
        ]
    ):

        concepts.append(
            "instruction or command to kill"
        )

    if groups:

        concepts.append(
            "group acting together"
        )

    return concepts


# =========================================================
# CHECK WHETHER LLM CONCEPT GENERATION IS NECESSARY
# =========================================================

def concepts_are_sufficient(
    concepts
):

    if not concepts:
        return False

    strong_patterns = [
        "causing death",
        "causing death by weapon attack",
        "completed lethal attack",
        "murder / intentional killing",
        "instruction or command to kill",
        "dishonest taking",
        "theft",
        "defamation",
        "criminal trespass"
    ]

    concept_text = " ".join(
        concepts
    ).lower()

    return any(
        pattern in concept_text
        for pattern in strong_patterns
    )


# =========================================================
# BNS RETRIEVAL
# =========================================================

def build_bns_candidates(
    question,
    facts=None,
    legal_concepts=None
):

    facts = facts or {}
    legal_concepts = legal_concepts or []

    query_parts = []

    if question:

        query_parts.append(
            question
        )

    if facts:

        fact_text = structured_facts_to_text(
            facts
        )

        if fact_text:

            query_parts.append(
                fact_text
            )

    if legal_concepts:

        query_parts.append(
            "\n".join(
                legal_concepts
            )
        )

    retrieval_query = "\n".join(
        query_parts
    )

    candidates = []

    # -----------------------------------------------------
    # BASE SEARCH
    # -----------------------------------------------------

    try:

        base_candidates = search(
            retrieval_query,
            15
        )

        if base_candidates:

            candidates.extend(
                base_candidates
            )

    except Exception as error:

        print(
            f"[RAG] Base retrieval failed: {error}"
        )

    query_lower = (
        retrieval_query.lower()
    )

    legal_queries = []

    # -----------------------------------------------------
    # DEATH / MURDER
    # -----------------------------------------------------

    death_indicators = [
        "death",
        "died",
        "dead",
        "killed",
        "murdered",
        "causing his death",
        "causing her death",
        "resulting in his death",
        "resulting in her death",
        "resulting in death"
    ]

    lethal_indicators = [
        "knife",
        "stab",
        "stabbing",
        "stabbed",
        "gun",
        "firearm",
        "pistol",
        "shoot",
        "shot",
        "sword",
        "weapon",
        "repeatedly struck",
        "repeated blows",
        "hit on the head",
        "struck on the head",
        "blow"
    ]

    has_death = any(
        phrase in query_lower
        for phrase in death_indicators
    )

    has_lethal_conduct = any(
        phrase in query_lower
        for phrase in lethal_indicators
    )

    has_kill_language = any(
        phrase in query_lower
        for phrase in [
            "kill",
            "killing",
            "murder",
            "murdered",
            "intended to kill",
            "instructed to kill",
            "ordered to kill"
        ]
    )

    if has_death and (
        has_lethal_conduct
        or has_kill_language
    ):

        legal_queries.extend([
            "BNS Section 101 murder",
            "BNS Section 103 punishment murder"
        ])

    elif has_death:

        legal_queries.extend([
            "BNS causing death homicide",
            "BNS punishment causing death"
        ])

    # -----------------------------------------------------
    # ABETMENT
    # -----------------------------------------------------

    if (
        "kill" in query_lower
        and any(
            phrase in query_lower
            for phrase in [
                "instructed",
                "ordered",
                "instigated",
                "commanded",
                "told"
            ]
        )
    ):

        legal_queries.append(
            "BNS abetment instigation instruction command offence"
        )

    # -----------------------------------------------------
    # GROUP
    # -----------------------------------------------------

    if facts.get(
        "group_or_assembly_facts"
    ):

        legal_queries.append(
            "BNS group persons acting together common intention"
        )

    # -----------------------------------------------------
    # THEFT
    # -----------------------------------------------------

    if any(
        phrase in query_lower
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

        legal_queries.append(
            "theft movable property dishonest taking possession consent"
        )

    # -----------------------------------------------------
    # RECEIVING STOLEN PROPERTY
    # -----------------------------------------------------

    if any(
        phrase in query_lower
        for phrase in [
            "received stolen",
            "receiving stolen",
            "retained stolen",
            "kept stolen property",
            "knowing it was stolen"
        ]
    ):

        legal_queries.append(
            "dishonestly receives or retains stolen property knowing stolen"
        )

    # -----------------------------------------------------
    # MISAPPROPRIATION
    # -----------------------------------------------------

    if any(
        phrase in query_lower
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
        phrase in query_lower
        for phrase in [
            "defamed",
            "defamation",
            "tarnishing image",
            "tarnished image",
            "reputation",
            "social media",
            "false allegation",
            "published allegations",
            "lowered reputation"
        ]
    ):

        legal_queries.append(
            "defamation imputation reputation publication"
        )

    # -----------------------------------------------------
    # CASTE / COMMUNITY
    # -----------------------------------------------------

    if any(
        phrase in query_lower
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

        legal_queries.append(
            "promoting enmity between groups caste religion community"
        )

    # -----------------------------------------------------
    # INTENTIONAL INSULT
    # -----------------------------------------------------

    if any(
        phrase in query_lower
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
            "intentional insult intent provoke breach public peace"
        )

    # -----------------------------------------------------
    # PUBLIC SERVANT
    # -----------------------------------------------------

    if any(
        phrase in query_lower
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

        legal_queries.append(
            "obstruct public servant discharge public functions"
        )

    # -----------------------------------------------------
    # TRESPASS
    # -----------------------------------------------------

    if any(
        phrase in query_lower
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

        legal_queries.append(
            "criminal trespass house trespass entry dwelling"
        )

    # -----------------------------------------------------
    # TARGETED SEARCH
    # -----------------------------------------------------

    for legal_query in legal_queries:

        try:

            extra = search(
                legal_query,
                6
            )

            if extra:

                candidates.extend(
                    extra
                )

        except Exception as error:

            print(
                f"[RAG] Additional search failed: {error}"
            )

    # -----------------------------------------------------
    # DEDUPLICATION
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

        try:

            section = int(
                section
            )

        except (
            ValueError,
            TypeError
        ):

            continue

        if section < 1 or section > 358:
            continue

        if section not in unique:

            unique[section] = item

        else:

            try:

                old_score = float(
                    unique[
                        section
                    ].get(
                        "score",
                        0
                    )
                )

            except Exception:

                old_score = 0

            try:

                new_score = float(
                    item.get(
                        "score",
                        0
                    )
                )

            except Exception:

                new_score = 0

            if new_score > old_score:

                unique[
                    section
                ] = item

    final_candidates = list(
        unique.values()
    )

    final_candidates.sort(
        key=lambda item: float(
            item.get(
                "score",
                0
            )
        ),
        reverse=True
    )

    # Keep a healthy recall pool.
    return final_candidates[:25]


# =========================================================
# FINAL ANSWER
# =========================================================

def generate_final_legal_answer(
    question,
    facts,
    applicable_sections,
    verified_results
):

    facts_text = structured_facts_to_text(
        facts
    )

    if not applicable_sections:

        return (
            "No BNS section can be conclusively identified "
            "from the provided facts."
        )

    allowed_numbers = [
        int(result["section"])
        for result in applicable_sections
    ]

    allowed_text = ", ".join(
        str(section)
        for section in allowed_numbers
    )

    applicable_text_parts = []

    for result in applicable_sections:

        section_text = result.get(
            "section_text",
            result.get(
                "text",
                ""
            )
        )

        # Avoid sending unnecessarily huge statutory text.
        section_text = section_text[:5000]

        applicable_text_parts.append(
            f"""
BNS SECTION {result['section']}
Title: {result.get('title', '')}
Section type: {result.get('section_type', 'OTHER')}

Section text:
{section_text}

Verification reason:
{result.get('reason', '')}

Supported ingredients:
{result.get('supported_ingredients', [])}

Inferable ingredients:
{result.get('inferable_ingredients', [])}
"""
        )

    applicable_text = "\n".join(
        applicable_text_parts
    )

    prompt = f"""
You are the final legal answer generator for an Indian
Bharatiya Nyaya Sanhita analysis system.

USER QUESTION:

{question}

EXPLICIT FACTS:

{facts_text}

AUTHORIZED BNS SECTION NUMBERS:

{allowed_text}

VERIFIED SECTIONS:

{applicable_text}

STRICT RULES:

1. Mention ONLY authorized BNS section numbers.

2. Do not introduce any other section.

3. Do not invent facts.

4. Do not turn allegations into established facts.

5. Do not use general legal knowledge to add sections.

6. For Section 101, explain the murder definition only
from the supplied facts.

7. For Section 103, state punishment only from the
supplied statutory text.

8. Do not invent aggravated circumstances.

9. Do not call a completed killing an attempt.

10. Do not treat arrest, seizure, investigation, fleeing
or police action as proof of guilt.

11. Clearly distinguish facts from legal conclusions.

12. Keep the answer concise.

13. Do not mention retrieval, verifier, model,
prompt or system architecture.

FORMAT:

BNS Section X — Title

Why it applies:
Brief explanation based only on the supplied facts.

If applicable, state the punishment from the supplied
statutory text.

Do not mention unauthorized section numbers.
"""

    return ask_qwen(
        prompt,
        num_predict=650
    )


# =========================================================
# MAIN CASE ANALYSIS
# =========================================================

def analyze_case(
    question,
    document_text="",
    pre_extracted_facts=None
):

    total_start = time.perf_counter()

    print(
        "\n" + "=" * 70
    )

    print(
        "STEP 1: FACT EXTRACTION"
    )

    print(
        "=" * 70
    )

    fact_start = time.perf_counter()

    if pre_extracted_facts is not None:

        print(
            "Using pre-extracted document facts."
        )

        facts = pre_extracted_facts

    else:

        facts = extract_facts(
            question,
            document_text
        )

    fact_time = time.perf_counter() - fact_start

    print(
        "\nExtracted facts:"
    )

    print(
        facts
    )

    extracted_fact_text = (
        structured_facts_to_text(
            facts
        )
    )

    if not extracted_fact_text.strip():

        print(
            "[WARNING] Fact extraction returned "
            "no usable facts."
        )

        print(
            "[WARNING] Raw input retained for routing."
        )

    # -----------------------------------------------------
    # LEGAL CONCEPTS
    # -----------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "STEP 1B: LEGAL CONCEPT GENERATION"
    )

    print(
        "=" * 70
    )

    concept_start = time.perf_counter()

    deterministic_concepts = (
        deterministic_legal_concepts(
            facts,
            question
        )
    )

    print(
        "\nDeterministic legal concepts:"
    )

    for concept in deterministic_concepts:

        print(
            "-",
            concept
        )

    # -----------------------------------------------------
    # SPEED OPTIMIZATION:
    # ONLY CALL QWEN IF DETERMINISTIC ROUTING IS
    # NOT ALREADY STRONG ENOUGH.
    # -----------------------------------------------------

    if concepts_are_sufficient(
        deterministic_concepts
    ):

        print(
            "\n[LEGAL CONCEPTS] "
            "Skipping Qwen concept generation."
        )

        llm_concepts = []

    else:

        print(
            "\n[LEGAL CONCEPTS] "
            "Running Qwen concept generation."
        )

        llm_concepts = generate_legal_concepts(
            question,
            facts
        )

    legal_concepts = []

    for concept in (
        deterministic_concepts
        + llm_concepts
    ):

        if (
            concept
            and concept not in legal_concepts
        ):

            legal_concepts.append(
                concept
            )

    print(
        "\nFinal legal concepts:"
    )

    for concept in legal_concepts:

        print(
            "-",
            concept
        )

    concept_time = (
        time.perf_counter()
        - concept_start
    )

    # -----------------------------------------------------
    # RETRIEVAL
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

    retrieval_start = time.perf_counter()

    candidates = build_bns_candidates(
        question,
        facts,
        legal_concepts
    )

    retrieval_time = (
        time.perf_counter()
        - retrieval_start
    )

    print(
        "\nRetrieved candidates:"
    )

    for candidate in candidates:

        try:

            score = float(
                candidate.get(
                    "score",
                    0
                )
            )

        except Exception:

            score = 0

        print(
            f"Section {candidate['section']} | "
            f"{candidate.get('title', '')} | "
            f"Score: {score:.4f}"
        )

    # -----------------------------------------------------
    # VERIFICATION
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

    verification_start = time.perf_counter()

    verified_results = verify_candidates(
        candidates,
        facts,
        question
    )

    verification_time = (
        time.perf_counter()
        - verification_start
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
        facts,
        question
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

    candidate_by_section = {}

    for candidate in candidates:

        try:

            section = int(
                candidate["section"]
            )

        except Exception:

            continue

        candidate_by_section[
            section
        ] = candidate

    for result in verified_results:

        try:

            section = int(
                result["section"]
            )

        except Exception:

            continue

        matching_candidate = (
            candidate_by_section.get(
                section
            )
        )

        if matching_candidate:

            result["section_text"] = (
                matching_candidate.get(
                    "text",
                    ""
                )
            )

    # -----------------------------------------------------
    # FINAL ANSWER
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

    final_answer_start = time.perf_counter()

    answer = generate_final_legal_answer(
        question,
        facts,
        applicable_sections,
        verified_results
    )

    final_answer_time = (
        time.perf_counter()
        - final_answer_start
    )

    print(
        "\nGenerated answer:"
    )

    print(
        answer
    )

    # -----------------------------------------------------
    # OUTPUT VALIDATION
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

    total_time = (
        time.perf_counter()
        - total_start
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "PERFORMANCE"
    )

    print(
        "=" * 70
    )

    print(
        f"Fact extraction:       {fact_time:.2f} sec"
    )

    print(
        f"Legal concepts:        {concept_time:.2f} sec"
    )

    print(
        f"BNS retrieval:         {retrieval_time:.2f} sec"
    )

    print(
        f"Section verification:  {verification_time:.2f} sec"
    )

    print(
        f"Final answer:          {final_answer_time:.2f} sec"
    )

    print(
        f"Total:                 {total_time:.2f} sec"
    )

    print(
        "=" * 70
    )

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
        validation[
            "unauthorized_sections"
        ]
    )

    allowed_text = ", ".join(
        str(section)
        for section in allowed_sections
    )

    correction_prompt = f"""
Rewrite the answer below.

ONLY these BNS section numbers are authorized:

{allowed_text}

Remove every unauthorized BNS section number.

Do not introduce new sections.
Do not introduce new facts.
Do not use general legal knowledge.

Return only the corrected answer.

ORIGINAL ANSWER:

{answer}
"""

    corrected_answer = ask_qwen(
        correction_prompt,
        num_predict=450
    )

    second_validation = validate_output(
        corrected_answer,
        allowed_sections
    )

    if second_validation["valid"]:

        return corrected_answer

    return (
        "Based on the provided facts, the conclusively "
        "identified provision(s) are: "
        + ", ".join(
            f"BNS Section {section}"
            for section in allowed_sections
        )
        + ". The available facts should be reviewed "
          "further before drawing additional legal conclusions."
    )


# =========================================================
# MAIN API FUNCTION
# =========================================================

def ask_ai(
    question,
    document_text="",
    filename="",
    pre_extracted_facts=None
):

    question = (
        question or ""
    ).strip()

    # -----------------------------------------------------
    # PRE-EXTRACTED DOCUMENT FACTS
    # -----------------------------------------------------

    if pre_extracted_facts is not None:

        if not question:

            question = (
                "Analyze the present case under the "
                "Bharatiya Nyaya Sanhita based only on "
                "the established facts provided."
            )

        return analyze_case(
            question,
            document_text,
            pre_extracted_facts=pre_extracted_facts
        )

    # -----------------------------------------------------
    # QUESTION + DOCUMENT
    # -----------------------------------------------------

    if document_text and question:

        from backend.document_rag import (
            retrieve_document_chunks
        )

        document_results = (
            retrieve_document_chunks(
                document_text,
                question,
                top_k=5
            )
        )

        document_context_parts = []

        for result in document_results:

            document_context_parts.append(
                result["text"]
            )

        document_context = (
            "\n\n--------------------\n\n"
        ).join(
            document_context_parts
        )

        combined_text = (
            "User question:\n"
            + question
            + "\n\nRelevant document excerpts:\n"
            + document_context
        )

        return analyze_case(
            combined_text,
            document_text
        )

    # -----------------------------------------------------
    # DOCUMENT ONLY
    # -----------------------------------------------------

    if document_text:

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

DOCUMENT SUMMARIES:

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
- Do not introduce legal sections absent from the
  document summaries.
- Distinguish facts from legal conclusions.
- If the document is not a judgment, do not call it
  a judgment.

Give a structured but concise analysis.
"""

        return ask_qwen(
            prompt,
            num_predict=900
        )

    # -----------------------------------------------------
    # QUESTION ONLY
    # -----------------------------------------------------

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

    pages = []

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:

            pages.append(
                page_text
            )

    text = "\n".join(
        pages
    ).strip()

    if not text:

        raise ValueError(
            "No readable text was found in the PDF."
        )

    return text