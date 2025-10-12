from fastapi import FastAPI, File, UploadFile
import os
from src.pdf_parser import extract_text_and_images
from src.text_chunker import chunk_text
from src.vector_store import embed_and_store
from src.rag_retriever import retrieve_context, generate_answer

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are allowed."}
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"message": f"File '{file.filename}' uploaded successfully!", "path": file_path}

@app.post("/parse-pdf/")
async def parse_pdf(file_path: str = Form(...)):
    if not os.path.exists(file_path):
        return {"error": "File not found."}

    # Extract text and images
    data = extract_text_and_images(file_path)
    return {"message": f"Parsed {file.filename}", "pages": len(data), "sample_page": data[0]}

@app.post("/chunk-pdf/")
async def chunk_pdf(file_path: str = Form(...)):
    if not os.path.exists(file_path):
        return {"error": "File not found."}

    page_data = extract_text_and_images(file_path)

    chunks = chunk_text(page_data, max_sentences=5)

    return {"num_chunks": len(chunks), "sample_chunk": chunks[0]}

@app.post("/index-pdf/")
async def index_pdf(file_path: str = Form(...)):
    if not os.path.exists(file_path):
        return {"error": "File not found."}

    # Extract + chunk
    page_data = extract_text_and_images(file_path)
    chunks = chunk_text(page_data)

    # Embed + store
    count = embed_and_store(chunks)

    return {"status": "Indexed successfully", "chunks_stored": count}

@app.post("/ask/")
async def ask_question(query: str = Form(...)):
    context, citations = retrieve_context(query)

    answer = generate_answer(query, context)

    return {"answer": answer, "citations": citations}