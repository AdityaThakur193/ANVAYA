import os
import re
import hashlib
from typing import Dict, Any, List, Tuple
from .pdf_parser import PDFParser
from .image_ocr import ImageOCRParser
from .audio_transcriber import AudioTranscriber

class MasterIngestor:
    """
    ANVAYA Master Multimodal Ingestion Dispatcher & Deduplicator
    Automatically routes input evidence files (.pdf, .docx, .png, .jpg, .wav, .mp3)
    to specialized parsers and applies 64-bit SimHash deduplication (Hamming distance <= 3).
    """
    def __init__(self, data_dir: str = "data", simhash_threshold: int = 3):
        self.data_dir = data_dir
        self.simhash_threshold = simhash_threshold
        self.seen_simhashes: Dict[str, int] = {}  # file_name -> simhash 64-bit int

        self.pdf_parser = PDFParser(output_dir=os.path.join(data_dir, "processed_text"))
        self.image_parser = ImageOCRParser(output_dir=os.path.join(data_dir, "processed_text"))
        self.audio_parser = AudioTranscriber(output_dir=os.path.join(data_dir, "processed_text"))

    def compute_simhash(self, text: str) -> int:
        """Generates a 64-bit SimHash fingerprint over word bi-grams."""
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        tokens = clean_text.split()
        if not tokens:
            return 0

        bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens)-1)] if len(tokens) > 1 else tokens
        v = [0] * 64

        for token in bigrams:
            digest = hashlib.md5(token.encode('utf-8')).hexdigest()
            hash_int = int(digest[:16], 16)
            for i in range(64):
                bit = (hash_int >> i) & 1
                v[i] += 1 if bit else -1

        simhash = 0
        for i in range(64):
            if v[i] > 0:
                simhash |= (1 << i)
        return simhash

    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """Calculates bitwise Hamming distance between two 64-bit integers."""
        x = hash1 ^ hash2
        return bin(x).count('1')

    def is_duplicate(self, text: str, file_name: str) -> Tuple[bool, str]:
        """Checks if extracted document text is a near-duplicate of a previously ingested file."""
        if not text.strip():
            return False, ""

        current_hash = self.compute_simhash(text)
        for existing_file, existing_hash in self.seen_simhashes.items():
            if existing_file != file_name and existing_hash != 0:
                if self.hamming_distance(current_hash, existing_hash) <= self.simhash_threshold:
                    return True, existing_file

        self.seen_simhashes[file_name] = current_hash
        return False, ""

    def process_file(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        if ext in [".pdf", ".docx", ".doc", ".txt"]:
            res = self.pdf_parser.parse_pdf(file_path)
            chunks = res["page_chunks"]
            media_type = "pdf"
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
            res = self.image_parser.parse_image(file_path)
            chunks = res["chunks"]
            media_type = "image"
        elif ext in [".wav", ".mp3", ".m4a", ".flac", ".ogg"]:
            res = self.audio_parser.transcribe_audio(file_path)
            chunks = res["chunks"]
            media_type = "audio"
        else:
            raise ValueError(f"Unsupported evidence file format: {ext}")

        # Check SimHash near-duplicate guard across concatenated chunk text
        combined_text = " ".join([c["text"] for c in chunks])
        duplicate, matched_file = self.is_duplicate(combined_text, file_name)

        if duplicate:
            print(f"[INGEST SKIPPED] {file_name} is a near-duplicate of {matched_file} (SimHash h<={self.simhash_threshold})")
            return {
                "file_name": file_name,
                "media_type": media_type,
                "is_duplicate": True,
                "duplicate_of": matched_file,
                "chunks": []
            }

        return {
            "file_name": file_name,
            "media_type": media_type,
            "is_duplicate": False,
            "chunks": chunks
        }
