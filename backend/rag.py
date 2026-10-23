# rag.py
import os
import re
import pickle
import numpy as np
import faiss

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

PDF_PATH = os.path.join(
    BASE_DIR,
    "reference",
    "legal_handbook.pdf"
)

INDEX_PATH = os.path.join(
    BASE_DIR,
    "reference",
    "legal_index.faiss"
)

CHUNKS_PATH = os.path.join(
    BASE_DIR,
    "reference",
    "legal_chunks.pkl"
)


# ============================================================
# EMBEDDING MODEL
# ============================================================

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# ============================================================
# COMMON LEGAL STOP WORDS
# ============================================================

STOP_WORDS = {
    "what",
    "is",
    "are",
    "the",
    "a",
    "an",
    "of",
    "for",
    "to",
    "under",
    "in",
    "on",
    "and",
    "or",
    "with",
    "from",
    "by",
    "does",
    "do",
    "can",
    "may",
    "be",
    "this",
    "that",
    "which",
    "who",
    "was",
    "were",
    "how",
    "when",
    "where",
    "why",
    "section",
    "bns",
    "bharatiya",
    "nyaya",
    "sanhita",
    "2023",
}


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    """
    Normalize text for keyword/title matching.
    """

    if not text:
        return ""

    text = text.lower()

    # Replace punctuation with spaces.
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text):
    """
    Convert text into useful normalized tokens.
    """

    text = normalize_text(text)

    tokens = text.split()

    return [
        token
        for token in tokens
        if token not in STOP_WORDS
        and len(token) > 1
    ]


# ============================================================
# PDF LOADING
# ============================================================

def load_pdf():
    """
    Read the BNS PDF page by page.
    """

    reader = PdfReader(PDF_PATH)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        text = page.extract_text()

        if text:

            text = text.strip()

            if text:

                pages.append({
                    "page": page_number,
                    "text": text
                })

    return pages


# ============================================================
# SECTION DETECTION
# ============================================================

SECTION_PATTERN = re.compile(
    r"^\s*(\d{1,3})\.\s*(.+)"
)


def is_section_start(line):
    """
    Detect lines such as:

    103. Punishment for murder.
    109. Attempt to murder.
    200. Punishment for non-treatment of victim.
    """

    match = SECTION_PATTERN.match(line)

    if not match:
        return None

    section_number = match.group(1)

    # BNS contains sections 1-358.
    number = int(section_number)

    if number < 1 or number > 358:
        return None

    return number


# ============================================================
# EXTRACT SECTION TITLE
# ============================================================

def extract_section_title(text, section_number):
    """
    Extract the legal title from the beginning of a BNS section.

    Examples:

    103. Punishment for murder. 103. Punishment for murder.—...

    -> Punishment for murder

    109. Attempt to murder. 109. Attempt to murder.—...

    -> Attempt to murder
    """

    if not text:
        return ""

    text = text.replace("\n", " ").strip()

    pattern = re.compile(
        rf"^\s*{section_number}\.\s*"
        rf"(.+?)"
        rf"\s+{section_number}\.\s*",
        re.IGNORECASE
    )

    match = pattern.search(text)

    if match:

        title = match.group(1).strip()

        # Remove trailing punctuation.
        title = re.sub(
            r"[.\-—–:]+$",
            "",
            title
        )

        return title.strip()

    # Fallback for sections that occur only once.
    pattern = re.compile(
        rf"^\s*{section_number}\.\s*(.+?)"
        rf"(?=\s+[—–-]|\s*\(|$)",
        re.IGNORECASE
    )

    match = pattern.search(text)

    if match:

        title = match.group(1).strip()

        title = re.sub(
            r"[.\-—–:]+$",
            "",
            title
        )

        return title.strip()

    return ""

# ============================================================
# CREATE SECTION CHUNKS
# ============================================================

