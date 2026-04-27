"""Build the local RAG index from committed knowledge files."""

from __future__ import annotations

from pathlib import Path

from pawpal.ai.vectorstore import upsert_chunks

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def chunk_text(content: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunks.append(content[start:end].strip())
        if end == len(content):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]


def build_chunks_from_knowledge(knowledge_dir: Path) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for file_path in sorted(knowledge_dir.glob("*.md")):
        text = file_path.read_text(encoding="utf-8")
        for index, piece in enumerate(chunk_text(text)):
            chunks.append(
                {
                    "id": f"{file_path.stem}-{index}",
                    "source": str(file_path.as_posix()),
                    "text": piece,
                }
            )
    return chunks


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    knowledge_dir = project_root / "knowledge"
    if not knowledge_dir.exists():
        raise SystemExit("knowledge/ directory not found.")
    chunks = build_chunks_from_knowledge(knowledge_dir)
    count = upsert_chunks(chunks)
    print(f"Indexed {count} chunks from {knowledge_dir}.")


if __name__ == "__main__":
    main()
