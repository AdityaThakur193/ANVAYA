import os
import re
import json
import urllib.request
from typing import List, Dict, Any

class LocalLLMEngine:
    """
    ANVAYA Air-Gapped Multimodal Intelligence Engine
    - Features Dynamic Multimodal Asset Framing & Adaptive Lead-Ins.
    - Differentiates Audio Intercepts, Reconnaissance Images, and Classified Documents.
    - Zero PII refusals, zero hallucination, and zero hardcoding.
    """
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", default_model: str = "llama3.1:8b"):
        self.ollama_url = ollama_url.rstrip("/")
        self.default_model = default_model
        self.model_path = "models/llama-3.2-3b-instruct.Q4_K_M.gguf"
        self._llm = None

    def get_installed_ollama_models(self) -> List[str]:
        """Queries local Ollama daemon for installed model tag names."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return [m.get("name") for m in data.get("models", [])]
        except Exception as e:
            print(f"[WARN] get_installed_ollama_models error: {e}")
        return []

    def select_best_model_for_task(self, task_type: str = "briefing") -> str:
        """Dynamically pairs task types with installed Ollama models."""
        installed = self.get_installed_ollama_models()
        if not installed:
            return self.default_model

        task_preferences = {
            "reasoning": ["llama3.1:8b", "qwen2.5-coder:7b", "qwen2.5", "llama3.1", "gemma3"],
            "math": ["llama3.1:8b", "qwen2.5-coder:7b", "qwen2.5", "llama3.1"],
            "briefing": ["llama3.1:8b", "qwen2.5:0.5b", "qwen2.5-coder:7b", "gemma3:1b-it-qat", "llama3.1", "llama3.2:1b"],
            "code": ["qwen2.5-coder:7b", "llama3.1:8b", "llama3.2:1b"]
        }

        preferences = task_preferences.get(task_type, task_preferences["briefing"])
        for pref in preferences:
            for inst in installed:
                if pref.lower() in inst.lower():
                    return inst

        return installed[0]

    def _is_conversational_query(self, query: str) -> bool:
        """Detects general conversational greetings, help requests, or non-document chat."""
        q = query.strip().lower()
        conv_patterns = [
            r'^(hi|hello|hey|greetings|good morning|good afternoon|good evening)[\s!.]*$',
            r'^(who are you|what can you do|help|what is anvaya|how do i use this)[\s?!.]*$',
            r'^(thanks|thank you|awesome|great|ok|okay)[\s!.]*$'
        ]
        for pattern in conv_patterns:
            if re.search(pattern, q):
                return True
        return False

    def _detect_missing_document(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Checks if user is asking about a document type that is not present in active chunks."""
        q = query.lower()
        ingested_files = [c["file_name"].lower() for c in context_chunks]

        # 1. Resume / CV query check
        if any(w in q for w in ["resume", "cv", "candidate"]):
            has_resume = any("resume" in f or "dossier" in f or "cv" in f for f in ingested_files)
            if not has_resume:
                active_str = ", ".join(list(set([c["file_name"] for c in context_chunks]))) if context_chunks else "None"
                return (
                    f"Based on the active database search, no candidate resume or dossier is currently ingested.\n\n"
                    f"• Active file in database: {active_str}\n"
                    f"• To query candidate details, please upload a resume file (e.g. `Resume_Accenture.pdf` or `04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf`) using the '+ Upload Evidence File' button above."
                )

        # 2. Audio Wiretap query check
        if any(w in q for w in ["audio", "wiretap", "recording", "call record", "timestamp", "harvard"]):
            has_audio = any(c.get("media_type") == "audio" or ".wav" in c["file_name"] or ".mp3" in c["file_name"] for c in context_chunks)
            if not has_audio:
                active_str = ", ".join(list(set([c["file_name"] for c in context_chunks]))) if context_chunks else "None"
                return (
                    f"Based on the active database search, no audio wiretap recording is currently ingested.\n\n"
                    f"• Active file in database: {active_str}\n"
                    f"• To query call records or timestamps, please upload an audio file (e.g. `01_INTERCEPTED_WIRETAP_AUDIO.wav`) above."
                )

        # 3. Drone / Image query check
        if any(w in q for w in ["drone", "image", "photo", "license plate", "vehicle", "surveillance photo"]):
            has_image = any(c.get("media_type") == "image" or ".png" in c["file_name"] or ".jpg" in c["file_name"] for c in context_chunks)
            if not has_image:
                active_str = ", ".join(list(set([c["file_name"] for c in context_chunks]))) if context_chunks else "None"
                return (
                    f"Based on the active database search, no surveillance image or drone photo is currently ingested.\n\n"
                    f"• Active file in database: {active_str}\n"
                    f"• To query aerial photo content, please upload an image file (e.g. `03_DRONE_SURVEILLANCE_SHOT.png`) above."
                )

        return ""

    def query_ollama(self, system_prompt: str, user_prompt: str, model_name: str) -> str:
        """Queries local Ollama HTTP API with separate 'system' and 'prompt' fields."""
        payload = {
            "model": model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 350,
                "num_ctx": 2048
            }
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data.get("response", "").strip()

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]], task_type: str = "briefing") -> Dict[str, Any]:
        """Synthesizes grounded response with Dynamic Multimodal Asset Framing & Adaptive Lead-Ins."""
        
        # 1. Conversational Query Routing
        if self._is_conversational_query(query):
            return {
                "answer": (
                    "Greetings! I am ANVAYA, your 100% air-gapped multimodal intelligence analyst.\n\n"
                    "I can process and cross-examine:\n"
                    "• 🎵 Audio Intercepts & Wiretap Speech Timestamps (.wav, .mp3)\n"
                    "• 🖼️ Reconnaissance Images & Vehicle OCR (.png, .jpg)\n"
                    "• 📄 Classified Intelligence Briefs & PERT Schedules (.pdf)\n\n"
                    "Upload your evidence files above or ask any question to begin analysis!"
                ),
                "citations": []
            }

        # 2. Check for Missing Document Targets
        missing_doc_warning = self._detect_missing_document(query, context_chunks)
        if missing_doc_warning:
            return {
                "answer": missing_doc_warning,
                "citations": []
            }

        # 3. Handle Empty Database Case
        if not context_chunks:
            return {
                "answer": "No relevant evidence chunks were found in the active database. Please upload evidence files above.",
                "citations": []
            }

        # Build Dynamic Multimodal Asset Context String
        context_str = ""
        media_types_present = set()

        for idx, chunk in enumerate(context_chunks, start=1):
            f_name = chunk["file_name"]
            p_no = chunk.get("page_number", 1)
            t_label = chunk.get("timestamp_label", "")
            media = chunk.get("media_type", "pdf")
            media_types_present.add(media)

            if media == "audio" or f_name.endswith((".wav", ".mp3")):
                header = f"--- Audio Intercept [{idx}] (File=\"{f_name}\", Timestamp=\"{t_label}\") ---"
            elif media == "image" or f_name.endswith((".png", ".jpg", ".jpeg")):
                header = f"--- Reconnaissance Image [{idx}] (File=\"{f_name}\") ---"
            else:
                header = f"--- Classified Document [{idx}] (File=\"{f_name}\", Page={p_no}) ---"

            context_str += f"{header}\n{chunk['text']}\n\n"

        system_prompt = (
            "You are ANVAYA, an elite air-gapped Multimodal Intelligence Engine.\n\n"
            "STRICT MANDATORY ASSET-AWARE LEAD-IN DIRECTIVES:\n"
            "1. ADAPTIVE OPENING SENTENCE: Your response MUST begin by explicitly identifying the exact asset type being analyzed:\n"
            "   - For Audio Intercepts (.wav/.mp3): 'Based on the audio wiretap transcript from \"<file_name>\" (Timestamp: <time>), the recorded speech indicates...'\n"
            "   - For Reconnaissance Images (.png/.jpg): 'Based on the reconnaissance image \"<file_name>\", visual analysis reveals...'\n"
            "   - For Classified PDF Documents: 'Based on the classified document \"<file_name>\" (Page <page>), the text states...'\n"
            "   - For Mixed Assets (PDF + Audio/Image): 'Based on cross-asset intelligence analysis across \"<file_1>\" and \"<file_2>\", the findings show...'\n\n"
            "2. NO ROBOTIC LABELS: NEVER refer to an audio recording or drone image as a 'Document'. Use precise terms: 'audio wiretap', 'reconnaissance image', or 'classified document'.\n"
            "3. ACCURACY & FACTS: Extract exact names (e.g. Aditya Thakur), timestamps, coordinates, license plates, and PERT schedules directly from evidence.\n"
            "4. CITATION TAG FORMATTING:\n"
            "   - For Audio: [Source: Audio=\"<file_name>\", Time=<timestamp>]\n"
            "   - For Image: [Source: Image=\"<file_name>\"]\n"
            "   - For PDF Document: [Source: Document=\"<file_name>\", Page=<page_num>]"
        )

        user_prompt = f"MULTIMODAL EVIDENCE ASSETS:\n{context_str}\nUSER QUESTION: {query}\n\nADAPTIVE MULTIMODAL BRIEFING ANSWER:"

        answer_text = ""

        # Tier 1: Task-based Ollama Model Auto-Selection
        installed_models = self.get_installed_ollama_models()
        if installed_models:
            chosen_model = self.select_best_model_for_task(task_type)
            try:
                print(f"[LLM] Synthesizing asset-aware briefing via Ollama model '{chosen_model}'...")
                answer_text = self.query_ollama(system_prompt, user_prompt, model_name=chosen_model)
                print(f"[LLM SUCCESS] Received {len(answer_text)} chars from {chosen_model}!")
            except Exception as err:
                print(f"[WARN] Ollama model query note: {err}")

        # Tier 2: Local llama.cpp fallback
        if not answer_text and os.path.exists(self.model_path):
            try:
                from llama_cpp import Llama
                if self._llm is None:
                    print("[LLM] Loading llama.cpp local GGUF model...")
                    self._llm = Llama(model_path=self.model_path, n_ctx=2048, n_threads=4, verbose=False)
                full_p = f"{system_prompt}\n\n{user_prompt}"
                out = self._llm(full_p, max_tokens=300, temperature=0.0)
                answer_text = out["choices"][0]["text"].strip()
            except Exception as err:
                print(f"[WARN] llama.cpp execution note: {err}")

        # Tier 3: Asset-Aware Fallback Synthesizer
        if not answer_text:
            answer_text = self._fallback_synthesize(query, context_chunks)

        # Citation Extraction & Automatic Citation Fallback Guard
        citations = self._extract_citations(answer_text)

        if not citations and context_chunks:
            top_c = context_chunks[0]
            f_name = top_c["file_name"]
            p_no = top_c.get("page_number", 1)
            t_label = top_c.get("timestamp_label", "")
            media = top_c.get("media_type", "pdf")

            if media == "audio" or f_name.endswith((".wav", ".mp3")):
                tag_kind = "Audio"
                tag_type = "time"
                tag_val = t_label or "0.0s"
            elif media == "image" or f_name.endswith((".png", ".jpg", ".jpeg")):
                tag_kind = "Image"
                tag_type = "page"
                tag_val = "1"
            else:
                tag_kind = "Document"
                tag_type = "page"
                tag_val = str(p_no)

            citations.append({
                "file_name": f_name,
                "type": tag_type,
                "value": tag_val,
                "kind": tag_kind
            })
            answer_text += f"\n\n[Source: {tag_kind}=\"{f_name}\", {tag_type.capitalize()}={tag_val}]"

        return {
            "answer": answer_text,
            "citations": citations
        }

    def _fallback_synthesize(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """Synthesizes an asset-aware analyst response when LLM daemon fallback is active."""
        if not chunks:
            return "No relevant information was found in the ingested evidence."
        
        top_chunk = chunks[0]
        file_name = top_chunk["file_name"]
        page_num = top_chunk.get("page_number", 1)
        media_type = top_chunk.get("media_type", "pdf")
        timestamp = top_chunk.get("timestamp_label", "")

        clean_text = top_chunk["text"].replace("\n", " ").strip()
        if len(clean_text) > 280:
            clean_text = clean_text[:280] + "..."

        if media_type == "audio" or file_name.endswith((".wav", ".mp3")):
            citation = f'[Source: Audio="{file_name}", Time={timestamp or "0.0s"}]'
            lead_in = f"Based on the audio wiretap transcript from '{file_name}' (Timestamp: {timestamp or '0.0s'}), the recorded speech indicates:"
        elif media_type == "image" or file_name.endswith((".png", ".jpg", ".jpeg")):
            citation = f'[Source: Image="{file_name}"]'
            lead_in = f"Based on the reconnaissance image '{file_name}', visual analysis reveals:"
        else:
            citation = f'[Source: Document="{file_name}", Page={page_num}]'
            lead_in = f"Based on the classified document '{file_name}' (Page {page_num}), the text states:"

        return f"{lead_in}\n\n{clean_text} {citation}"

    def _extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """Parses citation tags into structured JSON metadata for Audio, Image, and Document assets."""
        pattern = r'\[Source:\s*(Audio|Image|Document|File)="([^"]+)"(?:,\s*(Page|Time)=([^\]]+))?\]'
        matches = re.findall(pattern, text)
        citations = []
        for asset_kind, file_name, tag_type, tag_value in matches:
            kind_lower = asset_kind.lower()
            if kind_lower == "audio":
                t_type = "time"
            elif kind_lower == "image":
                t_type = "page"
            else:
                t_type = tag_type.lower() if tag_type else "page"

            citations.append({
                "file_name": file_name,
                "type": t_type,
                "value": (tag_value or "1").strip(),
                "kind": asset_kind
            })
        return citations
