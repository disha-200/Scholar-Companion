from __future__ import annotations
import os, json, pathlib, functools
from typing import Any, List

import faiss, numpy as np
from openai import OpenAI

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
_EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
_LLM_MODEL   = os.getenv("LLM_MODEL",   "gpt-3.5-turbo")

client = OpenAI()

# repo‑root/vector_store
VECTOR_DIR = pathlib.Path(__file__).resolve().parents[3] / "vector_store"

# ------------------------------------------------------------------ #
# Loaders
# ------------------------------------------------------------------ #
@functools.lru_cache(maxsize=8)
def load_index(paper_id: str) -> tuple[faiss.Index, List[dict[str, Any]]]:
    """
    Load a FAISS index **and** its side‑car JSON metadata for one paper.
    Results are cached to avoid disk hits on repeated queries.
    """
    # base = VECTOR_DIR / paper_id                      # e.g. 2504.13079v1
    faiss_path = VECTOR_DIR / f"{paper_id}.faiss"
    meta_path  = VECTOR_DIR / f"{paper_id}.json"
    # print("DEBUG ▶ looking for:", faiss_path, "| exists?", faiss_path.exists())
    # print("DEBUG ▶ vector_dir contents:", list(VECTOR_DIR.glob("*")))
    if not faiss_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Vector store for {paper_id} not found")

    index = faiss.read_index(str(faiss_path))
    meta  = json.loads(meta_path.read_text())
    return index, meta                                # meta[i] = {page_num, text, …}

# ------------------------------------------------------------------ #
# Core helpers
# ------------------------------------------------------------------ #
def embed(text: str) -> np.ndarray:
    """Return a 1‑D float32 numpy vector for `text`."""
    resp = client.embeddings.create(model=_EMBED_MODEL, input=[text])
    return np.asarray(resp.data[0].embedding, dtype="float32")

def retrieve(paper_id: str, query: str, top_k: int = 5) -> List[dict]:
    """ANN search → list[{ page_num, text, score, … }]"""
    index, meta = load_index(paper_id)
    # vec = embed(query)
    vec = embed(query).astype("float32")
    vec /= np.linalg.norm(vec) + 1e-9
    dists, idxs = index.search(np.expand_dims(vec, 0), top_k)
    return [meta[i] | {"score": float(d)} for i, d in zip(idxs[0], dists[0])]

def build_prompt(chunks: List[dict], question: str) -> List[dict]:
    """
    Assemble a 2‑message Chat prompt.

    • Each excerpt is shown as “>>> Page N”.
    • Assistant must answer ONLY from these excerpts.
    • If answer is missing, it must reply exactly ‘I don’t know.’
    • Otherwise answer in ≤ 2 sentences and cite page numbers.
    """
    excerpts = []
    for c in chunks:
        page = c.get("page_num", c.get("page"))
        text = c.get("clean_text", c["text"]).strip()
        excerpts.append(f">>> Page {page}\n{text}")

    context_block = "\n\n".join(excerpts)

    system_msg = (
        "You are an academic assistant. "
        "Answer strictly from the provided excerpts."
    )
    user_msg = (
        "Context (excerpts below):\n\n"
        f"{context_block}\n\n"
        f"Question: {question}\n\n"
        "• If the context does **not** contain the answer, reply exactly: I don’t know.\n"
        "• Otherwise, answer in ≤ 2 sentences and cite the page number(s)."
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": user_msg},
    ]

def answer(question: str, ctx: List[dict]) -> str:
    resp = client.chat.completions.create(
        model=_LLM_MODEL, messages=ctx, temperature=0.2
    )
    return resp.choices[0].message.content
