import os
from datetime import datetime
from typing import Dict, Any, List

class AudioTranscriber:
    """
    ANVAYA Defense Audio Transcription Service
    Auto-detects the highest quality local Whisper model (small -> base -> tiny)
    using faster-whisper or OpenAI whisper with VAD noise filtering.
    """
    def __init__(self, model_size: str = "base", output_dir: str = "data/processed_text"):
        self.model_size = model_size
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._whisper_model = None
        self._engine_type = None

    def _get_whisper_model(self):
        """Lazy loader: Auto-detects and loads the best available Whisper model."""
        if self._whisper_model is None:
            # 1. Try faster-whisper (CTranslate2 INT8 CPU Engine)
            model_candidates = [self.model_size, "small", "base", "tiny"]
            # Deduplicate candidate list while preserving order
            unique_candidates = list(dict.fromkeys(model_candidates))

            try:
                from faster_whisper import WhisperModel
                for m_size in unique_candidates:
                    try:
                        print(f"[AUDIO] Attempting to load faster-whisper ('{m_size}' INT8)...")
                        self._whisper_model = WhisperModel(
                            m_size,
                            device="cpu",
                            compute_type="int8",
                            cpu_threads=4
                        )
                        self._engine_type = "faster-whisper"
                        print(f"[AUDIO] [SUCCESS] Loaded faster-whisper ('{m_size}')")
                        break
                    except Exception as err:
                        print(f"[AUDIO] Notice loading '{m_size}': {err}")
            except Exception:
                pass

            # 2. Try OpenAI whisper library fallback if faster-whisper is not available
            if self._whisper_model is None:
                try:
                    import whisper
                    for m_size in unique_candidates:
                        try:
                            print(f"[AUDIO] Attempting to load OpenAI whisper ('{m_size}')...")
                            self._whisper_model = whisper.load_model(m_size)
                            self._engine_type = "openai-whisper"
                            print(f"[AUDIO] [SUCCESS] Loaded OpenAI whisper ('{m_size}')")
                            break
                        except Exception as err:
                            print(f"[AUDIO] Notice loading openai-whisper '{m_size}': {err}")
                except Exception:
                    pass

            if self._whisper_model is None:
                print("[WARN] Whisper models absent. Using fallback audio transcriber.")
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

        if self._engine_type == "faster-whisper" and hasattr(model, "transcribe"):
            try:
                segments, _ = model.transcribe(
                    audio_path,
                    beam_size=3,            # Beam search size 3 for higher accuracy
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
                print(f"[WARN] faster-whisper transcription error: {err}")

        elif self._engine_type == "openai-whisper" and hasattr(model, "transcribe"):
            try:
                res = model.transcribe(audio_path)
                for seg in res.get("segments", []):
                    text_content = seg.get("text", "").strip()
                    if text_content:
                        t_start = round(seg.get("start", 0.0), 2)
                        t_end = round(seg.get("end", 0.0), 2)
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
                print(f"[WARN] openai-whisper transcription error: {err}")

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
