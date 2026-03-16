"""Tests for NLP adapters."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from stratos_nlp.domain.entities import SentimentLabel, SentimentResult, AnalyzedDocument


# ── Component Tests ────────────────────────────────────────────────


class TestFinBERT:
    def test_score(self) -> None:
        from stratos_nlp.adapters.sentiment.finbert import FinBERTScorer
        
        # Mock pipeline factory
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = [[
            {"label": "positive", "score": 0.95},
            {"label": "negative", "score": 0.03},
            {"label": "neutral", "score": 0.02},
        ]]
        
        mock_factory = MagicMock(return_value=mock_pipeline_instance)
        
        scorer = FinBERTScorer(pipeline_factory=mock_factory)
        result = scorer.score("Test text")
        
        assert result.label == SentimentLabel.POSITIVE
        assert result.score == 0.95
        assert result.logits[SentimentLabel.POSITIVE] == 0.95


class TestSpacy:
    def test_extract(self) -> None:
        from stratos_nlp.adapters.extraction.spacy_ner import SpacyExtractor
        
        # Mock spacy load
        with patch("spacy.load") as mock_load:
            mock_nlp = MagicMock()
            mock_doc = MagicMock()
            
            # Mock entities
            ent1 = MagicMock()
            ent1.text = "Apple Inc."
            ent1.label_ = "ORG"
            
            ent2 = MagicMock()
            ent2.text = "Tim Cook"
            ent2.label_ = "PERSON"
            
            mock_doc.ents = [ent1, ent2]
            mock_nlp.return_value = mock_doc
            mock_load.return_value = mock_nlp
            
            extractor = SpacyExtractor()
            entities = extractor.extract("Apple Inc. CEO Tim Cook announced earnings.")
            
            assert "Apple Inc. (ORG)" in entities
            assert "Tim Cook (PERSON)" in entities


class TestEmbedder:
    def test_embed(self) -> None:
        from stratos_nlp.adapters.embeddings.sbert import SentenceTransformerEmbedder
        
        with patch("sentence_transformers.SentenceTransformer") as mock_cls:
            mock_model = MagicMock()
            # Return fake vector of size 384
            import numpy as np
            mock_model.encode.return_value = np.random.rand(384)
            mock_cls.return_value = mock_model
            
            embedder = SentenceTransformerEmbedder()
            vec = embedder.embed("Test")
            
            assert len(vec) == 384
            assert isinstance(vec[0], float)


class TestRAG:
    def test_index_search(self) -> None:
        from stratos_nlp.adapters.rag.memory_store import InMemoryRetriever
        from stratos_nlp.domain.entities import AnalyzedDocument
        from datetime import datetime
        
        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [1.0, 0.0, 0.0]
        
        retriever = InMemoryRetriever(embedder=mock_embedder)
        
        doc = AnalyzedDocument(
            id="doc1",
            content="Hello world",
            source="test",
            published_at=datetime.now(),
            embedding=[1.0, 0.0, 0.0]
        )
        
        retriever.index(doc)
        
        # Perfect match query
        results = retriever.search(query_embedding=[1.0, 0.0, 0.0], limit=1)
        assert len(results) == 1
        assert results[0].id == "doc1"
        
        # Orthogonal query
        results = retriever.search(query_embedding=[0.0, 1.0, 0.0], limit=1)
        # Cosine similarity 0, but still returns top k if forced
        assert len(results) == 1
