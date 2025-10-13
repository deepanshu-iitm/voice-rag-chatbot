from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "ai-docs"

if index_name not in [i["name"] for i in pc.list_indexes()]:
    pc.create_index(
        name=index_name,
        dimension=384, 
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(index_name)

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_and_store(chunks, filename=None):
    """
    Takes list of chunks [{"text":..., "page":..., "images":...}, ...]
    Creates embeddings and uploads to Pinecone.
    """
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts).tolist()

    vectors = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        metadata = {
            "page": chunk["page"],
            "text": chunk["text"],
            "images": chunk["images"]
        }
        if filename:
            metadata["filename"] = filename
            
        vectors.append({
            "id": f"chunk-{i}-{filename}" if filename else f"chunk-{i}",
            "values": emb,
            "metadata": metadata
        })

    index.upsert(vectors)
    return len(vectors)
