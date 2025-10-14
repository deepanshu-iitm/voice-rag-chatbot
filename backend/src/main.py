from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import fitz  
from PIL import Image, ImageDraw
import io
import re
import json
import asyncio
from src.pdf_parser import extract_text_and_images
from src.text_chunker import chunk_text
from src.vector_store import embed_and_store
from src.rag_retriever import retrieve_context, generate_answer, hybrid_search_and_answer
# Deepgram service removed - using Web Speech API in frontend

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
HIGHLIGHTED_DIR = "highlighted_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(HIGHLIGHTED_DIR, exist_ok=True)

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
    return {"message": f"Parsed {os.path.basename(file_path)}", "pages": len(data), "sample_page": data[0]}

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

    # Embed + store with filename
    filename = os.path.basename(file_path)
    count = embed_and_store(chunks, filename=filename)

    return {"status": "Indexed successfully", "chunks_stored": count}

@app.post("/ask/")
async def ask_question(query: str = Form(...)):
    context, citations = retrieve_context(query)

    answer = generate_answer(query, context)

    return {"answer": answer, "citations": citations}

@app.post("/ask-hybrid/")
async def ask_hybrid_question(query: str = Form(...), include_web: bool = Form(True)):
    """
    Ask a question using both RAG search and web search
    """
    result = hybrid_search_and_answer(query, include_web=include_web)
    
    return {
        "query": query,
        "answer": result["answer"],
        "rag_citations": result["rag_citations"],
        "web_results": result["web_results"]
    }

@app.get("/pdf-page-image/{filename}/{page_num}")
async def get_pdf_page_image(filename: str, page_num: int):
    """Serve a specific page of a PDF as an image"""
    try:
        pdf_path = os.path.join("uploads", filename)
        if not os.path.exists(pdf_path):
            return {"error": f"PDF file {filename} not found"}
        
        # Open PDF and get the specific page
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            return {"error": f"Page {page_num} not found in {filename}"}
        
        page = doc[page_num - 1]  # fitz uses 0-based indexing
        
        # Render page as image
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        doc.close()
        
        # Save PDF page image to dedicated folder
        safe_filename = filename.replace(".pdf", "").replace(" ", "_")
        page_filename = f"{safe_filename}_page_{page_num}.png"
        page_path = os.path.join(HIGHLIGHTED_DIR, page_filename)
        
        with open(page_path, "wb") as f:
            f.write(img_data)
        
        return FileResponse(page_path, media_type="image/png", filename=page_filename)
        
    except Exception as e:
        return {"error": f"Failed to get PDF page image: {str(e)}"}

@app.get("/pdf-page-highlighted/{filename}/{page_num}")
async def get_pdf_page_highlighted(filename: str, page_num: int, highlight_text: str = ""):
    """Serve a PDF page with specific text highlighted in yellow"""
    try:
        pdf_path = os.path.join("uploads", filename)
        if not os.path.exists(pdf_path):
            return {"error": f"PDF file {filename} not found"}
        
        # Open PDF and get the specific page
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            return {"error": f"Page {page_num} not found in {filename}"}
        
        page = doc[page_num - 1]  # fitz uses 0-based indexing
        
        # If highlight text is provided, search and highlight it
        if highlight_text.strip():
            search_text = highlight_text.strip()
            
            # Try multiple search strategies for better accuracy
            text_instances = []
            
            # Strategy 1: Exact phrase search
            exact_matches = page.search_for(search_text)
            text_instances.extend(exact_matches)
            
            # Strategy 2: If no exact matches and text is long, try first few words
            if not exact_matches and len(search_text.split()) > 3:
                first_words = ' '.join(search_text.split()[:3])
                partial_matches = page.search_for(first_words)
                text_instances.extend(partial_matches)
            
            # Strategy 3: If still no matches, try individual significant words (>3 chars)
            if not text_instances:
                words = [word for word in search_text.split() if len(word) > 3]
                for word in words[:2]:  # Only try first 2 significant words
                    word_matches = page.search_for(word)
                    text_instances.extend(word_matches)
            
            # Remove duplicates by converting to set of tuples and back
            unique_instances = []
            seen_rects = set()
            for inst in text_instances:
                rect_tuple = (inst.x0, inst.y0, inst.x1, inst.y1)
                if rect_tuple not in seen_rects:
                    seen_rects.add(rect_tuple)
                    unique_instances.append(inst)
            
            # Highlight each unique instance with yellow
            for inst in unique_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(stroke=[1, 1, 0])  # Yellow highlight
                highlight.update()
                
            print(f"Highlighted {len(unique_instances)} instances of text: '{search_text}'")
        
        # Render page as image with highlights
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        doc.close()
        
        # Save highlighted image to dedicated folder
        safe_filename = filename.replace(".pdf", "").replace(" ", "_")
        highlighted_filename = f"{safe_filename}_page_{page_num}_highlighted.png"
        highlighted_path = os.path.join(HIGHLIGHTED_DIR, highlighted_filename)
        
        with open(highlighted_path, "wb") as f:
            f.write(img_data)
        
        return FileResponse(highlighted_path, media_type="image/png", filename=highlighted_filename)
        
    except Exception as e:
        return {"error": f"Failed to get highlighted PDF page: {str(e)}"}

