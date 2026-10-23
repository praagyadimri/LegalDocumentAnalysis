# BNS Legal Document Analysis & RAG Chatbot

An AI-powered legal analysis system that helps users identify relevant sections of the **Bharatiya Nyaya Sanhita (BNS), 2023** from natural-language legal queries and uploaded documents.

The system combines **Retrieval-Augmented Generation (RAG)**, **FAISS**, **MiniLM embeddings**, and a local **Qwen LLM** with a deterministic verification layer to reduce unsupported or incorrect legal sections in the final response.

## Features

- 🔍 Natural-language legal query analysis
- 📄 Uploaded PDF document analysis
- ⚖️ BNS 2023 section retrieval
- 🧠 AI-based legal fact extraction
- 📚 RAG-based retrieval using FAISS
- 🔎 MiniLM-based semantic search
- 🤖 Local Qwen LLM for reasoning and analysis
- ✅ Deterministic section verification
- 🛡️ Validation layer to prevent unsupported sections
- 💬 Chat interface with conversation history

## How It Works

```text
User Question / Uploaded PDF
            ↓
     Document Processing
            ↓
      Fact Extraction
            ↓
    Legal Concept Detection
            ↓
   BNS Section Retrieval
            ↓
    FAISS + MiniLM Search
            ↓
       Qwen Analysis
            ↓
   Deterministic Verification
            ↓
      Output Validation
            ↓
       Final BNS Analysis
```

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Python | Backend and AI processing |
| FastAPI | Backend API |
| FAISS | Fast similarity search for BNS sections |
| MiniLM | Text embeddings for semantic retrieval |
| Qwen | Local LLM for legal reasoning |
| Ollama | Running the local Qwen model |
| PyPDF | PDF text extraction |
| HTML/CSS/JavaScript | Frontend |
| BNS 2023 | Legal knowledge base |

## Retrieval-Augmented Generation (RAG)

The system uses RAG to retrieve relevant sections from the BNS knowledge base before generating the final legal analysis.

Instead of relying only on the language model's internal knowledge, the system first searches the indexed BNS content for relevant sections.

### RAG Pipeline

```text
Legal Query
    ↓
MiniLM Embedding
    ↓
FAISS Similarity Search
    ↓
Relevant BNS Sections
    ↓
Qwen Analysis
    ↓
Verified Legal Response
```

### FAISS

**FAISS (Facebook AI Similarity Search)** is used to efficiently search the BNS section embeddings and retrieve the most relevant legal sections for a given query.

### MiniLM

**MiniLM** converts the legal query and BNS text into numerical vector representations called embeddings. These embeddings allow the system to find semantically similar legal sections even when the wording of the query differs from the wording in the BNS.

## Legal Verification

A major component of the system is the deterministic verification and validation layer.

The retrieved sections are not directly shown to the user. Instead, they are checked against the facts extracted from the query or uploaded document.

```text
Retrieved Sections
        ↓
Fact-Based Verification
        ↓
Unsupported Sections Removed
        ↓
Rule-Based Validation
        ↓
Final Legal Analysis
```

This helps reduce:

- Unsupported section recommendations
- Irrelevant sections
- Duplicate sections
- Sections based only on keyword matching
- Hallucinated legal facts

## Project Structure

```text
DMBS_Latest_RAG/
│
├── backend/
│   ├── app.py
│   ├── rag.py
│   ├── analyzer.py
│   ├── document_rag.py
│   ├── section_verifier.py
│   └── section_rules.py
│
├── reference/
│   ├── legal_handbook.pdf
│   ├── legal_index.faiss
│   └── legal_chunks.pkl
│
├── .env
├── index_latest.html
└── README.md
```

## Main Components

### `app.py`

Handles the FastAPI backend and communication between the frontend and the legal analysis pipeline.

### `rag.py`

Responsible for:

- Loading the BNS legal handbook
- Creating text chunks
- Generating embeddings
- Building the FAISS index
- Retrieving relevant BNS sections

### `analyzer.py`

Handles the main legal analysis pipeline, including:

- Fact extraction
- Legal concept identification
- Candidate section generation
- LLM-based analysis
- Final response generation

### `document_rag.py`

Handles uploaded document processing and extracts legally relevant information from PDF documents before passing the information to the existing BNS analysis pipeline.

### `section_verifier.py`

Checks whether retrieved BNS sections are actually supported by the facts provided by the user.

### `section_rules.py`

Contains deterministic legal rules used to prioritize, reject, or remove sections based on the established facts.

## Running the Project

### 1. Clone the Repository

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd DMBS_Latest_RAG
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Ollama

Make sure Ollama is installed and running.

Pull the required model:

```bash
ollama pull qwen3:8b
```

The project uses the local Ollama API to communicate with Qwen.

### 5. Start the FastAPI Server

From the project root:

```bash
uvicorn backend.app:app --reload
```

The backend will start at:

```text
http://127.0.0.1:8000
```

### 6. Open the Frontend

Open:

```text
index_latest.html
```

in your browser and use the chatbot to submit legal queries or upload supported PDF documents.

## Example

### Input

```text
A stabbed B with the intention of causing his death, resulting in B's death.
```

### Analysis

The system extracts the relevant facts, retrieves applicable BNS sections, verifies them against the facts, and generates a final response containing only the sections supported by the given circumstances.

## Important Design Principle

The system follows a **fact-first approach**.

It does not treat every retrieved section as automatically applicable. Retrieved sections are treated as candidates and are subsequently verified using the extracted facts and deterministic legal rules.

```text
Retrieval ≠ Final Answer

Retrieval
   ↓
Candidate Sections
   ↓
Verification
   ↓
Validation
   ↓
Final Answer
```

## Current Limitations

- Legal analysis depends on the quality and completeness of the provided facts.
- The system is designed as an academic/project prototype and should not be treated as a substitute for professional legal advice.
- Complex cases may require interpretation beyond automated analysis.
- The quality of document analysis depends on the text extracted from the uploaded PDF.

## Future Scope

- Improve legal document understanding
- Support additional Indian laws and legal databases
- Improve multilingual and Hindi legal-text handling
- Add citation-level references to source documents
- Improve retrieval accuracy
- Add stronger legal reasoning and contradiction detection
- Deploy the system as a web application
- Add authentication and secure document storage

## Project Outcome

The project demonstrates how **RAG, vector search, local LLMs, and deterministic verification** can be combined to build a more controlled AI-based legal analysis system.

The key objective is to retrieve relevant BNS provisions while reducing unsupported legal sections through a separate verification and validation layer.

## Disclaimer

This project is developed for **educational and research purposes**. The generated analysis should not be considered professional legal advice. Users should consult a qualified legal professional for actual legal matters.

## Authors

**Praagya Dimri**

B.Tech Computer Science & Engineering  
Amity University

---

⭐ If you find this project useful, consider giving the repository a star.
