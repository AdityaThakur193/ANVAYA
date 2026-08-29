import os
import re
import json
import pymupdf
from datetime import datetime
from typing import Dict, List, Any, Tuple

class PDFParser:
    """
    ANVAYA Defense PDF Parser & High-Fidelity Table Extractor
    Uses PyMuPDF layout block sorting + strict table validation filter to produce
    clean, human-readable text and pristine Markdown tables without false-positive pipe boxes.
    """
    def __init__(self, output_dir: str = "data/processed_text", manifest_path: str = "data/metadata.json"):
        self.output_dir = output_dir
        self.manifest_path = manifest_path
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)

    def clean_text(self, text: str) -> str:
        """Normalizes text, strips print timestamps and fixes line hyphens."""
        # Remove browser print timestamps like "26/08/2026, 08:24"
        text = re.sub(r"\d{2}/\d{2}/\d{4},\s*\d{2}:\d{2}", "", text)
        # Remove repeated footer strings
        text = re.sub(r"FPM Unit \d+ Master Question Bank.*", "", text)
        text = text.replace("\f", " ")
        text = re.sub(r"-\n", "", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ ]{2,}", " ", text)
        return text.strip()

    def _is_valid_data_table(self, grid: List[List[Any]]) -> bool:
        """
        Strict filter to verify if a candidate grid is a TRUE structured data table
        (e.g., CPM/PERT comparison, Float matrix) vs. a false-positive paragraph box.
        """
        if not grid or len(grid) < 2:
            return False

        num_cols = len(grid[0])
        if num_cols < 2:
            return False

        total_cells = 0
        long_paragraph_cells = 0

        for row in grid:
            for cell in row:
                cell_text = str(cell or "").strip()
                if cell_text:
                    total_cells += 1
                    # Data table cells contain short terms/numbers; paragraph boxes contain huge blocks
                    if len(cell_text) > 160:
                        long_paragraph_cells += 1

        # If > 25% of cells contain long paragraph blocks, it's a paragraph box, not a data table!
        if total_cells > 0 and (long_paragraph_cells / total_cells) > 0.25:
            return False

        return True

    def extract_structured_page_content(self, page: pymupdf.Page) -> Tuple[str, List[float]]:
        """
        Extracts page text with high-fidelity Markdown table formatting.
        Applies strict data table validation to prevent false-positive pipe boxes around paragraphs.
        """
        tables_md = []
        table_bboxes = []

        # 1. Detect and validate true structured data tables
        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                for tab in tabs.tables:
                    grid = tab.extract()
                    if grid and self._is_valid_data_table(grid):
                        clean_grid = [[str(cell or "").replace("\n", " ").strip() for cell in row] for row in grid]
                        if clean_grid and clean_grid[0]:
                            headers = clean_grid[0]
                            md = "\n\n| " + " | ".join(headers) + " |\n"
                            md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                            for row in clean_grid[1:]:
                                md += "| " + " | ".join(row) + " |\n"
                            tables_md.append(md)
                            table_bboxes.append(tab.bbox)
        except Exception:
            pass

        # 2. Extract non-table text blocks
        blocks = page.get_text("blocks")
        non_table_blocks = []
        page_bbox = [0, 0, 0, 0]

        if blocks:
            text_blocks = [b for b in blocks if b[6] == 0]
            if text_blocks:
                x0 = min(b[0] for b in text_blocks)
                y0 = min(b[1] for b in text_blocks)
                x1 = max(b[2] for b in text_blocks)
                y1 = max(b[3] for b in text_blocks)
                page_bbox = [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]

            for b in text_blocks:
                bx0, by0, bx1, by1 = b[0], b[1], b[2], b[3]
                # Check overlap with validated data tables
                in_table = False
                for tbox in table_bboxes:
                    if not (bx1 < tbox[0] or bx0 > tbox[2] or by1 < tbox[1] or by0 > tbox[3]):
                        in_table = True
                        break
                if not in_table:
                    block_text = b[4].strip()
                    if block_text:
                        non_table_blocks.append(block_text)

        body_text = "\n\n".join(non_table_blocks)
        if tables_md:
            body_text += "\n\n" + "\n".join(tables_md)

        return self.clean_text(body_text), page_bbox

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        base_filename = os.path.basename(pdf_path)
        doc = pymupdf.open(pdf_path)

        page_chunks = []
        full_text_list = []

        print(f"[PDF] Processing: {base_filename}")

        for page_idx, page in enumerate(doc, start=1):
            cleaned_text, bbox = self.extract_structured_page_content(page)

            if cleaned_text:
                full_text_list.append(cleaned_text)
                page_chunks.append({
                    "file_name": base_filename,
                    "media_type": "pdf",
                    "page_number": page_idx,
                    "text": cleaned_text,
                    "char_count": len(cleaned_text),
                    "bbox": bbox
                })

        combined_text = "\n\n".join(full_text_list)

        # Save extracted clean text to disk
        out_filename = f"{os.path.splitext(base_filename)[0]}_exText.txt"
        out_path = os.path.join(self.output_dir, out_filename)
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(combined_text)

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

        self._update_manifest(metadata)
        doc.close()

        print(f"[OK] Extracted {len(page_chunks)} structured page chunks for {base_filename}")

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
                print("[WARN] Manifest corrupted - reinitializing.")

        manifest.append(metadata)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
