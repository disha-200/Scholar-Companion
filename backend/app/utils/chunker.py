"""
Chunker utility
===============

Splits raw page text from PDFs into ~`max_tokens` sized chunks using the same
tokenizer OpenAI uses (`cl100k_base`).  An optional overlap keeps context
flowing between chunks.

Key public helpers
------------------
- `chunk_text`
- `chunk_page`
- `chunk_pdf`

All functions are pure / side-effect-free so they can be reused from CLI
scripts or FastAPI endpoints.

Author: you 🚀
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import tiktoken

try:
    import pdfplumber  # only needed for `chunk_pdf`
except ImportError:    # pragma: no cover
    pdfplumber = None  # allows importing this module without pdfplumber


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

ENCODER = tiktoken.get_encoding("cl100k_base")
DEFAULT_MAX_TOKENS = 500
DEFAULT_OVERLAP = 50


# --------------------------------------------------------------------------- #
# Core helpers
# --------------------------------------------------------------------------- #

def _encode(text: str) -> List[int]:
    """Return token IDs for `text` using the global encoder."""
    return ENCODER.encode(text, disallowed_special=[])


def _decode(token_ids: List[int]) -> str:
    """Inverse of `_encode`"""
    return ENCODER.decode(token_ids)


def chunk_text(
    text: str,
    *,
    page_num: int,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap: int = DEFAULT_OVERLAP,
) -> List[Dict]:
    """
    Split a *single page's* raw text into token-bounded chunks.

    Parameters
    ----------
    text : str
        Raw page text.
    page_num : int
        1-indexed page number (used in metadata).
    max_tokens : int, default 500
        Target upper-bound for each chunk.
    overlap : int, default 50
        Number of tokens caried over to the next chunk.

    Returns
    -------
    list[dict]
        Dicts with keys ``text``, ``page_num``, ``chunk_idx``, ``tokens``.
    """
    token_ids = _encode(text)
    chunks: List[Dict] = []

    start = 0
    chunk_idx = 0
    n_tokens = len(token_ids)

    if n_tokens == 0:  # empty / blank page
        return chunks

    # Sanity-check overlap
    overlap = min(overlap, max_tokens // 2)

    while start < n_tokens:
        end = min(start + max_tokens, n_tokens)
        tokens_slice = token_ids[start:end]

        chunk = {
            "text": _decode(tokens_slice),
            "page_num": page_num,
            "chunk_idx": chunk_idx,
            "tokens": len(tokens_slice),
        }
        chunks.append(chunk)

        chunk_idx += 1
        next_start = end - overlap
        start = next_start if next_start > start else end   # guarantees progress

    return chunks


def chunk_page(page_obj, *, page_num: int, **kwargs) -> List[Dict]:
    """
    Convenience wrapper for a *pdfplumber* Page object.

    Cleans up weird spacing, then delegates to `chunk_text`.
    """
    # 1️⃣  Pull text with slightly tighter x/y tolerances
    text = page_obj.extract_text(x_tolerance=1, y_tolerance=2) or ""

    # 2️⃣  Collapse all whitespace (keeps single spaces, removes newlines & doubles)
    text = " ".join(text.split())

    return chunk_text(text, page_num=page_num, **kwargs)


def chunk_pdf(
    pdf_path: Path | str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap: int = DEFAULT_OVERLAP,
) -> List[Dict]:
    """
    High-level helper: iterate every page of a PDF and aggregate chunks.

    Requires **pdfplumber**.  Heavy lifting is still delegated to `chunk_text`.
    """
    if pdfplumber is None:  # pragma: no cover
        raise ImportError("pdfplumber is required for chunk_pdf()")

    pdf_path = Path(pdf_path)
    chunks: List[Dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            chunks.extend(
                chunk_page(
                    page,
                    page_num=page_num,
                    max_tokens=max_tokens,
                    overlap=overlap,
                )
            )

    return chunks


# --------------------------------------------------------------------------- #
# Quick smoke test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":  # pragma: no cover
    from argparse import ArgumentParser
    import json

    ap = ArgumentParser(description="Chunk a PDF and print stats")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--max", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
    args = ap.parse_args()

    all_chunks = chunk_pdf(args.pdf, max_tokens=args.max, overlap=args.overlap)
    print(f"✅  Produced {len(all_chunks)} chunks")
    print(json.dumps(all_chunks[0], indent=2))
