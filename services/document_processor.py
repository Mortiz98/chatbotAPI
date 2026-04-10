import pdfplumber
from typing import List, Dict
import re


class DocumentProcessor:
    """PDF document processor for chunking."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extracts all text from a PDF."""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def chunk_text(self, text: str) -> List[str]:
        """Splits text into chunks with overlap."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            if end < len(text):
                last_newline = text.rfind("\n", start, end)
                last_space = text.rfind(" ", start, end)
                cut_point = max(last_newline, last_space)
                if cut_point > start:
                    end = cut_point

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = (
                end - self.overlap
                if end - self.overlap > start
                else start + self.chunk_size
            )

        return chunks

    def process_pdf(self, pdf_path: str, metadata: Dict = None) -> List[Dict]:
        """Processes a PDF and returns list of chunks with metadata."""
        text = self.extract_text_from_pdf(pdf_path)
        chunks = self.chunk_text(text)

        filename = pdf_path.split("/")[-1]

        return [
            {
                "text": chunk,
                "metadata": {
                    "source": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    **(metadata or {}),
                },
            }
            for i, chunk in enumerate(chunks)
        ]

    def clean_text(self, text: str) -> str:
        """Cleans text of unnecessary characters."""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        return text.strip()


class ChunkValidator:
    """Validator for chunk quality."""

    MIN_LENGTH = 50
    MAX_LENGTH = 2000

    @staticmethod
    def is_valid(chunk: str) -> bool:
        """Checks if a chunk is valid."""
        if not chunk or len(chunk) < ChunkValidator.MIN_LENGTH:
            return False
        if len(chunk) > ChunkValidator.MAX_LENGTH:
            return False
        alpha_ratio = sum(c.isalpha() for c in chunk) / len(chunk)
        return alpha_ratio > 0.3

    @staticmethod
    def filter_valid(chunks: List[str]) -> List[str]:
        """Filters only valid chunks."""
        return [c for c in chunks if ChunkValidator.is_valid(c)]
