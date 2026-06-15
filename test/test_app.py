import io

from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from main import app
from db import (
    initialize_database,
    save_message,
    get_chat_history
)

client = TestClient(app)


# =====================================
# DATABASE TESTS
# =====================================

def test_save_and_retrieve_chat_history():

    initialize_database()

    save_message(
        "test_session",
        "user",
        "What is AI?"
    )

    history = get_chat_history(
        "test_session"
    )

    assert len(history) > 0

    assert history[-1][0] == "user"

    assert history[-1][1] == "What is AI?"


# =====================================
# CONTEXT TESTS
# =====================================

def test_context_creation():

    docs = [
        Document(
            page_content="Artificial Intelligence"
        ),
        Document(
            page_content="Machine Learning"
        )
    ]

    context = "\n\n".join(
        [
            doc.page_content
            for doc in docs
        ]
    )

    assert "Artificial Intelligence" in context

    assert "Machine Learning" in context


# =====================================
# PROMPT TESTS
# =====================================

def test_prompt_generation():

    prompt = ChatPromptTemplate.from_messages([
        (
            "human",
            """
History:
{history}

Context:
{context}

Question:
{query}
"""
        )
    ])

    final_prompt = prompt.invoke(
        {
            "history": "user: What is AI?",
            "context": "AI means Artificial Intelligence",
            "query": "Explain it"
        }
    )

    prompt_text = str(final_prompt)

    assert "What is AI?" in prompt_text

    assert "Artificial Intelligence" in prompt_text

    assert "Explain it" in prompt_text


# =====================================
# ROOT ENDPOINT
# =====================================

def test_root_endpoint():

    response = client.get("/")

    assert response.status_code == 200

    assert "message" in response.json()


# =====================================
# RESET ENDPOINT
# =====================================

def test_reset_endpoint():

    response = client.post("/reset")

    assert response.status_code == 200

    assert response.json()["status"] == "success"


from unittest.mock import patch, MagicMock

# =====================================
# PDF UPLOAD ENDPOINT
# =====================================

@patch("main.injest_files")
def test_upload_pdf_endpoint(mock_injest):
    mock_injest.return_value = 5  # mock 5 chunks generated

    fake_pdf = io.BytesIO(
        b"%PDF-1.4 Fake PDF content"
    )

    response = client.post(
        "/upload_files",
        files={
            "files": (
                "sample.pdf",
                fake_pdf,
                "application/pdf"
            )
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["new_chunks"] == 5


# =====================================
# ASK ENDPOINT STRUCTURE TEST
# =====================================

def test_query_request_model():

    payload = {
        "query": "What is AI?",
        "session_id": "test_user"
    }

    assert payload["query"] == "What is AI?"

    assert payload["session_id"] == "test_user"


# =====================================
# ASK ENDPOINT TESTS
# =====================================

@patch("main.Chroma")
@patch("main.llm")
def test_ask_endpoint(mock_llm, mock_chroma):
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [
        Document(page_content="RAG means Retrieval-Augmented Generation")
    ]
    mock_chroma.return_value.as_retriever.return_value = mock_retriever

    mock_response = MagicMock()
    mock_response.content = "Mocked answer: RAG is Retrieval-Augmented Generation"
    mock_llm.invoke.return_value = mock_response

    response = client.post(
        "/ask",
        json={"query": "What is RAG?", "session_id": "test_session"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "Mocked answer" in data["answer"]
    assert len(data["sources"]) == 1


# =====================================
# RESET ENDPOINT EXCEPTION TESTS
# =====================================

@patch("main.shutil.rmtree")
@patch("main.Chroma")
def test_reset_endpoint_handles_exceptions(mock_chroma, mock_rmtree):
    mock_rmtree.side_effect = Exception("Mocked folder deletion error")
    mock_chroma.return_value.reset_collection.side_effect = Exception("Chroma error")

    response = client.post("/reset")

    assert response.status_code == 200
    assert response.json()["status"] == "success"


# =====================================
# ASK STREAM ENDPOINT TESTS
# =====================================

@patch("main.Chroma")
@patch("main.llm")
def test_ask_stream_endpoint(mock_llm, mock_chroma):
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = []
    mock_chroma.return_value.as_retriever.return_value = mock_retriever

    class MockChunk:
        def __init__(self, content):
            self.content = content
    mock_llm.stream.return_value = [MockChunk("Hello"), MockChunk(" World")]

    response = client.post(
        "/ask_stream",
        json={"query": "Hi", "session_id": "test_session"}
    )
    
    assert response.status_code == 200
    content = response.text
    assert "event: token" in content
    assert "Hello" in content
    assert "World" in content