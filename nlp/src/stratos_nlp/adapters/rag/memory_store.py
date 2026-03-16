"""FAISS vector store for RAG via LangChain.

Implements `DocumentRetriever` protocol using LangChain's FAISS wrapper.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict

from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document
import faiss

from stratos_nlp.domain.entities import AnalyzedDocument
from stratos_nlp.domain.ports import TextEmbedder


from langchain_core.embeddings import Embeddings

class EmbedderShim(Embeddings):
    """Shim to make TextEmbedder protocol compatible with LangChain Embeddings."""
    
    def __init__(self, embedder: TextEmbedder):
        self.embedder = embedder
        
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_batch(texts)
        
    def embed_query(self, text: str) -> list[float]:
        return self.embedder.embed(text)


class InMemoryRetriever:
    """FAISS-based vector store using LangChain."""

    def __init__(self, embedder: TextEmbedder) -> None:
        self.embedder = embedder
        # Dimension for all-MiniLM-L6-v2 is 384.
        dimension = 384 
        index = faiss.IndexFlatL2(dimension)
        
        # Use shim to pass LangChain-compatible embeddings object
        self._embeddings = EmbedderShim(embedder)
        
        self._vectorstore = FAISS(
            embedding_function=self._embeddings,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={}
        )

    def index(self, document: AnalyzedDocument) -> None:

        """Index a document."""
        # Convert to LangChain Document
        metadata = {
            "source": document.source,
            "sentiment_label": document.sentiment.label if document.sentiment else None,
            "sentiment_score": document.sentiment.score if document.sentiment else None,
            # Flatten entities for metadata filter if needed
        }
        
        # Create unique ID if not present
        doc_id = document.id or str(uuid.uuid4())
        
        # Add to FAISS by vector
        if document.embedding:
            self._vectorstore.add_embeddings(
                text_embeddings=[(document.content, document.embedding)],
                metadatas=[metadata],
                ids=[doc_id]
            )
        else:
            # Fallback if embedding missing (shouldn't happen per use case logic)
            embedding = self.embedder.embed(document.content)
            self._vectorstore.add_embeddings(
                text_embeddings=[(document.content, embedding)],
                metadatas=[metadata],
                ids=[doc_id]
            )

    def search(self, query_embedding: list[float], limit: int = 5) -> list[AnalyzedDocument]:
        """Search by embedding vector."""
        # similarity_search_by_vector_with_score returns List[(Document, float)]
        # We need to map back to AnalyzedDocument.
        # Note: FAISS score is L2 distance (lower is better) if using IndexFlatL2.
        # If we want cosine similarity, we should normalize. 
        # For this refactor, raw FAISS usage ensures "using LangChain".
        
        results = self._vectorstore.similarity_search_by_vector(
            embedding=query_embedding,
            k=limit
        )
        
        analyzed_docs = []
        for doc in results:
            # Map back
            # Note: We lose some original fields like 'entities' list in simple metadata 
            # unless we stored them as JSON string. For RAG context, content is sufficient.
            analyzed_docs.append(AnalyzedDocument(
                id="retrieved_doc", # ID mapping specific to docstore
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                embedding=[], # We don't return embedding to save bandwidth
            ))
            
        return analyzed_docs
