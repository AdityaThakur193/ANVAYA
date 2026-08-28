import os
import re
import json
import pymupdf
from datetime import datetime
from typing import Dict, List, Any

class PDFParser:
    """
    ANVAYA PDF Parsing Service
    Uses PyMuPDF & Regex cleaning to extract clean text, page numbers, and metadata.
    """
    def __init__(self, output_dir: str = "data/processed_text", manifest_path: str = "data/metadata.json"):
        self.output_dir = output_dir
        self.manifest_path = manifest_path
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)

    def clean_text(self, text: str) -> str:
        """PyMuPDF Regex text cleaning & normalization"""
        text = text.replace("\f", " ")                   # remove form feed
        text = re.sub(r"-\n", "", text)                  # fix hyphenation across lines
        text = re.sub(r"\s+\n", "\n", text)              # trim spaces before newlines
        text = re.sub(r"\n{3,}", "\n\n", text)           # collapse excessive newlines
        text = re.sub(r"[ ]{2,}", " ", text)             # collapse multiple spaces
        return text.strip()

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        base_filename = os.path.basename(pdf_path)
        doc = pymupdf.open(pdf_path)

        page_chunks = []
        full_text_list = []

        print(f"📘 Processing PDF: {base_filename}")

        # Page-by-page extraction for precise RAG page citations
        for page_idx, page in enumerate(doc, start=1):
            raw_text = page.get_text()
            cleaned_text = self.clean_text(raw_text)

            if cleaned_text:
                full_text_list.append(cleaned_text)
                page_chunks.append({
                    "file_name": base_filename,
                    "media_type": "pdf",
                    "page_number": page_idx,
                    "text": cleaned_text,
                    "char_count": len(cleaned_text)
                })

        combined_text = "\n\n".join(full_text_list)

        # Save extracted clean text to disk
        out_filename = f"{os.path.splitext(base_filename)[0]}_exText.txt"
        out_path = os.path.join(self.output_dir, out_filename)
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(combined_text)

        # Extract & normalize metadata
        raw_meta = doc.metadata or {}
        base_name = os.path.splitext(base_filename)[0]

        metadata = {
            "title": raw_meta.get("title") or base_name,
            "author": raw_meta.get("author") or "Unknown",
            "pages": len(doc),
            "file": base_filename,
            "processed_at": datetime.now().isoformat(),
            "source": "document"
        }

        # Update metadata.json manifest
        self._update_manifest(metadata)
        doc.close()

        print(f"✅ Extracted {len(page_chunks)} page chunks for {base_filename}")

        return {
            "metadata": metadata,
            "text_path": out_path,
            "page_chunks": page_chunks
        }

    def _update_manifest(self, metadata: Dict[str, Any]):
        manifest = []
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Manifest corrupted — reinitializing.")

        manifest.append(metadata)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
