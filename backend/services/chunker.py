from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from services.document_reader import read_file_content

def chunk_files(file_paths):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    
    documents = []
    
    for file_path in file_paths:
        content = read_file_content(file_path)
        
        if not content:
            continue
        
        chunks = text_splitter.split_text(content)
        
        for chunk in chunks:
            doc = Document(
                page_content=chunk,
                metadata={"source": file_path}
            )
            documents.append(doc)
    
    return documents
