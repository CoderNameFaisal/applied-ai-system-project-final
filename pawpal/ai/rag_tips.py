"""Retrieval-only care tips grounded in project knowledge."""

from __future__ import annotations

from dataclasses import dataclass

from pawpal.ai.rag_utils import retrieve_knowledge
from pawpal.system import Owner, Pet


@dataclass(frozen=True)
class CareTip:
    text: str
    source: str
    score: float


@dataclass(frozen=True)
class CareTipsResult:
    tips: list[CareTip]
    used_vectorstore: bool
    note: str


def get_care_tips(owner: Owner, pet: Pet, top_k: int = 4) -> CareTipsResult:
    query = (
        f"Pet care guidance for species={pet.species}, breed={pet.breed}, age={pet.age}. "
        f"Owner preferences: {owner.preferences or 'none'}."
    )
    snippets, used_vectorstore, note = retrieve_knowledge(query, top_k=top_k)
    return CareTipsResult(
        tips=[CareTip(text=row.text, source=row.source, score=row.score) for row in snippets],
        used_vectorstore=used_vectorstore,
        note=note,
    )
