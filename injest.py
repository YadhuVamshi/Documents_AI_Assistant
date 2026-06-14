from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()


# Loads a list of PDF files and embeds them
def injest_files(file_paths: list[str]):
    all_documents = []
    for path in file_paths:
        loader = PyPDFLoader(path)
        all_documents.extend(loader.load())

    if not all_documents:
        return 0

    # Chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(all_documents)

    if not chunks:
        return 0
        
    # Embeddings
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    vector_store = Chroma.from_documents(documents = chunks, embedding = embedding_model, persist_directory="./chroma_db")

    return len(chunks)