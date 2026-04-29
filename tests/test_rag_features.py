from types import SimpleNamespace

from pawpal.ai.rag_utils import retrieve_knowledge


def test_retrieve_knowledge_uses_vectorstore_when_available(monkeypatch) -> None:
    fake_chunks = [
        SimpleNamespace(text="Use consistent walk windows.", source="knowledge/care_basics.md", score=0.12),
    ]
    monkeypatch.setattr("pawpal.ai.rag_utils.retrieve_chunks", lambda *_args, **_kwargs: fake_chunks)

    snippets, used_vectorstore, note = retrieve_knowledge("dog walk timing", top_k=1)

    assert used_vectorstore is True
    assert note == ""
    assert len(snippets) == 1
    assert snippets[0].text == "Use consistent walk windows."


def test_retrieve_knowledge_falls_back_to_local_lexical(monkeypatch) -> None:
    def _raise(*_args, **_kwargs):
        raise RuntimeError("vector backend unavailable")

    monkeypatch.setattr("pawpal.ai.rag_utils.retrieve_chunks", _raise)

    snippets, used_vectorstore, note = retrieve_knowledge("species breed age habits", top_k=2)

    assert used_vectorstore is False
    assert "fallback" in note.lower()
    assert len(snippets) > 0
    assert all("knowledge" in row.source for row in snippets)
