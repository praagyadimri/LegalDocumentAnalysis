from pathlib import Path

from backend.document_analysis import analyze_document


PDF_PATH = Path(
    r"test_docs\judgement.pdf"
)


with open(
    PDF_PATH,
    "rb"
) as file:

    pdf_bytes = file.read()


result = analyze_document(
    pdf_bytes
)


print("\nPAGE COUNT:")
print(
    result["page_count"]
)

print("\nVERIFIED FACTS:")

for fact in result["facts"]:

    print(
        "\nCATEGORY:",
        fact["category"]
    )

    print(
        "FACT:",
        fact["fact"]
    )

    print(
        "PAGE:",
        fact.get("page")
    )

    print(
        "CLAUSE:",
        fact.get("section_number")
    )

    print(
        "EVIDENCE:",
        fact.get("evidence")
    )

print("\nBNS FACTS:")

for key, values in result[
    "bns_facts"
].items():

    if values:

        print(
            key,
            ":",
            values
        )