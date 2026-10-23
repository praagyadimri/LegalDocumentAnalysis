# # output.validator.py
# import re


# MAX_BNS_SECTION = 358


# SECTION_PATTERNS = [
#     # Section 101
#     r"\bsection\s+(\d{1,3})(?:\s*\(\s*\d+\s*\))?",

#     # BNS Section 101
#     r"\bbns\s+section\s+(\d{1,3})(?:\s*\(\s*\d+\s*\))?",

#     # Sec. 101
#     r"\bsec\.?\s+(\d{1,3})(?:\s*\(\s*\d+\s*\))?"
# ]


# def extract_section_numbers(
#     text
# ):

#     if not text:
#         return []

#     numbers = []

#     for pattern in SECTION_PATTERNS:

#         matches = re.findall(
#             pattern,
#             text,
#             flags=re.IGNORECASE
#         )

#         for match in matches:

#             try:

#                 number = int(
#                     match
#                 )

#             except (
#                 ValueError,
#                 TypeError
#             ):

#                 continue

#             if (
#                 1 <= number
#                 <= MAX_BNS_SECTION
#             ):

#                 if number not in numbers:

#                     numbers.append(
#                         number
#                     )

#     return numbers


# def validate_output(
#     answer,
#     allowed_sections
# ):

#     allowed = set()

#     for section in allowed_sections:

#         try:

#             section = int(
#                 section
#             )

#             if (
#                 1 <= section
#                 <= MAX_BNS_SECTION
#             ):

#                 allowed.add(
#                     section
#                 )

#         except (
#             ValueError,
#             TypeError
#         ):
#             continue

#     mentioned = extract_section_numbers(
#         answer
#     )

#     unauthorized = [
#         section
#         for section in mentioned
#         if section not in allowed
#     ]

#     # -----------------------------------------------------
#     # ZERO SECTION CASE
#     # -----------------------------------------------------

#     if not allowed:

#         valid = len(
#             mentioned
#         ) == 0

#         return {
#             "valid": valid,
#             "mentioned_sections": mentioned,
#             "unauthorized_sections": unauthorized
#         }

#     return {
#         "valid": len(
#             unauthorized
#         ) == 0,
#         "mentioned_sections": mentioned,
#         "unauthorized_sections": unauthorized
#     }





import re


MAX_BNS_SECTION = 358


SECTION_PATTERNS = [
    r"\bsection\s+(\d{1,3})(?:\s*\(\s*\d+\s*\))?",
    r"\bbns\s+section\s+(\d{1,3})(?:\s*\(\s*\d+\s*\))?",
    r"\bsec\.?\s+(\d{1,3})(?:\s*\(\s*\d+\s*\))?"
]


def extract_section_numbers(
    text
):

    if not text:

        return []

    numbers = []

    for pattern in SECTION_PATTERNS:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for match in matches:

            try:

                number = int(
                    match
                )

            except (
                ValueError,
                TypeError
            ):

                continue

            if not (
                1 <= number <= MAX_BNS_SECTION
            ):

                continue

            if number not in numbers:

                numbers.append(
                    number
                )

    return numbers


def validate_output(
    answer,
    allowed_sections
):

    allowed = set()

    for section in allowed_sections:

        try:

            section = int(
                section
            )

        except (
            ValueError,
            TypeError
        ):

            continue

        if (
            1 <= section
            <= MAX_BNS_SECTION
        ):

            allowed.add(
                section
            )

    mentioned = extract_section_numbers(
        answer
    )

    unauthorized = [
        section
        for section in mentioned
        if section not in allowed
    ]

    if not allowed:

        return {
            "valid": len(
                mentioned
            ) == 0,
            "mentioned_sections": mentioned,
            "unauthorized_sections": unauthorized
        }

    return {
        "valid": len(
            unauthorized
        ) == 0,
        "mentioned_sections": mentioned,
        "unauthorized_sections": unauthorized
    }