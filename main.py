import json
import os
import shutil
import time

from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_chroma import Chroma
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate

from injest import injest_files

from db import (
    initialize_database,
    save_message,
    get_chat_history
)

load_dotenv()

app = FastAPI(
    title="Multi Document AI Assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database/table on startup
initialize_database()

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001"
)

llm = ChatMistralAI(
    model="mistral-small-2506"
)


class QueryRequest(BaseModel):
    query: str
    session_id: str


@app.get("/")
def root():
    return {
        "message": "Welcome to the Multi Document AI Assistant. Use the query endpoint to ask questions."
    }


@app.post("/reset")
def reset_database():
    try:
        vector_store = Chroma(
            persist_directory="./chroma_db",
            embedding_function=embedding_model
        )
        vector_store.reset_collection()
    except Exception:
        pass

    if os.path.exists("./documents"):
        try:
            shutil.rmtree("./documents")
        except Exception:
            pass

    os.makedirs("documents", exist_ok=True)

    return {
        "status": "success",
        "message": "Database and documents folder cleared."
    }


@app.post("/upload_files")
async def upload_files(files: list[UploadFile] = File(...)):
    os.makedirs("documents", exist_ok=True)

    uploaded_files = []
    saved_file_paths = []

    for file in files:
        safe_filename = os.path.basename(file.filename)

        file_path = os.path.join(
            "documents",
            safe_filename
        )

        with open(file_path, "wb") as f:
            f.write(await file.read())

        uploaded_files.append(
            {
                "filename": file.filename
            }
        )

        saved_file_paths.append(file_path)

    chunk_count = injest_files(saved_file_paths)

    return {
        "status": "success",
        "uploaded_files": uploaded_files,
        "new_chunks": chunk_count
    }


@app.post("/ask")
def ask_question(request: QueryRequest):

    vector_store = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embedding_model
    )

    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 3}
    )

    search_results = retriever.invoke(request.query)

    context = "\n\n".join(
        [
            doc.page_content
            for doc in search_results
        ]
    )

    # Fetch previous conversation
    history_rows = get_chat_history(
        request.session_id
    )

    history_text = "\n".join(
        [
            f"{role}: {message}"
            for role, message in history_rows
        ]
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a helpful assistant.

Use:
1. Previous conversation history
2. Retrieved document context

Answer only from the document context.

If the answer is not available in the context, respond professionally that you do not have enough information to answer.
"""
            ),
            (
                "human",
                """
Conversation History:
{history}

Document Context:
{context}

Question:
{query}
"""
            )
        ]
    )

    final_prompt = prompt.invoke(
        {
            "history": history_text,
            "context": context,
            "query": request.query
        }
    )

    # Save user question
    save_message(
        request.session_id,
        "user",
        request.query
    )

    response = llm.invoke(final_prompt)

    # Save assistant response
    save_message(
        request.session_id,
        "assistant",
        response.content
    )

    source_chunks = []

    for i, chunk in enumerate(
        search_results,
        start=1
    ):
        source_chunks.append(
            {
                "chunk_number": i,
                "source": chunk.metadata.get(
                    "source",
                    "Unknown"
                ),
                "page": chunk.metadata.get(
                    "page",
                    "Unknown"
                ),
                "content": chunk.page_content
            }
        )

    return {
        "question": request.query,
        "answer": response.content,
        "sources": source_chunks
    }


@app.post("/ask_stream")
def ask_question_stream(request: QueryRequest):
    vector_store = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embedding_model
    )

    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 3}
    )

    search_results = retriever.invoke(request.query)

    context = "\n\n".join(
        [
            doc.page_content
            for doc in search_results
        ]
    )

    # Fetch previous conversation
    history_rows = get_chat_history(
        request.session_id
    )

    history_text = "\n".join(
        [
            f"{role}: {message}"
            for role, message in history_rows
        ]
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a helpful assistant.

Use:
1. Previous conversation history
2. Retrieved document context

Answer only from the document context.

If the answer is not available in the context, respond professionally that you do not have enough information to answer.
"""
            ),
            (
                "human",
                """
Conversation History:
{history}

Document Context:
{context}

Question:
{query}
"""
            )
        ]
    )

    final_prompt = prompt.invoke(
        {
            "history": history_text,
            "context": context,
            "query": request.query
        }
    )

    source_chunks = []
    for i, chunk in enumerate(
        search_results,
        start=1
    ):
        source_chunks.append(
            {
                "chunk_number": i,
                "source": chunk.metadata.get(
                    "source",
                    "Unknown"
                ),
                "page": chunk.metadata.get(
                    "page",
                    "Unknown"
                ),
                "content": chunk.page_content
            }
        )

    def event_generator():
        # Yield sources first
        yield f"event: sources\ndata: {json.dumps(source_chunks)}\n\n"

        full_response = ""
        # Yield tokens from stream
        for chunk in llm.stream(final_prompt):
            token = chunk.content
            full_response += token
            yield f"event: token\ndata: {json.dumps(token)}\n\n"
            time.sleep(0.04)

        # Save user question
        save_message(
            request.session_id,
            "user",
            request.query
        )

        # Save assistant response
        save_message(
            request.session_id,
            "assistant",
            full_response
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )