"""
Indexing script — runs the full RAG ingestion pipeline on a document.

Usage (from repo root):
    cd backend && uv run python -m scripts.index_document <path_to_pdf>

Or directly:
    cd backend && uv run python scripts/index_document.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# ── ensure backend/ is on sys.path ──────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# ── imports (after path fix) ─────────────────────────────────────────────────
from app.database.session import SessionLocal
from rag.chunking.overlap import OverlapChunker
from rag.embeddings.openrouter import OpenRouterEmbeddings
from rag.ingestion.pipeline import IngestionPipeline
from rag.vectorstores.pgvector import PGVectorStore

# ── configuration ─────────────────────────────────────────────────────────────
DOCUMENT_PATH = Path(__file__).resolve().parents[2] / "document_store" / "PyTorch_Complete_Course_CampusX_OCR.pdf"

CHUNK_SIZE    = 800   # characters
CHUNK_OVERLAP = 150   # characters
EMBED_MODEL   = "sentence-transformers/all-minilm-l6-v2"
BATCH_SIZE    = 64    # chunks per embedding/store batch


def log(msg: str) -> None:
    print(f"[indexer] {msg}", flush=True)


def run_indexing(pdf_path: Path) -> None:
    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        sys.exit(1)

    total_start = time.perf_counter()

    # ── 1. Ingestion: Load → Parse → Clean ────────────────────────────────────
    log(f"Loading & parsing: {pdf_path.name}")
    t = time.perf_counter()
    pipeline = IngestionPipeline()
    document = pipeline.run(pdf_path)
    log(f"  ✓ Parsed {document.page_count} pages  [{time.perf_counter()-t:.1f}s]")

    # ── 2. Chunking (OverlapChunker) ──────────────────────────────────────────
    log(f"Chunking (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}) …")
    t = time.perf_counter()
    chunker = OverlapChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks  = chunker.chunk(document)
    log(f"  ✓ {len(chunks)} chunks produced  [{time.perf_counter()-t:.1f}s]")
    if not chunks:
        log("No chunks generated — aborting.")
        return

    # Show breakdown
    from collections import Counter
    type_counts = Counter(
        (c.chunk_type.value if hasattr(c.chunk_type, 'value') else str(c.chunk_type))
        for c in chunks
    )
    for t_name, count in sorted(type_counts.items()):
        log(f"    {t_name}: {count}")

    # ── 3. Embedding + Storage (batch) ────────────────────────────────────────
    log(f"Embedding model: {EMBED_MODEL}")
    embedder  = OpenRouterEmbeddings(model_name=EMBED_MODEL)
    log(f"  ✓ Embedding dimension: {embedder.dimension}")

    session   = SessionLocal()
    store     = PGVectorStore(session=session)

    total_stored = 0
    embed_time   = 0.0
    store_time   = 0.0

    log(f"Storing chunks in batches of {BATCH_SIZE} …")
    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]

        # Embed
        te = time.perf_counter()
        texts      = [c.content for c in batch]
        embeddings = embedder.embed_batch(texts)
        embed_time += time.perf_counter() - te

        # Attach embeddings to chunk objects
        for chunk, vec in zip(batch, embeddings):
            chunk.embedding = vec

        # Store
        ts = time.perf_counter()
        store.add_chunks(batch)
        store_time += time.perf_counter() - ts

        total_stored += len(batch)
        pct = total_stored / len(chunks) * 100
        log(f"  stored {total_stored}/{len(chunks)} ({pct:.0f}%)")

    session.close()

    elapsed = time.perf_counter() - total_start
    log("─" * 60)
    log(f"✓ Indexing complete!")
    log(f"  Document   : {document.document_id}")
    log(f"  Pages      : {document.page_count}")
    log(f"  Chunks     : {len(chunks)}")
    log(f"  Embed time : {embed_time:.1f}s")
    log(f"  Store time : {store_time:.1f}s")
    log(f"  Total time : {elapsed:.1f}s")


if __name__ == "__main__":
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else DOCUMENT_PATH
    run_indexing(pdf)
