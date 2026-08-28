import os
import re
import cv2
import numpy as np
import pymupdf
from datetime import datetime
from typing import Dict, Any, List

class ImageOCRParser:
    """
    ANVAYA Defense Image OCR Service
    Extracts text from scanned handwritten notes, maps, and screenshots.
    Applies OpenCV minAreaRect deskewing to rectify rotated images before OCR.
    """
    def __init__(self, output_dir: str = "data/processed_text"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._ocr_engine = None

    def _get_ocr_engine(self):
        """Lazy loader for PaddleOCR engine to optimize startup memory."""
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR
                print("[OCR] Initializing PaddleOCR engine (100% offline)...")
                self._ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            except Exception as e:
                print(f"[WARN] PaddleOCR notice: {e}. Using fallback image text extractor.")
                self._ocr_engine = "fallback"
        return self._ocr_engine

    def deskew_image(self, image_path: str) -> np.ndarray:
        """
        Detects skew angle in scanned documents/maps and applies corrective rotation.
        """
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))

        if len(coords) == 0:
            return img

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > 0.5:
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        return img

    def clean_text(self, text: str) -> str:
        """Normalizes extracted OCR text"""
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"[ ]{2,}", " ", text)
        return text.strip()

    def parse_image(self, image_path: str) -> Dict[str, Any]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        base_filename = os.path.basename(image_path)
        print(f"[OCR] Processing Image: {base_filename}")

        extracted_lines = []
        engine = self._get_ocr_engine()

        # Deskew image if OpenCV can read it
        deskewed_img = self.deskew_image(image_path)

        if engine != "fallback" and hasattr(engine, "ocr"):
            try:
                # If deskewed, pass image numpy array
                img_input = deskewed_img if deskewed_img is not None else image_path
                result = engine.ocr(img_input, cls=True)
                if result and result[0]:
                    for line in result[0]:
                        text_content = line[1][0]
                        confidence = line[1][1]
                        if confidence > 0.4:
                            extracted_lines.append(text_content)
            except Exception as err:
                print(f"[WARN] OCR processing error on {base_filename}: {err}")

        # Fallback text extraction via PyMuPDF image text reader if OCR engine is unavailable
        if not extracted_lines:
            try:
                img_doc = pymupdf.open(image_path)
                page = img_doc[0]
                text = page.get_text()
                if text.strip():
                    extracted_lines.append(text.strip())
                img_doc.close()
            except Exception:
                pass

        cleaned_text = self.clean_text("\n".join(extracted_lines)) if extracted_lines else f"[Image Screenshot: {base_filename}]"

        # Save extracted text to disk
        out_filename = f"{os.path.splitext(base_filename)[0]}_ocrText.txt"
        out_path = os.path.join(self.output_dir, out_filename)
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(cleaned_text)

        chunk = {
            "file_name": base_filename,
            "media_type": "image",
            "page_number": 1,
            "text": cleaned_text,
            "char_count": len(cleaned_text),
            "processed_at": datetime.now().isoformat()
        }

        print(f"[OK] Extracted OCR text ({len(cleaned_text)} chars) for {base_filename}")

        return {
            "metadata": {
                "file": base_filename,
                "type": "image",
                "processed_at": datetime.now().isoformat()
            },
            "text_path": out_path,
            "chunks": [chunk]
        }
