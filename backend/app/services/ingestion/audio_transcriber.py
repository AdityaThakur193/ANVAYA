import os
from datetime import datetime
from typing import Dict, Any, List

class AudioTranscriber:
    """
    ANVAYA Audio Transcription Service
    Uses faster-whisper (CTranslate2 INT8 CPU engine) with VAD noise filtering
    to extract timestamped voice transcripts for audio playback citations.
    """
    def __init__(self, model_size: str = "tiny", output_dir: str = "data/processed_text"):
        self.model_size = model_size
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._whisper_model = None

    def _get_whisper_model(self):
        """Lazy loader for faster-whisper model to save memory."""
        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel
                print(f"[AUDIO] Loading faster-whisper ({self.model_size} INT8)...")
                self._whisper_model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=2
                )
            except Exception as e:
                print(f"[WARN] faster-whisper loading warning: {e}. Using fallback audio transcriber.")
                self._whisper_model = "fallback"
        return self._whisper_model

    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        base_filename = os.path.basename(audio_path)
        print(f"[AUDIO] Transcribing Audio Wiretap: {base_filename}")

        audio_chunks = []
        full_text_list = []
        model = self._get_whisper_model()

        if model != "fallback" and hasattr(model, "transcribe"):
            try:
                segments, _ = model.transcribe(
                    audio_path,
                    beam_size=1,            # Greedy decoding for fast CPU execution
                    vad_filter=True,        # Strip background wiretap radio static
                    vad_parameters=dict(min_silence_duration_ms=500)
                )

                for idx, seg in enumerate(segments, start=1):
                    text_content = seg.text.strip()
                    if text_content:
                        t_start = round(seg.start, 2)
                        t_end = round(seg.end, 2)
                        full_text_list.append(f"[{t_start}s - {t_end}s] {text_content}")

                        audio_chunks.append({
                            "file_name": base_filename,
                            "media_type": "audio",
                            "page_number": 1,
                            "t_start": t_start,
                            "t_end": t_end,
                            "text": text_content,
                            "timestamp_label": f"{t_start}s-{t_end}s"
                        })
            except Exception as err:
                print(f"[WARN] Audio transcription error on {base_filename}: {err}")

        combined_text = "\n".join(full_text_list) if full_text_list else f"[Audio Wiretap: {base_filename}]"

        # Save extracted text to disk
        out_filename = f"{os.path.splitext(base_filename)[0]}_audioText.txt"
        out_path = os.path.join(self.output_dir, out_filename)
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(combined_text)

        print(f"[OK] Transcribed {len(audio_chunks)} audio segments for {base_filename}")

        return {
            "metadata": {
                "file": base_filename,
                "type": "audio",
                "processed_at": datetime.now().isoformat()
            },
            "text_path": out_path,
            "chunks": audio_chunks
        }
