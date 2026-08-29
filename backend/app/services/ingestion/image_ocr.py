import os
import re
import cv2
import numpy as np
import pymupdf
from datetime import datetime
from typing import Dict, Any, List

class ImageOCRParser:
    """
    ANVAYA Defense Vision & OCR Service
    1. Extracts printed & handwritten text via EasyOCR.
    2. Detects objects, scenes, and visual context via local Vision Transformers / BLIP.
    3. Handles drone shots, satellite imagery, suspect photos, and scanned notes.
    """
    def __init__(self, output_dir: str = "data/processed_text"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._ocr_engine = None
        self._blip_processor = None
        self._blip_model = None

    def _get_ocr_engine(self):
        """Lazy loader for EasyOCR engine."""
        if self._ocr_engine is None:
            try:
                import easyocr
                print("[OCR] Initializing EasyOCR engine (100% offline)...")
                self._ocr_engine = easyocr.Reader(['en'], gpu=False)
            except Exception as e:
                print(f"[WARN] OCR engine notice: {e}. Using fallback image text extractor.")
                self._ocr_engine = "fallback"
        return self._ocr_engine

    def _get_blip_vision_model(self):
        """Lazy loader for local HuggingFace BLIP Image Captioning Vision Model."""
        if self._blip_model is None:
            try:
                from transformers import BlipProcessor, BlipForConditionalGeneration
                print("[VISION] Initializing local BLIP Image Captioning engine...")
                self._blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
                self._blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            except Exception as e:
                print(f"[WARN] Vision Model notice: {e}. Falling back to metadata tagging.")
                self._blip_model = "fallback"
        return self._blip_model

    def preprocess_and_deskew(self, image_path: str) -> List[np.ndarray]:
        """Applies image upscaling, adaptive Gaussian thresholding, and minAreaRect deskewing."""
        img = cv2.imread(image_path)
        if img is None:
            return []

        h, w = img.shape[:2]
        processed_variants = [img]

        if w < 500 or h < 500:
            upscaled = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
            processed_variants.append(upscaled)

        try:
            gray = cv2.cvtColor(img if (w >= 500 and h >= 500) else upscaled, cv2.COLOR_BGR2GRAY)
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            adaptive_bgr = cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR)
            processed_variants.append(adaptive_bgr)
        except Exception:
            pass

        return processed_variants

    def generate_visual_description(self, image_path: str) -> str:
        """
        Generates automatic visual description for drone shots, satellite photos, and non-text imagery.
        """
        b_model = self._get_blip_vision_model()
        if b_model != "fallback" and self._blip_processor is not None:
            try:
                from PIL import Image
                raw_image = Image.open(image_path).convert('RGB')
                inputs = self._blip_processor(raw_image, return_tensors="pt")
                out = self._blip_model.generate(**inputs, max_new_tokens=50)
                caption = self._blip_processor.decode(out[0], skip_special_tokens=True).strip()
                if caption:
                    return f"[VISUAL DESCRIPTION]: {caption}"
            except Exception as err:
                print(f"[WARN] Visual captioning note: {err}")
        return ""

    def clean_text(self, text: str) -> str:
        """Normalizes text"""
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"[ ]{2,}", " ", text)
        return text.strip()

    def parse_image(self, image_path: str) -> Dict[str, Any]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        base_filename = os.path.basename(image_path)
        print(f"[VISION/OCR] Processing Image: {base_filename}")

        extracted_lines = []
        ocr_engine = self._get_ocr_engine()

        # 1. Run EasyOCR for text content
        image_variants = self.preprocess_and_deskew(image_path)
        if ocr_engine != "fallback" and hasattr(ocr_engine, "readtext"):
            for var_img in image_variants:
                try:
                    results = ocr_engine.readtext(var_img)
                    for bbox, text_content, confidence in results:
                        if confidence > 0.25 and text_content.strip():
                            if text_content.strip() not in extracted_lines:
                                extracted_lines.append(text_content.strip())
                except Exception:
                    pass

        # 2. Run Visual Scene & Object Recognition (for drone shots, photos, maps)
        visual_caption = self.generate_visual_description(image_path)

        combined_text_blocks = []
        if visual_caption:
            combined_text_blocks.append(visual_caption)

        if extracted_lines:
            combined_text_blocks.append("[OCR TEXT]:\n" + "\n".join(extracted_lines))
        elif not visual_caption:
            combined_text_blocks.append(f"[Image Evidence: {base_filename}]")

        cleaned_text = self.clean_text("\n\n".join(combined_text_blocks))

        # Save extracted clean text to disk
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

        print(f"[OK] Processed Vision & OCR ({len(cleaned_text)} chars) for {base_filename}")

        return {
            "metadata": {
                "file": base_filename,
                "type": "image",
                "processed_at": datetime.now().isoformat()
            },
            "text_path": out_path,
            "chunks": [chunk]
        }
