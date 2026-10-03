"""Evidence helper – Person 4.

Utilities for parsing and classifying uploaded documents (PDFs, screenshots).
Works alongside extraction.py.

Signature to implement:
    def classify_document(content: bytes, filename: str) -> DocumentType
    def extract_text(content: bytes, mime: str) -> str
"""
