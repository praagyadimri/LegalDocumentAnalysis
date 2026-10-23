# from backend.rag import search

# results = search(
#     "What is the punishment for murder under the Bharatiya Nyaya Sanhita?",
#     10
# )

# for result in results:
#     print(f"PAGE {result['page']}:")
#     print(f"SECTION {result['section']} | PAGE {result['page']}:")
#     print()

from backend.rag import search

query = "What is the punishment for murder under the Bharatiya Nyaya Sanhita?"

results = search(query, 10)

print("\nQUERY:")
print(query)

print("\nRESULTS:\n")

for rank, result in enumerate(results, start=1):

    print("=" * 80)

    print(f"RANK: {rank}")
    print(f"SECTION: {result['section']}")
    print(f"TITLE: {result['title']}")
    print(f"PAGE: {result['page']}")

    print(f"\nFINAL SCORE: {result['score']:.4f}")
    print(f"Semantic: {result['semantic_score']:.4f}")
    print(f"Keyword: {result['keyword_score']:.4f}")
    print(f"Phrase: {result['phrase_score']:.4f}")

    print("\nTEXT:")
    print(result["text"])

    print()