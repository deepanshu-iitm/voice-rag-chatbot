from fastapi import FastAPI, File, UploadFile, Form, WebSocket, WebSocketDisconnect
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
from src.deepgram_service import deepgram_service

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
            # Search for the text on the page
            text_instances = page.search_for(highlight_text.strip())
            
            # Highlight each instance with yellow
            for inst in text_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(stroke=[1, 1, 0])  # Yellow highlight
                highlight.update()
        
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

@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """WebSocket endpoint for real-time Deepgram transcription"""
    await websocket.accept()
    
    try:
        # Start Deepgram live transcription
        success = await deepgram_service.start_live_transcription(websocket)
        
        if not success:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Failed to start Deepgram transcription"
            }))
            return
        
        # Listen for audio data from frontend
        while True:
            try:
                # Receive audio data from frontend
                data = await websocket.receive_bytes()
                
                # Send audio data to Deepgram
                await deepgram_service.send_audio_data(data)
                
            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
                break
    
    except Exception as e:
        print(f"WebSocket connection error: {e}")
    
    finally:
        # Clean up Deepgram connection
        await deepgram_service.stop_live_transcription()

@app.post("/transcribe-audio/")
async def transcribe_audio_file(file: UploadFile = File(...)):
    """Transcribe uploaded audio file using Deepgram"""
    try:
        # Save uploaded audio file temporarily
        temp_audio_path = f"temp_audio_{file.filename}"
        with open(temp_audio_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Transcribe using Deepgram
        result = await deepgram_service.transcribe_file(temp_audio_path)
        
        # Clean up temporary file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        
        if result:
            return {
                "transcript": result["transcript"],
                "confidence": result["confidence"],
                "success": True
            }
        else:
            return {"error": "Failed to transcribe audio", "success": False}
            
    except Exception as e:
        return {"error": f"Audio transcription failed: {str(e)}", "success": False}