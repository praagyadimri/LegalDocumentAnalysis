from backend.analyzer import ask_ai


question = """
Mr hemant caste-based remarks to arora , publicly humiliating the complainant, obstructing government duties, and allegedly tarnishing their image on social media. What sections under BNS apply to him
"""

answer = ask_ai(question)

print("\n" + "=" * 80)
print("FINAL ANSWER")
print("=" * 80)
print(answer)