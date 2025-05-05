#!/usr/bin/env python3
"""
Build *per‑paper* FAISS indices.

$ python scripts/index_papers.py               # defaults to backend/uploads
$ python scripts/index_papers.py --dir docs/

Outputs
-------
vector_store/<paperId>.faiss   (binary FAISS)
vector_store/<paperId>.json    (chunk‑level metadata)
"""

from __future__ import annotations

import argparse, json, logging, os, sys
from pathlib import Path

# ─── allow `import app.*` ────────────────────────────────────────────
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from dotenv import load_dotenv          # pip install python-dotenv
load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")

import faiss
import numpy as np
import pdfplumber
from tqdm import tqdm

from app.utils.chunker import chunk_page
from app.utils.embedding import embed_text

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
DIM = 1536                                   # ada‑002 vector size
VECTOR_DIR = Path(__file__).resolve().parents[1] / "vector_store"
VECTOR_DIR.mkdir(exist_ok=True)

logging.getLogger("pdfminer.pdfpage").setLevel(logging.ERROR)

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def index_single_pdf(pdf_path: Path) -> None:
    """Create FAISS + metadata files for one PDF."""
    # index = faiss.IndexIDMap(faiss.IndexFlatL2(DIM))
    index = faiss.IndexIDMap(faiss.IndexFlatIP(DIM))
    metadata: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            for chunk in chunk_page(page, page_num=page_num):
                clean = chunk["text"]
                # vec = np.asarray(embed_text(chunk["text"]), dtype="float32")[None, :]
                vec = np.asarray(embed_text(clean), dtype="float32")          # 1‑D
                vec /= np.linalg.norm(vec) + 1e-9                             # unit length
                vec = vec[None, :]                                            # 2‑D for FAISS
                id_ = len(metadata)
                index.add_with_ids(vec, np.array([id_], dtype="int64"))
                # metadata.append({**chunk, "id": id_, "pdf_name": pdf_path.name})
                metadata.append({
        **chunk,                # keeps page_num, chunk_idx, tokens, *raw text*
        "id"       : id_,
        "pdf_name" : pdf_path.name,
        "clean_text": clean     # ➊  NEW FIELD
    })

    # ---------- persist with FULL stem (including dots) ----------
    paper_id  = pdf_path.name.removesuffix(".pdf")   # keeps 2504.13079v1
    faiss_path = VECTOR_DIR / f"{paper_id}.faiss"
    meta_path  = VECTOR_DIR / f"{paper_id}.json"

    faiss.write_index(index, str(faiss_path))
    meta_path.write_text(json.dumps(metadata, indent=2))

    print(f"✅  {pdf_path.name:<30} → {len(metadata):>5} vectors  ({faiss_path.name})")

# ------------------------------------------------------------------ #
# CLI
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    default_dir = Path(__file__).resolve().parents[1] / "backend" / "uploads"

    parser = argparse.ArgumentParser(description="Embed & index all PDFs in a folder")
    parser.add_argument(
        "--dir", type=Path, default=default_dir,
        help=f"PDF directory (default: {default_dir})",
    )
    args = parser.parse_args()

    pdfs = sorted(args.dir.glob("*.pdf"))
    if not pdfs:
        print(f"⛔ No PDFs found in {args.dir}")
        raise SystemExit(1)

    with tqdm(total=len(pdfs), desc="Indexing", unit="pdf") as bar:
        for pdf in pdfs:
            index_single_pdf(pdf)
            bar.update(1)
