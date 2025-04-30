"""
Embedding utility
-----------------
Stateless helper for turning text → embedding vectors via OpenAI’s
`text-embedding-ada-002` (default 1536-dim).

Usage
-----
from app.utils.embedding import embed_text
vec = embed_text("hello world")
"""

from __future__ import annotations

import logging
import time
from typing import List

from fastapi import HTTPException
from openai import OpenAI, OpenAIError

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

client = OpenAI()  # relies on OPENAI_API_KEY in env
_MODEL = "text-embedding-ada-002"
_MAX_RETRIES = 3
_BACKOFF_SEC = 2  # exponential: 2, 4, 8 …

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Public helper
# --------------------------------------------------------------------------- #

def embed_text(text: str, *, model: str = _MODEL) -> List[float]:
    """
    Return the embedding vector for *text*.

    Raises
    ------
    HTTPException(503) if OpenAI is unreachable or returns a non-retryable error.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            res = client.embeddings.create(input=text, model=model)
            return res.data[0].embedding

        except OpenAIError as exc:
            # Log server‐side details, but expose only a generic 503 to the client
            log.warning("OpenAI embedding attempt %d/%d failed: %s",
                        attempt, _MAX_RETRIES, exc)

            # Decide whether to retry
            if attempt == _MAX_RETRIES or not _is_retryable(exc):
                raise HTTPException(
                    status_code=503,
                    detail="Embedding service temporarily unavailable",
                ) from exc

            # Exponential back-off
            time.sleep(_BACKOFF_SEC * 2 ** (attempt - 1))


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _is_retryable(exc: OpenAIError) -> bool:
    """Return True if the error warrants another attempt."""
    # Network/time-out or 5xx responses are usually retryable.
    # The OpenAI SDK exposes `.http_status` for API errors.
    status = getattr(exc, "http_status", None)
    return status is None or 500 <= status < 600