def create_chunks(pages):

    raw_chunks = []

    for page in pages:

        page_number = page["page"]

        lines = page["text"].splitlines()

        current_section = None
        current_text = []

        for line in lines:

            line = line.strip()

            if not line:
                continue

            section_number = is_section_start(line)

            if section_number is not None:

                # Save previous section.
                if (
                    current_section is not None
                    and current_text
                ):

                    raw_chunks.append({
                        "page": current_page,
                        "section": current_section,
                        "text": " ".join(current_text)
                    })

                current_section = section_number
                current_page = page_number

                current_text = [line]

            else:

                if current_section is not None:

                    current_text.append(line)

        # Save final section on page.
        if (
            current_section is not None
            and current_text
        ):

            raw_chunks.append({
                "page": current_page,
                "section": current_section,
                "text": " ".join(current_text)
            })

    return raw_chunks


# ============================================================
# CLEAN / DEDUPLICATE SECTIONS
# ============================================================

def clean_chunks(raw_chunks):

    section_map = {}

    for chunk in raw_chunks:

        section_number = chunk["section"]

        text = chunk["text"].strip()

        if not text:
            continue

        if section_number not in section_map:

            section_map[section_number] = {
                "page": chunk["page"],
                "section": section_number,
                "text": text
            }

        else:

            # Some PDF pages may split a section.
            existing = section_map[section_number]

            existing["text"] += " " + text

    chunks = []

    for section_number in sorted(section_map):

        chunk = section_map[section_number]

        title = extract_section_title(
            chunk["text"],
            section_number
        )

        chunk["title"] = title

        chunks.append(chunk)

    return chunks


# ============================================================
# BUILD FAISS INDEX
# ============================================================

def create_index():

    print("=" * 35)
    print("Building BNS legal knowledge base")
    print("=" * 35)

    print("Reading BNS handbook...")

    pages = load_pdf()

    print(
        f"Pages loaded: {len(pages)}"
    )

    raw_chunks = create_chunks(
        pages
    )

    print(
        f"Raw section chunks: {len(raw_chunks)}"
    )

    chunks = clean_chunks(
        raw_chunks
    )

    print(
        f"Unique BNS sections: {len(chunks)}"
    )

    if not chunks:

        raise RuntimeError(
            "No BNS sections were extracted from the PDF."
        )

    texts = []

    for chunk in chunks:

        # Embedding text contains title + statutory text.
        embedding_text = (
            f"Section {chunk['section']}. "
            f"{chunk['title']}. "
            f"{chunk['text']}"
        )

        texts.append(
            embedding_text
        )

    print("Creating embeddings...")

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32"
    )

    # Cosine similarity through normalized vectors.
    index = faiss.IndexFlatIP(
        embeddings.shape[1]
    )

    index.add(
        embeddings
    )

    faiss.write_index(
        index,
        INDEX_PATH
    )

    with open(
        CHUNKS_PATH,
        "wb"
    ) as file:

        pickle.dump(
            chunks,
            file
        )

    print()
    print("BNS index created successfully.")
    print(
        f"Sections indexed: {len(chunks)}"
    )


# ============================================================
# LOAD INDEX
# ============================================================

def load_index():

    if (
        not os.path.exists(INDEX_PATH)
        or not os.path.exists(CHUNKS_PATH)
    ):

        create_index()

    index = faiss.read_index(
        INDEX_PATH
    )

    with open(
        CHUNKS_PATH,
        "rb"
    ) as file:

        chunks = pickle.load(file)

    return index, chunks


# ============================================================
# LEGAL QUERY TERMS
# ============================================================

def extract_query_terms(query):

    normalized_query = normalize_text(
        query
    )

    tokens = tokenize(
        query
    )

    return normalized_query, tokens


# ============================================================
# KEYWORD SCORE
# ============================================================

def keyword_score(
    query_tokens,
    title,
    text
):

    title_tokens = set(
        tokenize(title)
    )

    text_tokens = set(
        tokenize(text)
    )

    if not query_tokens:
        return 0.0

    title_matches = sum(
        1
        for token in query_tokens
        if token in title_tokens
    )

    text_matches = sum(
        1
        for token in query_tokens
        if token in text_tokens
    )

    # Title matches are much more important
    # than matches buried inside statutory text.

    title_score = (
        title_matches /
        len(query_tokens)
    )

    text_score = (
        text_matches /
        len(query_tokens)
    )

    score = (
        0.75 * title_score
        +
        0.25 * text_score
    )

    return min(
        score,
        1.0
    )


