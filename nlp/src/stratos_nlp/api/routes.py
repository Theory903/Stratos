"""NLP API routes."""

from fastapi import APIRouter

router = APIRouter(tags=["NLP"])


@router.post("/sentiment/score")
async def score_sentiment(text: str = "") -> dict:
    return {"status": "not_implemented"}


@router.post("/earnings/parse")
async def parse_earnings() -> dict:
    return {"status": "not_implemented"}


@router.post("/rag/query")
async def rag_query(query: str = "") -> dict:
    return {"status": "not_implemented"}


@router.post("/narrative/detect")
async def detect_narrative() -> dict:
    return {"status": "not_implemented"}
