import nltk
nltk.download("punkt_tab")
from nltk.tokenize import sent_tokenize

def chunk_text(page_data, max_sentences=5):
    """
    page_data: List of dictionaries like [{'page': 1, 'text': '...', 'images': [...]}, ...]
    Returns: list of chunks with page number
    """
    chunks = []

    for page in page_data:
        sentences = sent_tokenize(page["text"])
        for i in range(0, len(sentences), max_sentences):
            chunk_text = " ".join(sentences[i:i+max_sentences])
            chunks.append({
                "text": chunk_text,
                "page": page["page"],
                "images": page["images"]
            })

    return chunks
