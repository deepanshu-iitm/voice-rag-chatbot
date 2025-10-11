import fitz  
import os

UPLOAD_DIR = "uploads"
EXTRACTED_DIR = "uploads/extracted"
os.makedirs(EXTRACTED_DIR, exist_ok=True)

def extract_text_and_images(pdf_path):
    doc = fitz.open(pdf_path)
    data = []

    for page_number, page in enumerate(doc, start=1):
        # Extract text
        text = page.get_text()

        # Extract images
        images = []
        for img_index, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_name = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page{page_number}_img{img_index}.{image_ext}"
            image_path = os.path.join(EXTRACTED_DIR, image_name)
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            images.append(image_path)

        data.append({
            "page": page_number,
            "text": text,
            "images": images
        })

    return data
