from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _load_documents(file_path: Path):
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path), mode="single")
        return loader.load()
    if suffix == ".docx":
        loader = Docx2txtLoader(str(file_path))
        return loader.load()
    if suffix == ".txt":
        # Fallback: lettura diretta
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        # Normalizza in un singolo "Document" equivalente (dict minimalista)
        class _Doc:
            def __init__(self, text: str):
                self.page_content = text

        return [_Doc(content)]
    raise ValueError("unsupported_file_type")


def extract_text(file_path: Path) -> str:
    docs = _load_documents(file_path)
    parts: List[str] = [getattr(d, "page_content", "") or "" for d in docs]
    return "\n".join(parts).strip()


def split_text(content: str, chunk_size: int = 800, chunk_overlap: int = 160) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(content or "")
