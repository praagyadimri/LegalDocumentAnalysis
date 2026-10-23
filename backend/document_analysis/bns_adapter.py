# bns_adapter.py
import json
from pathlib import Path


ALLOWED_BNS_SOURCE_ROLES = {
    "CASE_FACT",
}

FORBIDDEN_BNS_SOURCE_ROLES = {
    "PROCEDURAL_EVENT",
    "COURT_ORDER",
    "REFERENCED_CASE",
    "EXTERNAL_EXAMPLE",
    "LEGAL_PROPOSITION",
    "GENERAL_OBSERVATION",
    "PUBLICATION",
    "BACKGROUND",
    "OTHER",
    "PARTY_ALLEGATION",
    "PARTY_ARGUMENT",
}


EMPTY_BNS_FACTS = {
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
    "other_facts": [],
}


def is_bns_relevant(result):
    relevance = (
        result.get("bns_relevance", {})
        .get("classification", "")
        .strip()
        .upper()
    )

    return relevance in {"HIGH", "MEDIUM"}


def _clean_text(value):
    if not isinstance(value, str):
        return ""

    return " ".join(value.split()).strip()


def _make_fact_item(item, category):
    return {
        "text": _clean_text(item.get("fact", "")),
        "evidence": _clean_text(item.get("evidence", "")),
        "page": item.get("page"),
        "role": item.get("role", ""),
        "confidence": item.get("confidence", 0.0),
        "category": category,
    }


def _is_case_fact(item):
    role = str(item.get("role", "")).strip().upper()

    if role in FORBIDDEN_BNS_SOURCE_ROLES:
        return False

    return role in ALLOWED_BNS_SOURCE_ROLES


def _text_contains_any(text, phrases):
    text = text.lower()

    return any(
        phrase.lower() in text
        for phrase in phrases
    )


def _extract_parties(result):
    """
    Extract persons from Gemini's structured present-case parties.

    Party roles such as ACCUSED and VICTIM are not Gemini
    source-fact roles, so they are intentionally kept separately.
    """

    persons = []

    present_case = result.get("present_case", {})
    parties = present_case.get("parties", [])

    if not isinstance(parties, list):
        return persons

    for party in parties:
        if not isinstance(party, dict):
            continue

        name = _clean_text(party.get("name", ""))
        role = _clean_text(party.get("role", ""))
        description = _clean_text(
            party.get("description", "")
        )

        if not name:
            continue

        persons.append({
            "text": name,
            "role": role,
            "description": description,
            "category": "persons",
        })

    return persons


def _classify_case_fact(item):
    """
    Classify an established CASE_FACT.

    The classification is deliberately conservative.
    """

    text = _clean_text(item.get("fact", ""))

    if not text:
        return []

    lower = text.lower()

    categories = []

    # ---------------------------------------------------------
    # DEATH
    # ---------------------------------------------------------

    death_terms = [
        "died",
        "death",
        "dead",
        "killed",
        "succumbed",
    ]

    if _text_contains_any(lower, death_terms):
        categories.append("deaths")

    # ---------------------------------------------------------
    # INJURY
    # ---------------------------------------------------------

    injury_terms = [
        "injur",
        "wound",
        "stab wound",
        "severe injuries",
        "serious injuries",
        "fracture",
        "bleeding",
        "hurt",
        "bodily harm",
    ]

    if _text_contains_any(lower, injury_terms):
        categories.append("injuries")

    # ---------------------------------------------------------
    # WEAPON
    # ---------------------------------------------------------

    weapon_terms = [
        "knife",
        "sword",
        "firearm",
        "pistol",
        "rifle",
        "gun",
        "weapon",
        "gunshot",
        "bullet",
        "blade",
    ]

    if _text_contains_any(lower, weapon_terms):
        categories.append("weapons")

    # ---------------------------------------------------------
    # THREATS
    # ---------------------------------------------------------

    threat_terms = [
        "threatened",
        "threat",
        "threatening",
        "intimidated",
        "intimidation",
    ]

    if _text_contains_any(lower, threat_terms):
        categories.append("threats")

    # ---------------------------------------------------------
    # PROPERTY
    # ---------------------------------------------------------

    property_terms = [
        "stole",
        "stolen",
        "robbed",
        "property",
        "cash",
        "money",
        "jewellery",
        "jewelry",
        "valuable",
        "vehicle",
        "destroyed property",
        "damaged property",
    ]

    if _text_contains_any(lower, property_terms):
        categories.append("property")

    # ---------------------------------------------------------
    # ACTION
    # ---------------------------------------------------------

    action_terms = [
        "stabbed",
        "stab",
        "killed",
        "struck",
        "hit",
        "beat",
        "assaulted",
        "attacked",
        "shot",
        "fired",
        "choked",
        "strangled",
        "pushed",
        "threw",
        "caused",
        "inflicted",
    ]

    if _text_contains_any(lower, action_terms):
        categories.append("actions")

    # ---------------------------------------------------------
    # EXPLICIT INTENT
    # ---------------------------------------------------------

    explicit_intent_terms = [
        "deliberately",
        "intentionally",
        "with intent",
        "with the intention",
        "intended to",
        "purposefully",
        "knowingly",
    ]

    if _text_contains_any(lower, explicit_intent_terms):
        categories.append("intent_facts")

    # ---------------------------------------------------------
    # EXPLICIT KNOWLEDGE
    # ---------------------------------------------------------

    explicit_knowledge_terms = [
        "knew that",
        "knowledge that",
        "aware that",
        "knowing that",
        "was aware",
    ]

    if _text_contains_any(lower, explicit_knowledge_terms):
        categories.append("knowledge_facts")

    # ---------------------------------------------------------
    # OTHER
    # ---------------------------------------------------------

    if not categories:
        categories.append("other_facts")

    return categories