# ============================================================
# EXACT PHRASE SCORE
# ============================================================

def phrase_score(
    normalized_query,
    title
):

    normalized_title = normalize_text(
        title
    )

    if not normalized_title:
        return 0.0

    # Exact title inside query.
    if normalized_title in normalized_query:

        return 1.0

    # Exact important phrase combinations.
    query_tokens = set(
        tokenize(normalized_query)
    )

    title_tokens = tokenize(
        normalized_title
    )

    if not title_tokens:
        return 0.0

    matched = sum(
        1
        for token in title_tokens
        if token in query_tokens
    )

    if matched == len(title_tokens):

        return 1.0

    if matched >= 2:

        return 0.7

    return 0.0


# ============================================================
# SECTION NUMBER MATCHING
# ============================================================

def section_number_score(
    query,
    section
):

    query_lower = query.lower()

    patterns = [
        rf"\bsection\s+{section}\b",
        rf"\bsec\.?\s*{section}\b",
        rf"\b{section}\s+of\s+bns\b",
    ]

    for pattern in patterns:

        if re.search(
            pattern,
            query_lower
        ):

            return 1.0

    return 0.0


# ============================================================
# HYBRID SEARCH
# ============================================================

def search(
    query,
    top_k=10
):

    if not query or not query.strip():

        return []

    index, chunks = load_index()

    normalized_query, query_tokens = (
        extract_query_terms(query)
    )

    # --------------------------------------------------------
    # Semantic retrieval
    # --------------------------------------------------------

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32"
    )

    # Retrieve more candidates than we finally return.
    #
    # This is important because hybrid reranking
    # needs a larger candidate pool.

    candidate_k = min(
        max(top_k * 5, 50),
        len(chunks)
    )

    semantic_scores, indices = (
        index.search(
            query_embedding,
            candidate_k
        )
    )

    candidates = []

    for semantic_score, index_number in zip(
        semantic_scores[0],
        indices[0]
    ):

        if index_number < 0:
            continue

        if index_number >= len(chunks):
            continue

        chunk = chunks[index_number]

        semantic_score = float(
            semantic_score
        )

        # ----------------------------------------------------
        # Keyword score
        # ----------------------------------------------------

        kw_score = keyword_score(
            query_tokens,
            chunk.get("title", ""),
            chunk.get("text", "")
        )

        # ----------------------------------------------------
        # Exact phrase score
        # ----------------------------------------------------

        ph_score = phrase_score(
            normalized_query,
            chunk.get("title", "")
        )

        # ----------------------------------------------------
        # Section number score
        # ----------------------------------------------------

        sec_score = section_number_score(
            query,
            chunk["section"]
        )

        # ----------------------------------------------------
        # Hybrid score
        # ----------------------------------------------------

        final_score = (
            0.45 * semantic_score
            +
            0.30 * kw_score
            +
            0.20 * ph_score
            +
            0.05 * sec_score
        )

        candidates.append({
            "page": chunk["page"],
            "section": chunk["section"],
            "title": chunk.get(
                "title",
                ""
            ),
            "text": chunk["text"],

            # Keep individual scores for debugging.
            "semantic_score": semantic_score,
            "keyword_score": kw_score,
            "phrase_score": ph_score,
            "section_number_score": sec_score,

            "score": float(
                final_score
            )
        })

    # --------------------------------------------------------
    # Sort by hybrid score
    # --------------------------------------------------------

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # --------------------------------------------------------
    # Return top K
    # --------------------------------------------------------

    return candidates[:top_k]


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # Delete old index files before rebuilding.
    #
    # This ensures that changes to the chunking /
    # metadata structure are reflected.

    if os.path.exists(INDEX_PATH):

        os.remove(
            INDEX_PATH
        )

    if os.path.exists(CHUNKS_PATH):

        os.remove(
            CHUNKS_PATH
        )

    create_index()