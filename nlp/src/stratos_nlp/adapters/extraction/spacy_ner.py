"""spaCy entity extraction adapter.

Implements `EntityExtractor` protocol.
Extracts ORG, PERSON, GPE, MONEY, PERCENT entities.
"""

from __future__ import annotations

import spacy


class SpacyExtractor:
    """Named entity recognition using spaCy en_core_web_sm."""

    def __init__(self, model: str = "en_core_web_sm") -> None:
        self.model_name = model
        self._nlp = None

    def name(self) -> str:
        return f"spaCy({self.model_name})"

    def _load(self) -> None:
        """Lazy load spaCy model."""
        if self._nlp is None:
            try:
                self._nlp = spacy.load(self.model_name)
            except OSError:
                from spacy.cli import download
                download(self.model_name)
                self._nlp = spacy.load(self.model_name)

    def extract(self, text: str) -> list[str]:
        """Extract entities from text."""
        self._load()
        doc = self._nlp(text)
        
        # Filter for relevant entity types
        relevant_types = {"ORG", "PERSON", "GPE", "MONEY", "PERCENT"}
        
        entities = []
        for ent in doc.ents:
            if ent.label_ in relevant_types:
                entities.append(f"{ent.text} ({ent.label_})")
                
        return sorted(list(set(entities)))
