# # app.py
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from backend.analyzer import ask_ai, extract_pdf_text


# app = FastAPI()


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"]
# )


# @app.post("/ask")
# async def ask(
#     question: str = Form(""),
#     conversation_id: str = Form(...),
#     file: UploadFile = File(None)
# ):
#     question = question.strip()

#     if not question and not file:
#         raise HTTPException(
#             status_code=400,
#             detail="Please enter a question or select a document."
#         )

#     document_text = ""
#     filename = ""

#     if file:
#         if not file.filename.lower().endswith(".pdf"):
#             raise HTTPException(
#                 status_code=400,
#                 detail="Only PDF files are supported."
#             )

#         file_content = await file.read()

#         if not file_content:
#             raise HTTPException(
#                 status_code=400,
#                 detail="The uploaded file is empty."
#             )

#         try:
#             document_text = extract_pdf_text(
#                 file_content
#             )

#             filename = file.filename

#         except Exception as error:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Unable to read the PDF: {str(error)}"
#             )

#     try:
#         answer = ask_ai(
#             question,
#             document_text,
#             filename
#         )

#         return {
#             "answer": answer
#         }

#     except Exception as error:
#         raise HTTPException(
#             status_code=500,
#             detail=f"AI response failed: {str(error)}"
#         )

# app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.analyzer import ask_ai
from backend.document_analysis.document_service import (
    analyze_uploaded_pdf,
    format_document_analysis
)


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.post("/ask")
async def ask(
    question: str = Form(""),
    conversation_id: str = Form(...),
    file: UploadFile = File(None)
):
    question = question.strip()

    if not question and not file:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question or select a document."
        )

    # ------------------------------------------------------------
    # NO DOCUMENT
    # ------------------------------------------------------------
    # This keeps the existing text-analysis entry point intact
    # for now. The Gemini text integration will be handled inside
    # the analyzer layer.
    # ------------------------------------------------------------
    if not file:
        try:
            answer = ask_ai(question)

            return {
                "answer": answer
            }

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"AI response failed: {str(error)}"
            )

    # ------------------------------------------------------------
    # DOCUMENT VALIDATION
    # ------------------------------------------------------------
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid file."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    # ------------------------------------------------------------
    # GEMINI DOCUMENT ANALYSIS
    # ------------------------------------------------------------
    try:
        gemini_result, bns_result = analyze_uploaded_pdf(
            file_content,
            file.filename
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to analyze the PDF: {str(error)}"
        )

    # ------------------------------------------------------------
    # DOCUMENT ONLY
    # ------------------------------------------------------------
    # If the user uploaded a document without asking a question,
    # return the document analysis itself.
    # ------------------------------------------------------------
    if not question:
        try:
            answer = format_document_analysis(
                gemini_result
            )

            return {
                "answer": answer
            }

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to format document analysis: {str(error)}"
            )

    # ------------------------------------------------------------
    # DOCUMENT + LEGAL QUESTION
    # ------------------------------------------------------------
    # Gemini only extracts facts.
    #
    # The BNS adapter converts those facts into the structure
    # expected by the existing BNS analysis pipeline.
    #
    # Existing pipeline:
    #
    # BNS facts
    #     ↓
    # legal concepts
    #     ↓
    # BNS RAG
    #     ↓
    # section verifier
    #     ↓
    # section rules
    #     ↓
    # output validator
    #     ↓
    # final answer
    # ------------------------------------------------------------

    if not bns_result.get("bns_relevant", False):
        # The document does not contain sufficiently relevant
        # BNS facts. Do not force it through the BNS pipeline.
        return {
            "answer": format_document_analysis(
                gemini_result
            )
        }

    validation = bns_result.get("validation", {})

    if not validation.get("valid", False):
        raise HTTPException(
            status_code=500,
            detail="The extracted document facts failed BNS validation."
        )

    bns_facts = bns_result.get("facts")

    if not bns_facts:
        raise HTTPException(
            status_code=500,
            detail="No usable BNS facts were extracted from the document."
        )

    try:
        answer = ask_ai(
            question=question,
            document_text="",
            filename=file.filename,
            pre_extracted_facts=bns_facts
        )

        return {
            "answer": answer
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"AI response failed: {str(error)}"
        )