def _is_weapon_recovery_fact(text):
    """
    Recovery/seizure of a weapon is evidence, not automatically
    another weapon occurrence.
    """

    lower = text.lower()

    recovery_terms = [
        "recovered",
        "recovery",
        "seized",
        "found by police",
        "found by the investigating officer",
    ]

    return _text_contains_any(lower, recovery_terms)


def _is_evidence_only_action(text):
    """
    Statements such as CCTV recordings should not create a
    duplicate criminal action when the actual action has already
    been established elsewhere.
    """

    lower = text.lower()

    evidence_terms = [
        "cctv footage",
        "cctv",
        "video footage",
        "video recording",
        "camera footage",
        "recorded",
        "recording showed",
        "footage showed",
    ]

    return _text_contains_any(lower, evidence_terms)


def _extract_bns_relevant_facts(result):
    facts = result.get("bns_relevant_facts", [])

    if not isinstance(facts, list):
        return []

    return [
        item
        for item in facts
        if isinstance(item, dict)
        and _is_case_fact(item)
    ]


def _fallback_case_facts(result):
    present_case = result.get("present_case", {})
    facts = present_case.get("facts", [])

    if not isinstance(facts, list):
        return []

    return [
        item
        for item in facts
        if isinstance(item, dict)
        and _is_case_fact(item)
    ]


def _append_unique(target, item):
    text = _clean_text(item.get("text", ""))

    if not text:
        return

    for existing in target:
        if (
            _clean_text(existing.get("text", "")).lower()
            == text.lower()
        ):
            return

    target.append(item)


def _build_bns_facts(result):
    facts = {
        key: [] if isinstance(value, list) else value
        for key, value in EMPTY_BNS_FACTS.items()
    }

    # Persons come from structured present-case parties.
    facts["persons"] = _extract_parties(result)

    relevant_items = _extract_bns_relevant_facts(result)

    if not relevant_items:
        relevant_items = _fallback_case_facts(result)

    for item in relevant_items:

        text = _clean_text(item.get("fact", ""))

        if not text:
            continue

        categories = _classify_case_fact(item)

        # -----------------------------------------------------
        # CCTV / recording statements are evidence of an action,
        # not a second occurrence of the action.
        # -----------------------------------------------------

        if (
            "actions" in categories
            and _is_evidence_only_action(text)
        ):
            categories.remove("actions")

            if not categories:
                categories.append("other_facts")

        # -----------------------------------------------------
        # Weapon recovery is evidence and should not create
        # another weapon entry.
        # -----------------------------------------------------

        if (
            "weapons" in categories
            and _is_weapon_recovery_fact(text)
        ):
            categories.remove("weapons")

            if not categories:
                categories.append("other_facts")

        # -----------------------------------------------------
        # Add the fact to each applicable category.
        # -----------------------------------------------------

        for category in categories:

            fact_item = _make_fact_item(
                item,
                category,
            )

            _append_unique(
                facts[category],
                fact_item,
            )

    return facts


