from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import google.generativeai as genai
import os

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("ai-docs")

model = SentenceTransformer("all-mpnet-base-v2")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def retrieve_context(query, top_k=5):
    """Search Pinecone for similar chunks"""
    query_emb = model.encode(query).tolist()
    results = index.query(vector=query_emb, top_k=top_k, include_metadata=True)
    contexts = []
    citations = []
    for match in results["matches"]:
        meta = match["metadata"]
        contexts.append(meta["text"])
        citations.append({
            "page": meta["page"],
            "images": meta["images"]
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
