from pydantic import Field
from .base import CamelModel          

class ChatRequest(CamelModel):
    paper_id: str = Field(..., alias="paperId")
    query: str

class Citation(CamelModel):
    page: int
    text_snippet: str = Field(..., alias="textSnippet")

class ChatResponse(CamelModel):
    answer: str
    citations: list[Citation]
