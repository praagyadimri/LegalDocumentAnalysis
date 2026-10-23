# section_rules.py

import re


def _text(facts):
    if not facts:
        return ""

    parts = []

    for key, value in facts.items():
        if isinstance(value, list):
            parts.extend(str(x) for x in value)
        elif value:
            parts.append(str(value))

    return " ".join(parts).lower()


def _has_any(text, words):
    return any(word in text for word in words)


def _section_number(result):
    try:
        return int(str(result.get("section", "")).strip())
    except Exception:
        return None


def _reject(result, reason):
    result["decision"] = "REJECT"
    result["reason"] = reason
    result["rule_rejected"] = True
    return result


def apply_section_rules(results, facts, question=""):
    """
    Apply general deterministic safety rules after statutory verification.

    Important:
    - Never make a section applicable only because a keyword appears.
    - Never add facts that are not supplied.
    - Deterministic rules may reject unsupported sections.
    - They should not convert an unsupported section into APPLICABLE.
    """

    if not results:
        return results

    fact_text = _text(facts)
    question_text = str(question or "").lower()
    text = fact_text + " " + question_text

    completed_death = _has_any(
        text,
        [
            "died",
            "death",
            "killed",
            "murdered",
            "caused the death",
            "causing death",
            "dead"
        ]
    )

    # These words indicate that the facts actually describe
    # disappearance/suppression of evidence rather than merely
    # possession or disposal of an object.
    evidence_screening = _has_any(
        text,
        [
            "destroyed evidence",
            "destroy evidence",
            "disappeared evidence",
            "caused disappearance of evidence",
            "concealed evidence",
            "conceal evidence",
            "hid the evidence",
            "hide the evidence",
            "disposed of the knife to screen",
            "destroyed the knife to screen",
            "disposed of evidence to screen",
            "screen the offender",
            "screened the offender",
            "screen the offenders",
            "screened the offenders",
            "with intent to screen"
        ]
    )

    # Section 120 requires a very specific purpose:
    # obtaining confession/information OR compelling restoration
    # of property. Generic "compel action" is not enough.
    section_120_purpose = _has_any(
        text,
        [
            "extort confession",
            "extorting a confession",
            "extort information",
            "extorting information",
            "obtain a confession",
            "obtain information",
            "compel him to confess",
            "compel him to give information",
            "compel restoration of property",
            "compel restoration",
            "restore the property",
            "restore stolen property",
            "recover the property"
        ]
    )

    # Section 307 requires theft/extortion AND preparation for
    # causing death/hurt/restraint in order to commit that theft
    # or extortion. Merely carrying a knife during an attack is
    # insufficient.
    theft_or_extortion = _has_any(
        text,
        [
            "theft",
            "steal",
            "stealing",
            "stole",
            "stolen",
            "rob",
            "robbery",
            "extort",
            "extortion"
        ]
    )

    preparation_for_theft = _has_any(
        text,
        [
            "prepared to cause death to commit theft",
            "prepared to cause hurt to commit theft",
            "prepared to cause restraint to commit theft",
            "prepared for causing death in order to commit theft",
            "prepared for causing hurt in order to commit theft",
            "prepared for causing restraint in order to commit theft",
            "carried a weapon to commit theft",
            "carried a knife to commit theft",
            "armed himself to commit theft",
            "armed themselves to commit theft",
            "prepared to cause death to commit extortion",
            "prepared to cause hurt to commit extortion",
            "prepared to cause restraint to commit extortion"
        ]
    )

    cleaned = []

    for original in results:
        result = dict(original)
        section = _section_number(result)

        # ---------------------------------------------------------
        # Section 120
        # Voluntarily causing hurt/grievous hurt for the specified
        # purpose of extorting confession/information or compelling
        # restoration of property.
        # ---------------------------------------------------------
        if section == 120:
            if not section_120_purpose:
                result = _reject(
                    result,
                    "Section 120 requires hurt or grievous hurt specifically "
                    "for extorting a confession/information or compelling "
                    "restoration of property. That purpose is not established "
                    "by the supplied facts."
                )
                cleaned.append(result)
                continue

        # ---------------------------------------------------------
        # Section 238
        # Disappearance of evidence / screening offender.
        #
        # Do NOT reject merely because the object was disposed of.
        # But the supplied facts must indicate disappearance/concealment
        # of evidence with the required screening purpose.
        # ---------------------------------------------------------
        if section == 238:
            if not evidence_screening:
                result = _reject(
                    result,
                    "Disappearance or concealment of evidence with the "
                    "required intention to screen an offender is not "
                    "established by the supplied facts."
                )
                cleaned.append(result)
                continue

        # ---------------------------------------------------------
        # Section 307
        # Theft/extortion after preparation for causing death, hurt,
        # or restraint.
        #
        # Carrying/using a knife in an unrelated attack is NOT enough.
        # ---------------------------------------------------------
        if section == 307:
            if not theft_or_extortion or not preparation_for_theft:
                result = _reject(
                    result,
                    "Section 307 requires theft or extortion together with "
                    "prior preparation for causing death, hurt, or restraint "
                    "for the purpose of committing that theft or extortion. "
                    "Those essential ingredients are not established."
                )
                cleaned.append(result)
                continue

        # ---------------------------------------------------------
        # Attempt provisions must not survive when the facts clearly
        # establish a completed death.
        # ---------------------------------------------------------
        if section in (109, 110) and completed_death:
            result = _reject(
                result,
                "An attempt provision is not applicable where the supplied "
                "facts establish that the victim actually died."
            )
            cleaned.append(result)
            continue

        # ---------------------------------------------------------
        # Different-victim provision requires an actual different
        # victim outcome, not merely words such as "intended to kill".
        # ---------------------------------------------------------
        if section == 102:
            different_victim = _has_any(
                text,
                [
                    "different person was killed",
                    "another person was killed",
                    "another person died",
                    "wrong person was killed",
                    "wrong victim was killed",
                    "different victim was killed"
                ]
            )

            if not different_victim:
                result = _reject(
                    result,
                    "The facts do not establish that the act caused the "
                    "death of a different person from the intended victim."
                )
                cleaned.append(result)
                continue

        # ---------------------------------------------------------
        # Pregnancy / miscarriage / unborn-child provisions
        # ---------------------------------------------------------
        if section in (88, 90, 92):
            pregnancy_context = _has_any(
                text,
                [
                    "pregnant",
                    "pregnancy",
                    "miscarriage",
                    "unborn child",
                    "unborn",
                    "quick with child",
                    "foetus",
                    "fetus"
                ]
            )

            if not pregnancy_context:
                result = _reject(
                    result,
                    "The supplied facts do not establish the required "
                    "pregnancy, miscarriage, unborn-child, or foetal context."
                )
                cleaned.append(result)
                continue

        # ---------------------------------------------------------
        # Public-servant related provisions
        # ---------------------------------------------------------
        if section in (198, 199, 200, 201, 202, 203, 204, 205):
            public_servant_context = _has_any(
                text,
                [
                    "public servant",
                    "police officer",
                    "government officer",
                    "government official",
                    "magistrate",
                    "judge",
                    "officer of the government"
                ]
            )

            if not public_servant_context:
                result = _reject(
                    result,
                    "The supplied facts do not establish the required "
                    "public-servant context."
                )
                cleaned.append(result)
                continue

        # ---------------------------------------------------------
        # Private-defence provisions
        # ---------------------------------------------------------
        if section in (34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44):
            defence_context = _has_any(
                text,
                [
                    "private defence",
                    "self defence",
                    "self-defense",
                    "defend himself",
                    "defend herself",
                    "defend themselves",
                    "defending himself",
                    "defending herself",
                    "defending themselves",
                    "defence of body",
                    "defence of property"
                ]
            )

            if not defence_context:
                result = _reject(
                    result,
                    "The supplied facts do not establish a private-defence "
                    "context required for this provision."
                )
                cleaned.append(result)
                continue

        cleaned.append(result)

    # -------------------------------------------------------------
    # Final safety pass:
    # Never convert REJECT/POSSIBLE into APPLICABLE here.
    # Only remove duplicate sections.
    # -------------------------------------------------------------
    final_results = []
    seen = set()

    for result in cleaned:
        section = str(result.get("section", "")).strip()

        if section in seen:
            continue

        seen.add(section)
        final_results.append(result)

    return final_results