from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import google.generativeai as genai
import os
from src.web_search import search_web, format_web_results

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("ai-docs")

model = SentenceTransformer("all-MiniLM-L6-v2")

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
genai.configure(api_key="AIzaSyAcEahNIbKQOT2ZooPfd8uJJSIskh6EN4U")

def retrieve_context(query, top_k=5, document_filter=None, min_score=0.3):
    """Search Pinecone for similar chunks, optionally filtered by document"""
    query_emb = model.encode(query).tolist()
    
    # Add document filter if specified
    filter_dict = {}
    if document_filter:
        filter_dict["filename"] = document_filter
    
    results = index.query(
        vector=query_emb, 
        top_k=top_k, 
        include_metadata=True,
        filter=filter_dict if filter_dict else None
    )
    
    contexts = []
    citations = []
    for match in results["matches"]:
        # Only include citations with high relevance scores
        if match["score"] >= min_score:
            meta = match["metadata"]
            contexts.append(meta["text"])
            citations.append({
                "page": meta["page"],
                "images": meta["images"],
                "text": meta["text"],
                "filename": meta.get("filename", "Unknown"),
                "score": match["score"]
            })
    return "\n\n".join(contexts), citations

def generate_answer(query, context):
    """Ask Gemini to answer based on retrieved context"""
    prompt = f"""
You are a helpful document assistant.
Use ONLY the provided context to answer accurately.
If unsure, say you don't know.

Context:
{context}

Question: {query}
Answer:
"""
    response = genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
    return response.text.strip()

def hybrid_search_and_answer(query, include_web=True):
    """
    Combine RAG search with web search for comprehensive answers
    """
    # Get RAG context and citations
    rag_context, rag_citations = retrieve_context(query)
    
    # Get web search results if enabled
    web_results = []
    web_context = ""
    if include_web:
        web_data = search_web(query)
        if not web_data.get("error") and web_data.get("results"):
            web_results = web_data.get("results", [])
            # Format web results for context
            web_context = "\n\nWeb Search Results:\n" + "\n".join([
                f"- {result['title']}: {result['snippet']}" 
                for result in web_results[:3]
            ])
    
    # Combine contexts for AI generation
    combined_context = f"**Document Context:**\n{rag_context}"
    if web_context:
        combined_context += web_context
    
    # Generate answer using combined context
    answer = generate_answer(query, combined_context)
    
    return {
        "answer": answer,
        "rag_citations": rag_citations,
        "web_results": web_results
    }
