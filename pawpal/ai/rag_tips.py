"""Retrieval-only care tips grounded in project knowledge."""

from __future__ import annotations

import re
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


def _tokenize(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(token) > 1}


def _age_band(age: int) -> str:
    if age <= 1:
        return "young"
    if age >= 8:
        return "senior"
    return "adult"


def _profile_queries(owner: Owner, pet: Pet) -> list[str]:
    age_band = _age_band(pet.age)
    habits = (pet.habits or "none").strip()
    return [
        (
            f"Actionable care tips for {pet.species} breed {pet.breed} age {pet.age} "
            f"({age_band}) with habits: {habits}."
        ),
        (
            f"Scheduling adjustments for {pet.species} {pet.breed} considering age {pet.age} "
            f"and owner preferences: {owner.preferences or 'none'}."
        ),
        (
            f"Practical routines and enrichment pacing for {pet.species}, breed {pet.breed}, "
            f"age band {age_band}."
        ),
    ]


def _rerank_snippets(owner: Owner, pet: Pet, snippets: list[CareTip], top_k: int) -> list[CareTip]:
    profile_terms = _tokenize(f"{pet.species} {pet.breed} {_age_band(pet.age)} {pet.age} {pet.habits or ''}")
    owner_terms = _tokenize(owner.preferences or "")
    ranked: list[CareTip] = []
    for row in snippets:
        snippet_terms = _tokenize(row.text)
        profile_overlap = len(snippet_terms & profile_terms)
        owner_overlap = len(snippet_terms & owner_terms)
        blended_score = row.score + (0.12 * profile_overlap) + (0.08 * owner_overlap)
        ranked.append(CareTip(text=row.text, source=row.source, score=blended_score))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:top_k]


def _personalize_tip_text(pet: Pet, raw_text: str) -> str:
    age_band = _age_band(pet.age)
    return (
        f"For {pet.name} ({pet.breed}, age {pet.age}, {age_band}), "
        f"{raw_text}"
    )


def get_care_tips(owner: Owner, pet: Pet, top_k: int = 4) -> CareTipsResult:
    collected: list[CareTip] = []
    used_vectorstore = False
    notes: list[str] = []

    # Multi-query retrieval adds profile-aware context rather than a single generic search.
    for query in _profile_queries(owner, pet):
        snippets, used_vectorstore_for_query, note = retrieve_knowledge(query, top_k=max(top_k, 2))
        used_vectorstore = used_vectorstore or used_vectorstore_for_query
        if note:
            notes.append(note)
        collected.extend(CareTip(text=row.text, source=row.source, score=row.score) for row in snippets)

    # Deduplicate by snippet text before reranking.
    deduped: dict[str, CareTip] = {}
    for row in collected:
        key = row.text.strip().lower()
        if not key:
            continue
        previous = deduped.get(key)
        if previous is None or row.score > previous.score:
            deduped[key] = row

    reranked = _rerank_snippets(owner, pet, list(deduped.values()), top_k=top_k)
    return CareTipsResult(
        tips=[
            CareTip(
                text=_personalize_tip_text(pet, row.text),
                source=row.source,
                score=row.score,
            )
            for row in reranked
        ],
        used_vectorstore=used_vectorstore,
        note=notes[0] if notes else "",
    )
