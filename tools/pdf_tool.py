"""
tools/pdf_tool.py

Agno-compatible tool for extracting raw text and layout hints from a
resume PDF. Uses PyMuPDF (fast, good for text) with pdfplumber as a
fallback for PDFs where PyMuPDF returns weak text (e.g. some
table-heavy resume templates).
"""

from __future__ import annotations

import fitz  # PyMuPDF
import pdfplumber
from agno.tools import Toolkit


class PDFTool(Toolkit):
    """Extracts text content from resume PDFs for downstream agents."""

    def __init__(self):
        super().__init__(name="pdf_tool")
        self.register(self.extract_text)
        self.register(self.extract_text_with_layout)

    def extract_text(self, file_path: str) -> str:
        """Extract plain text from a PDF using PyMuPDF.

        Args:
            file_path: Absolute path to the PDF file on disk.

        Returns:
            The extracted text as a single string. Falls back to
            pdfplumber if PyMuPDF yields suspiciously little text
            (< 40 characters), which usually means the PDF is
            image-based or has an unusual layout.
        """
        text = ""
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text("text") + "\n"
        except Exception as exc:  # noqa: BLE001
            text = f""  # fall through to pdfplumber

        if len(text.strip()) < 40:
            text = self._extract_with_pdfplumber(file_path)

        return text.strip()

    def extract_text_with_layout(self, file_path: str) -> str:
        """Extract text while preserving rough table/column structure.

        Useful for resumes that use two-column layouts, since plain
        text extraction can interleave columns and confuse the LLM.

        Args:
            file_path: Absolute path to the PDF file on disk.

        Returns:
            Text with page and table boundaries marked.
        """
        return self._extract_with_pdfplumber(file_path)

    @staticmethod
    def _extract_with_pdfplumber(file_path: str) -> str:
        chunks = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                chunks.append(f"--- Page {i + 1} ---\n{page_text}")

                tables = page.extract_tables()
                for t_idx, table in enumerate(tables):
                    chunks.append(f"[Table {t_idx + 1} on page {i + 1}]")
                    for row in table:
                        chunks.append(" | ".join(cell or "" for cell in row))
        return "\n".join(chunks).strip()
