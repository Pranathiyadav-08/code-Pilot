from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os

VECTOR_STORE_PATH = "vector_store/faiss_index"

_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
    return _embeddings

def create_vector_store(documents):
    if not documents:
        return None
    
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(documents, embeddings)
    
    os.makedirs("vector_store", exist_ok=True)
    vector_store.save_local(VECTOR_STORE_PATH)
    
    return vector_store

def load_vector_store():
    if not os.path.exists(VECTOR_STORE_PATH):
        return None
    
    embeddings = get_embeddings()
    vector_store = FAISS.load_local(
        VECTOR_STORE_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )
    
    return vector_store
