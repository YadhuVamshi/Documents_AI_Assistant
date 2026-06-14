from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader

# Automatically detects and loads multiple documents
loader = DirectoryLoader("documents", glob="**/*.pdf", loader_cls = PyPDFLoader)
docs = loader.load()

print(f"Loaded {len(docs)} documents for LLM processing.")
print(docs[-1].page_content[:200])