def build_bns_facts(result):
    if not is_bns_relevant(result):
        return {
            key: [] if isinstance(value, list) else value
            for key, value in EMPTY_BNS_FACTS.items()
        }

    return _build_bns_facts(result)


def validate_bns_adapter_output(result, facts):
    """
    Validate established factual categories.

    Persons are validated separately because their role values
    are party roles such as Accused/Victim, not Gemini fact roles.
    """

    errors = []

    relevance = (
        result.get("bns_relevance", {})
        .get("classification", "")
        .strip()
        .upper()
    )

    factual_categories = [
        "actions",
        "injuries",
        "deaths",
        "weapons",
        "threats",
        "property",
        "intent_facts",
        "knowledge_facts",
        "other_facts",
    ]

    total_facts = sum(
        len(facts.get(category, []))
        for category in factual_categories
    )

    if relevance in {"NONE", "LOW"} and total_facts > 0:
        errors.append(
            "BNS facts were produced despite NONE/LOW BNS relevance."
        )

    # ---------------------------------------------------------
    # Validate factual categories only.
    # Persons are intentionally excluded here.
    # ---------------------------------------------------------

    for category in factual_categories:

        items = facts.get(category, [])

        if not isinstance(items, list):
            continue

        for item in items:

            role = (
                str(item.get("role", ""))
                .strip()
                .upper()
            )

            if role != "CASE_FACT":
                errors.append(
                    f"Non-CASE_FACT entered established BNS "
                    f"facts in {category}: {role}"
                )

    # ---------------------------------------------------------
    # Validate persons separately.
    # ---------------------------------------------------------

    persons = facts.get("persons", [])

    if not isinstance(persons, list):
        errors.append(
            "Persons must be represented as a list."
        )
    else:
        for person in persons:

            if not isinstance(person, dict):
                errors.append(
                    "Invalid person entry."
                )
                continue

            if not _clean_text(person.get("text", "")):
                errors.append(
                    "Person entry has no name."
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "total_bns_facts": total_facts,
        "bns_relevance": relevance,
    }


def adapt_gemini_to_bns(result):
    bns_relevant = is_bns_relevant(result)

    if not bns_relevant:
        facts = {
            key: [] if isinstance(value, list) else value
            for key, value in EMPTY_BNS_FACTS.items()
        }
    else:
        facts = build_bns_facts(result)

    validation = validate_bns_adapter_output(
        result,
        facts,
    )

    return {
        "bns_relevant": bns_relevant,
        "facts": facts,
        "validation": validation,
    }


def _print_fact_counts(facts):
    categories = [
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
    ]

    print("\nFact counts:")

    for category in categories:
        print(
            f"  {category}: "
            f"{len(facts.get(category, []))}"
        )


if __name__ == "__main__":

    print("=" * 70)
    print("GEMINI → BNS ADAPTER TEST")
    print("=" * 70)

    analysis_path = Path(
        "gemini_document_analysis.json"
    )

    if not analysis_path.exists():
        raise FileNotFoundError(
            f"Analysis file not found: {analysis_path}"
        )

    with analysis_path.open(
        "r",
        encoding="utf-8",
    ) as f:
        result = json.load(f)

    adapted = adapt_gemini_to_bns(result)

    print(
        f"BNS relevant: "
        f"{adapted['bns_relevant']}"
    )

    print(
        f"Validation valid: "
        f"{adapted['validation']['valid']}"
    )

    if adapted["validation"]["errors"]:
        print("\nValidation errors:")

        for error in adapted["validation"]["errors"]:
            print(f"  - {error}")

    facts = adapted["facts"]

    print(
        f"Total BNS facts: "
        f"{adapted['validation']['total_bns_facts']}"
    )

    _print_fact_counts(facts)

    print("\nFull adapter output:")

    print(
        json.dumps(
            adapted,
            indent=2,
            ensure_ascii=False,
        )
    )