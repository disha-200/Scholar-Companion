#!/usr/bin/env python3
"""
Build a FAISS index from all PDFs in a directory.

$ python scripts/index_papers.py               # defaults to backend/uploads
$ python scripts/index_papers.py --dir docs/   # custom directory

Outputs
-------
vector_store/vector.index       (binary FAISS file)
vector_store/vector_meta.json   (chunk-level metadata)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import faiss
import numpy as np
import pdfplumber
from tqdm import tqdm

from app.utils.chunker import chunk_page
from app.utils.embedding import embed_text

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

DIM = 1536                             # ada-002 output size
VECTOR_DIR = Path(__file__).resolve().parents[1] / "vector_store"
VECTOR_DIR.mkdir(exist_ok=True)

# --------------------------------------------------------------------------- #
# Index helpers
# --------------------------------------------------------------------------- #

def index_single_pdf(pdf_path: Path, index: faiss.Index, meta_store: list) -> None:
    """Chunk + embed one PDF and append data to the FAISS index and metadata list."""
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            for chunk in chunk_page(page, page_num):
                vec = np.asarray(embed_text(chunk["text"]), dtype="float32").reshape(1, -1)

                id_ = len(meta_store)          # next integer ID
                index.add_with_ids(vec, np.array([id_]))
                meta_store.append({**chunk, "pdf_name": pdf_path.name})


def build_index(root: Path) -> None:
    pdfs = list(root.glob("*.pdf"))
    print(f"🗂  Found {len(pdfs)} PDF(s) in {root}")

    if not pdfs:
        return

    faiss_index = faiss.IndexFlatL2(DIM)
    metadata: list[dict] = []

    with tqdm(total=len(pdfs), desc="Indexing", unit="pdf") as bar:
        for pdf in pdfs:
            index_single_pdf(pdf, faiss_index, metadata)
            bar.update(1)

    # ---------- persist ----------
    faiss_path = VECTOR_DIR / "vector.index"
    meta_path = VECTOR_DIR / "vector_meta.json"

    faiss.write_index(faiss_index, str(faiss_path))
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅  {faiss_index.ntotal} vectors  →  {faiss_path}")
    print(f"✅  {len(metadata)} metadata rows →  {meta_path}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    default_dir = Path(__file__).resolve().parents[1] / "backend" / "uploads"

    parser = argparse.ArgumentParser(description="Embed & index all PDFs in a folder")
    parser.add_argument(
        "--dir",
        type=Path,
        default=default_dir,
        help=f"PDF directory (default: {default_dir})",
    )
    args = parser.parse_args()

    build_index(args.dir)
