"""
RAG indexer — reads seed documents, chunks them, embeds with nomic-embed-text
(via Ollama), and persists to ChromaDB.

Usage:
    python rag/indexer.py

Safe to re-run: only indexes documents not already in the collection.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

from config.settings import (
    CHROMA_DB_PATH,
    EMBEDDING_MODEL,
    OLLAMA_BASE_URL,
    RAG_CHUNK_SIZE,
    RAG_CHUNK_OVERLAP,
    RAG_COLLECTION_NAME,
)

SEED_DOCS_DIR = Path(__file__).parent / "seed_docs"


def build_index(force_rebuild: bool = False) -> Chroma:
    """
    Build or load the ChromaDB vector index.

    Args:
        force_rebuild: If True, deletes existing collection and rebuilds from scratch.

    Returns:
        LangChain Chroma vectorstore instance ready for querying.
    """
    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    chroma_path = Path(CHROMA_DB_PATH)

    # If index already exists and we're not forcing a rebuild, just load it
    if chroma_path.exists() and not force_rebuild:
        print(f"[Indexer] Loading existing ChromaDB index from {CHROMA_DB_PATH}")
        vectorstore = Chroma(
            collection_name=RAG_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH,
        )
        count = vectorstore._collection.count()
        print(f"[Indexer] Loaded {count} existing document chunks.")
        return vectorstore

    # Load documents from seed_docs/
    if not SEED_DOCS_DIR.exists() or not any(SEED_DOCS_DIR.glob("*.txt")):
        raise FileNotFoundError(
            f"Seed docs directory not found or empty: {SEED_DOCS_DIR}. "
            "Run 'python rag/seed_data.py' first."
        )

    print(f"[Indexer] Loading documents from {SEED_DOCS_DIR} ...")
    loader = DirectoryLoader(
        str(SEED_DOCS_DIR),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    docs = loader.load()
    print(f"[Indexer] Loaded {len(docs)} documents.")

    # Add source metadata for attribution
    for doc in docs:
        source_path = Path(doc.metadata.get("source", ""))
        doc.metadata["filename"] = source_path.name
        doc.metadata["category"] = _categorise(source_path.name)

    # Chunk documents
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"[Indexer] Split into {len(chunks)} chunks.")

    # Embed and store in ChromaDB
    print(f"[Indexer] Embedding with '{EMBEDDING_MODEL}' and storing in ChromaDB ...")
    print("          (This may take a few minutes on first run)")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=RAG_COLLECTION_NAME,
        persist_directory=CHROMA_DB_PATH,
    )
    print(f"[Indexer] Stored {len(chunks)} chunks. Index saved to {CHROMA_DB_PATH}")
    return vectorstore


def _categorise(filename: str) -> str:
    """Assign a document category based on filename prefix for metadata."""
    if filename.startswith("fundamentals_"):
        return "company_fundamental"
    if filename.startswith("recent_news"):
        return "news"
    return "reference_guide"


def get_vectorstore() -> Chroma:
    """
    Return the vectorstore, building the index if it doesn't exist yet.
    Called by the retriever and agent tools at runtime.
    """
    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    chroma_path = Path(CHROMA_DB_PATH)
    if not chroma_path.exists():
        print("[Indexer] Index not found — building now (this runs once) ...")
        # Auto-seed if seed_docs doesn't exist either
        if not SEED_DOCS_DIR.exists() or not any(SEED_DOCS_DIR.glob("*.txt")):
            print("[Indexer] Seeding reference documents first ...")
            from rag.seed_data import build_reference_texts
            build_reference_texts()
        return build_index()
    return Chroma(
        collection_name=RAG_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build the RAG ChromaDB index.")
    parser.add_argument("--force-rebuild", action="store_true", help="Delete and rebuild index.")
    args = parser.parse_args()
    build_index(force_rebuild=args.force_rebuild)
    print("[Indexer] Done.")
