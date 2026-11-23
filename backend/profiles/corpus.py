"""Career Corpus (Evidence Vault) — NotebookLM-style multi-source ingestion & retrieval.

Allows any user to attach multiple heterogeneous career documents (PDFs, DOCX,
PPTX presentations, Markdown, plain text, papers, project reports) to a
MasterProfile. At generation time, BM25-style keyword retrieval selects the
most relevant passages for the target Job Description and injects them into
the prompt as verified evidence — zero external vector DB required.
"""

from __future__ import annotations

import io
import math
import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from backend.profiles.cv_parser import extract_text

SUPPORTED_SOURCE_EXTENSIONS: frozenset[str] = frozenset({"pdf", "docx", "txt", "md", "pptx"})

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
        "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "this", "that", "these", "those",
        "it", "its", "as", "not", "no", "so", "if", "then", "than", "too", "very",
        "just", "about", "into", "over", "under", "up", "out", "all", "also", "any",
        "we", "you", "your", "our", "they", "their", "them", "who", "which", "what",
        "role", "position", "team", "work", "working", "experience", "years", "strong",
    }
)


def extract_source_text(file_bytes: bytes, filename: str) -> str:
    """Extract clean plain text from PDF, DOCX, PPTX, MD, or TXT bytes."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_SOURCE_EXTENSIONS:
        raise ValueError(
            f"Unsupported source format '.{ext}'. Supported: {', '.join(sorted(SUPPORTED_SOURCE_EXTENSIONS))}"
        )

    if ext in ("txt", "md"):
        return file_bytes.decode("utf-8", errors="replace").strip()

    if ext in ("pdf", "docx"):
        return extract_text(file_bytes, filename).strip()

    if ext == "pptx":
        return _extract_pptx_text(file_bytes)

    return ""


def _extract_pptx_text(file_bytes: bytes) -> str:
    """Extract slide text from a PPTX archive using Python stdlib only."""
    slides: list[str] = []
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
        slide_names = sorted(
            name
            for name in archive.namelist()
            if re.match(r"^ppt/slides/slide\d+\.xml$", name)
        )
        for name in slide_names:
            root = ET.fromstring(archive.read(name))
            texts = [
                elem.text.strip()
                for elem in root.iter()
                if elem.tag.endswith("}t") and elem.text and elem.text.strip()
            ]
            if texts:
                slides.append(" ".join(texts))
    return "\n\n".join(slides).strip()


def chunk_text(text: str, *, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    """Split text into overlapping, whitespace-normalized passages."""
    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        return []

    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n{2,}", cleaned)]
    paragraphs = [p for p in paragraphs if p]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            step = max(1, chunk_size - overlap)
            for start in range(0, len(para), step):
                piece = para[start : start + chunk_size].strip()
                if piece:
                    chunks.append(piece)
            continue

        if current and len(current) + 1 + len(para) > chunk_size:
            chunks.append(current)
            tail = current[-overlap:].strip() if overlap > 0 else ""
            current = f"{tail} {para}".strip() if tail else para
        else:
            current = f"{current} {para}".strip() if current else para

    if current:
        chunks.append(current)
    return chunks


def build_source_entry(
    *,
    title: str,
    text: str,
    source_type: str = "text",
    filename: str | None = None,
    max_chunks: int = 80,
) -> dict[str, Any]:
    """Build a serializable ProfileSourceEntry dict from extracted text."""
    chunks = chunk_text(text)[:max_chunks]
    return {
        "id": str(uuid.uuid4()),
        "title": title.strip()[:255] or (filename or "Untitled Source"),
        "source_type": source_type,
        "filename": filename,
        "char_count": len(text),
        "chunks": chunks,
        "uploaded_at": datetime.now(UTC).isoformat(),
    }


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+#._-]{1,}", text.lower())
    return [tok for tok in tokens if tok not in _STOP_WORDS and len(tok) >= 2]


def retrieve_relevant_evidence(
    sources: list[dict[str, Any]],
    query_text: str,
    *,
    top_k: int = 6,
    max_total_chars: int = 4500,
) -> list[dict[str, Any]]:
    """Rank and return top-K corpus passages most relevant to *query_text* using BM25."""
    query_tokens = _tokenize(query_text)
    if not query_tokens or not sources:
        return []

    query_terms = set(query_tokens)
    corpus_docs: list[tuple[str, str, list[str], Counter[str]]] = []
    doc_freq: Counter[str] = Counter()

    for src in sources:
        title = str(src.get("title") or src.get("filename") or "Source")
        for chunk in src.get("chunks") or []:
            text = str(chunk).strip()
            if not text:
                continue
            tokens = _tokenize(text)
            if not tokens:
                continue
            tf = Counter(tokens)
            corpus_docs.append((title, text, tokens, tf))
            for term in set(tokens):
                doc_freq[term] += 1

    if not corpus_docs:
        return []

    n_docs = len(corpus_docs)
    avg_dl = sum(len(doc[2]) for doc in corpus_docs) / n_docs
    k1 = 1.5
    b = 0.75

    scored: list[tuple[float, str, str]] = []
    for title, text, tokens, tf in corpus_docs:
        dl = len(tokens)
        score = 0.0
        for term in query_terms:
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            df = doc_freq[term]
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            denom = freq + k1 * (1.0 - b + b * (dl / max(avg_dl, 1.0)))
            score += idf * ((freq * (k1 + 1.0)) / denom)
        if score > 0.0:
            scored.append((score, title, text))

    scored.sort(key=lambda item: item[0], reverse=True)

    selected: list[dict[str, Any]] = []
    total_chars = 0
    for score, title, text in scored[:top_k]:
        if total_chars + len(text) > max_total_chars and selected:
            break
        selected.append({"source": title, "score": round(score, 4), "excerpt": text})
        total_chars += len(text)
    return selected
