from fastapi import APIRouter, HTTPException
from ..schemas.chat import ChatRequest, ChatResponse, Citation
from ..utils.rag import retrieve, build_prompt, answer

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat", response_model=ChatResponse, summary="Query a paper")
async def chat(req: ChatRequest):
    try:
        # ➊  fetch more candidates than we finally need
        chunks = retrieve(req.paper_id, req.query, top_k=20)
    except FileNotFoundError:
        raise HTTPException(404, f"Paper {req.paper_id} not indexed")

    # ➋  cheap heuristic: keep chunks whose clean_text mentions “loss”
    filtered = [
        c for c in chunks
        if "loss" in c.get("clean_text", c["text"]).lower()
    ] or chunks                     # fallback if filter yields nothing

    # ➌  trim back to the 5 best‑scoring survivors
    chunks = filtered[:5]

    prompt  = build_prompt(chunks, req.query)
    raw_ans = answer(req.query, prompt)

    citations = [
        Citation(
            page        = c.get("page_num", c.get("page")),
            textSnippet = c.get("clean_text", c["text"])[:160] + "…"
        )
        for c in chunks
    ]
    return ChatResponse(answer=raw_ans, citations=citations)
