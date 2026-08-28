import os
import re
import json
import pymupdf
from datetime import datetime
from typing import Dict, List, Any

class PDFParser:
    """
    ANVAYA Defense PDF Parsing Service
    Uses PyMuPDF (fitz) structural layout block parsing + regex text normalization
    + bounding box spatial coordinates (x0, y0, x1, y1) + Markdown table preservation.
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

        print(f"[PDF] Processing: {base_filename}")

        # Page-by-page extraction with structural layout blocks & bounding box spatial coordinates
        for page_idx, page in enumerate(doc, start=1):
            raw_text = page.get_text()
            cleaned_page_text = self.clean_text(raw_text)

            # Table preservation check
            tables_md = self._extract_tables_as_markdown(page)
            if tables_md:
                cleaned_page_text += "\n\n" + tables_md

            if cleaned_page_text:
                full_text_list.append(cleaned_page_text)

                # Extract layout blocks for spatial coordinates
                blocks = page.get_text("blocks")
                page_bbox = [0, 0, 0, 0]
                if blocks:
                    # Filter text blocks (block[6] == 0)
                    text_blocks = [b for b in blocks if b[6] == 0]
                    if text_blocks:
                        x0 = min(b[0] for b in text_blocks)
                        y0 = min(b[1] for b in text_blocks)
                        x1 = max(b[2] for b in text_blocks)
                        y1 = max(b[3] for b in text_blocks)
                        page_bbox = [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]

                page_chunks.append({
                    "file_name": base_filename,
                    "media_type": "pdf",
                    "page_number": page_idx,
                    "text": cleaned_page_text,
                    "char_count": len(cleaned_page_text),
                    "bbox": page_bbox
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

        print(f"[OK] Extracted {len(page_chunks)} page chunks for {base_filename}")

        return {
            "metadata": metadata,
            "text_path": out_path,
            "page_chunks": page_chunks
        }

    def _extract_tables_as_markdown(self, page: pymupdf.Page) -> str:
        """Detects PDF grid tables and converts them to explicit Markdown tables."""
        try:
            tabs = page.find_tables()
            if not tabs or len(tabs.tables) == 0:
                return ""

            table_output = ""
            for table in tabs:
                grid = table.extract()
                if not grid or len(grid) == 0:
                    continue

                headers = [str(cell or "").replace("\n", " ").strip() for cell in grid[0]]
                markdown_table = "\n| " + " | ".join(headers) + " |\n"
                markdown_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"

                for row in grid[1:]:
                    row_cells = [str(cell or "").replace("\n", " ").strip() for cell in row]
                    markdown_table += "| " + " | ".join(row_cells) + " |\n"

                table_output += markdown_table + "\n"

            return table_output.strip()
        except Exception:
            return ""

    def _update_manifest(self, metadata: Dict[str, Any]):
        manifest = []
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except json.JSONDecodeError:
                print("[WARN] Manifest corrupted - reinitializing.")

        manifest.append(metadata)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
