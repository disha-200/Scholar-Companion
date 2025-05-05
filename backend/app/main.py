from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from .routes import chat
import pdfplumber
# from pdfplumber.pdfminer.pdfparser import PDFSyntaxError
from pdfminer.pdfparser import PDFSyntaxError
import os
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from dotenv import load_dotenv            # ⬅ pip install python-dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")

app = FastAPI()
app.include_router(chat.router)
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


MAX_BYTES = 10 * 1024 * 1024 # 10MB

# === Add CORS middleware immediately after creating your app ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your Next.js origin
    allow_methods=["*"],
    allow_headers=["*"],
)

async def save_file_with_limit(upload: UploadFile, dest_path: str, limit: int):
    """Read the incoming file in chunks and stop if we exceed `limit`."""
    total = 0
    with open(dest_path, "wb") as out_file:
        while True:
            chunk = await upload.read(1024 * 512)  # 512 KiB chunks
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                # Clean up partial write
                out_file.close()
                os.remove(dest_path)
                raise HTTPException(413, f"File exceeds {limit//(1024*1024)} MiB limit")
            out_file.write(chunk)


# === Now define your endpoints ===
@app.post("/upload")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    # (Optional) preflight header check
    cl = request.headers.get("content-length")
    if cl and int(cl) > MAX_BYTES:
        raise HTTPException(413, "File too large")

    # 1. Validate extension & MIME
    if file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed")
    
    # 1.1 Quick “magic header” check
    header = await file.read(5)
    await file.seek(0)
    if header != b"%PDF-":
        raise HTTPException(400, "Invalid PDF signature")

    # 2. Stream-save with size enforcement
    dest = os.path.join(UPLOAD_DIR, file.filename)
    await save_file_with_limit(file, dest, MAX_BYTES)

    # 3. Extract text per page
    pages = []
    try:
        with pdfplumber.open(dest) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                pages.append({"page": i, "text": page.extract_text() or ""})
    except PDFSyntaxError:
        raise HTTPException(422, "Malformed PDF—could not parse")
    except Exception as e:
        # log for your own diagnostics, then:
        raise HTTPException(500, "Unexpected error reading PDF")

    # 4. Return JSON
    return {"filename": file.filename, "pages": pages}


