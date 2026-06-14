# Multi-Document AI Assistant (RAG Pipeline)

A containerized, full-stack Retrieval-Augmented Generation (RAG) application that allows users to upload multiple PDF documents and converse with them. The project features a FastAPI backend, a React/Vite frontend, a Chroma vector store, and a SQLite-based chat history database.

---

## 1. RAG Pipeline Architecture

Below is a diagram illustrating the ingestion and query-response flows in this application:

### Ingestion Flow (PDF Upload & Indexing)
```
[User Uploads PDFs]
         │
         ▼
[FastAPI /upload_pdf]
         │
         ▼
[PyPDFLoader (Extract Text)]
         │
         ▼
[RecursiveCharacterTextSplitter] (Chunk Size: 1000, Overlap: 200)
         │
         ▼
[Google Gemini Embeddings] (models/gemini-embedding-001)
         │
         ▼
[Chroma Vector Store] (Persisted to ./chroma_db)
```

### Retrieval & Query Flow
```
               [User Question & Session ID]
                            │
                            ▼
                     [FastAPI /ask]
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
 [Retrieve top 3 chunks]            [Fetch last 6 messages]
    (Chroma MMR Search)               (SQLite chat_history)
            │                               │
            └───────────────┬───────────────┘
                            ▼
           [Construct ChatPromptTemplate]
                            │
                            ▼
                [Mistral AI LLM Call] (mistral-small-2506)
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
 [Save user message to DB]      [Save response to DB]
            │                               │
            └───────────────┬───────────────┘
                            ▼
                [Return JSON Response]
                  - Answer
                  - Retrieved Source Page & Chunks
```

---

## 2. Setup and Run Instructions

### Option A: Using Docker (Recommended)
This method runs the backend and frontend in isolated containers and handles all installation automatically.

#### 1. Prerequisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) on your machine.

#### 2. Configuration
- Create a `.env` file in the root directory:
  ```env
  GOOGLE_API_KEY = "your_google_gemini_api_key"
  MISTRAL_API_KEY = "your_mistral_api_key"
  ```
  *(You can copy and rename `.env.example` as a template).*

#### 3. Start the Application
Open a terminal in the project directory and run:
```bash
docker compose up --build
```
This builds both container images and runs them. Once started:
* **Frontend UI**: Open your browser at **[http://localhost:5173](http://localhost:5173)**
* **Backend API Docs**: Open your browser at **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

### Option B: Local Running (Without Docker)
If you want to run the project directly on your host machine.

#### 1. Prerequisites
- **Python 3.11** installed.
- **Node.js 20+** and npm installed.

#### 2. Backend Setup
1. Open a terminal in the root directory.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

#### 3. Frontend Setup
1. Open a new terminal in the `frontend` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
4. Access the UI at `http://localhost:5173`.

---

## 3. Key Design Choices

### 1. Vector Database: Chroma DB
- **Why**: Chroma is a serverless, in-process vector database that requires zero configuration to deploy, making it highly portable. It works natively with LangChain and persists its data inside a local directory (`./chroma_db`), which we mount inside a Docker volume so your indexed documents survive container rebuilds.
- **Search Type**: Maximum Marginal Relevance (MMR) retrieval. MMR balances retrieving highly relevant documents with retrieving *diverse* information, reducing redundancy in the LLM prompt context.

### 2. Embedding Model: Google Gemini (`models/gemini-embedding-001`)
- **Why**: Google's Gemini embedding model is highly performant and cost-effective. It accurately encodes semantic relationships across large segments of text (up to 2048 dimensions).

### 3. LLM: Mistral AI (`mistral-small-2506`)
- **Why**: Mistral Small strikes an optimal balance between low latency, cost-efficiency, and reasoning capability. It excels at adhering to strict RAG constraints (such as answering strictly from the provided context or declining if the info is missing).

### 4. Memory/Session Storage: SQLite (`chat_memory.db`)
- **Why**: SQLite runs as a local database file, ensuring chat sessions are persisted across page reloads without requiring an external database cluster like Redis or PostgreSQL. It handles multi-turn conversation memory by fetching the last 6 messages of the user's active session.

---

## 4. Known Limitations & Future Improvements

### Current Limitations:
1. **File-Bound Database**: SQLite database lock issues can occur under high user concurrency.
2. **Local Vector Database**: Chroma DB runs inside the container process. If you scale the backend to multiple instances, they will not share vector space without a separate central vector database.
3. **Scanned PDF Limitations**: The current `PyPDFLoader` reads text layers. Scanned PDF documents (images of text) will not be indexed properly.
4. **Coarse-Grained Chunking**: Fixed-size text splitting can occasionally slice paragraphs in half, separating key context.

### Future Improvements:
1. **Production Databases**: Migrate SQLite to PostgreSQL (or Redis) for session storage, and Chroma to a standalone service like Qdrant, Pinecone, or PGVector.
2. **OCR Integration**: Implement `pytesseract` or an OCR tool to read scanned PDF documents.
3. **Hybrid Search & Re-ranking**: Use a combination of BM25 (keyword search) and Dense Vector Search (Chroma), then filter results through a Cohere or SentenceTransformers Re-ranker to maximize context relevance.
4. **Document Metadata Management**: Enable users to view, delete, or choose specific documents to query against, rather than querying the entire uploaded corpus.

---

## 5. Assumptions Made
1. **Network Connectivity**: The container has stable outbound network access to connect to external LLM/Embedding API endpoints (Google, Mistral).
2. **Text-Based Documents**: The user uploads standard PDF documents containing selectable text.
3. **Short Sessions**: Storing the last 6 messages (limit=6) is sufficient to maintain standard conversation flow while avoiding prompt token bloat.
4. **Database Persistency**: The local folder directories are not deleted, allowing mapped Docker volumes to mount SQLite (`chat_memory.db`) and Chroma (`chroma_db/`) successfully.
