"""NLP application layer — use cases."""

from __future__ import annotations

from stratos_nlp.domain.entities import NarrativeShift, SentimentResult, Sentiment
from stratos_nlp.domain.ports import DocumentRetriever, EntityExtractor, SentimentScorer


class ScoreSentimentUseCase:
    def __init__(self, scorer: SentimentScorer) -> None:
        self._scorer = scorer

    async def execute(self, text: str) -> SentimentResult:
        score = self._scorer.score(text)
        sentiment = Sentiment.POSITIVE if score > 0.1 else Sentiment.NEGATIVE if score < -0.1 else Sentiment.NEUTRAL
        return SentimentResult(text=text[:100], sentiment=sentiment, score=score, model="default")


class ParseEarningsUseCase:
    def __init__(self, extractor: EntityExtractor) -> None:
        self._extractor = extractor

    async def execute(self, transcript: str) -> list[dict[str, str]]:
        return self._extractor.extract(transcript)


class RetrieveContextUseCase:
    def __init__(self, retriever: DocumentRetriever) -> None:
        self._retriever = retriever

    async def execute(self, query: str, top_k: int = 5) -> list[dict]:
        return self._retriever.retrieve(query, top_k=top_k)
