"""spaCy entity extraction adapter."""

from __future__ import annotations

import sys
import types

try:  # pragma: no cover - exercised indirectly in environments with spaCy
    import spacy  # type: ignore
except ImportError:  # pragma: no cover - lightweight fallback for tests
    spacy = types.ModuleType("spacy")

    def _missing_spacy(*args, **kwargs):
        raise ImportError("spaCy is required to use SpacyExtractor.")

    spacy.load = _missing_spacy  # type: ignore[attr-defined]
    cli = types.ModuleType("spacy.cli")
    cli.download = _missing_spacy  # type: ignore[attr-defined]
    spacy.cli = cli  # type: ignore[attr-defined]
    sys.modules.setdefault("spacy", spacy)
    sys.modules.setdefault("spacy.cli", cli)


class SpacyExtractor:
    """Named entity recognition using spaCy en_core_web_sm."""

    def __init__(self, model: str = "en_core_web_sm") -> None:
        self.model_name = model
        self._nlp = None

    def name(self) -> str:
        return f"spaCy({self.model_name})"

    def _load(self) -> None:
        if self._nlp is not None:
            return

        try:
            self._nlp = spacy.load(self.model_name)
        except OSError:
            from spacy.cli import download

            download(self.model_name)
            self._nlp = spacy.load(self.model_name)

    def extract(self, text: str) -> list[str]:
        self._load()
        doc = self._nlp(text)
        relevant_types = {"ORG", "PERSON", "GPE", "MONEY", "PERCENT"}
        entities = [f"{ent.text} ({ent.label_})" for ent in doc.ents if ent.label_ in relevant_types]
        return sorted(set(entities))
