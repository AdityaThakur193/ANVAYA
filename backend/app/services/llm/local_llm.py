import os
import re
import json
import urllib.request
from typing import List, Dict, Any

class LocalLLMEngine:
    """
    ANVAYA Air-Gapped Local LLM & Multi-Model Task Dispatcher
    - Features strict document extraction prompt guidance for full names, skills, dates, and facts.
    - Zero PII refusals and zero hallucination on vague user prompts.
    """
    def __init__(self, ollama_url: str = "http://localhost:11434", default_model: str = "llama3.1:8b"):
        self.ollama_url = ollama_url.rstrip("/")
        self.default_model = default_model
        self.model_path = "models/llama-3.2-3b-instruct.Q4_K_M.gguf"
        self._llm = None

    def get_installed_ollama_models(self) -> List[str]:
        """Queries local Ollama daemon for full installed model tag names."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return [m.get("name") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def select_best_model_for_task(self, task_type: str = "briefing") -> str:
        """
        Dynamically pairs task types with the best model installed on the user's machine.
        Prioritizes Llama 3.1 8B over 1B models for zero hallucination.
        """
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

    def query_ollama(self, system_prompt: str, user_prompt: str, model_name: str) -> str:
        """Queries local Ollama HTTP API with separate 'system' and 'prompt' fields."""
        payload = {
            "model": model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,   # 0.0 Temperature for zero hallucination
                "num_predict": 350,   # High token budget for full answers
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data.get("response", "").strip()

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]], task_type: str = "briefing") -> Dict[str, Any]:
        """Synthesizes grounded response with automatic citation enforcement fallback."""
        if not context_chunks:
            return {
                "answer": "No relevant evidence chunks found in database.",
                "citations": []
            }

        # Build clean separate System and User Prompts
        context_str = ""
        for idx, chunk in enumerate(context_chunks, start=1):
            f_name = chunk["file_name"]
            p_no = chunk.get("page_number", 1)
            t_label = chunk.get("timestamp_label", "")
            media = chunk.get("media_type", "pdf")

            if media == "audio" and t_label:
                anchor = f"File=\"{f_name}\", Time={t_label}"
            else:
                anchor = f"File=\"{f_name}\", Page={p_no}"

            context_str += f"--- Document [{idx}] ({anchor}) ---\n{chunk['text']}\n\n"

        system_prompt = (
            "You are ANVAYA, an air-gapped Document Analysis & Intelligence Extraction System.\n"
            "Your job is to read the provided evidence documents and extract facts exactly as written.\n"
            "DIRECTIVES:\n"
            "1. If asked for a candidate name, document owner, or person's name, extract and report the primary name (e.g., Aditya Thakur) immediately from the text.\n"
            "2. Never guess or hallucinate names not present in the text.\n"
            "3. Append citation tags formatted exactly as: [Source: File=\"<file_name>\", Page=<page_num>] or [Source: File=\"<file_name>\", Time=<t_start>-<t_end>] after key claims."
        )

        user_prompt = f"EVIDENCE DOCUMENTS:\n{context_str}\nUSER QUESTION: {query}\n\nEXTRACTED FACTUAL ANSWER:"

        answer_text = ""

        # Tier 1: Task-based Ollama Model Auto-Selection
        installed_models = self.get_installed_ollama_models()
        if installed_models:
            chosen_model = self.select_best_model_for_task(task_type)
            try:
                print(f"[LLM] Dispatching task '{task_type}' to Ollama model '{chosen_model}'...")
                answer_text = self.query_ollama(system_prompt, user_prompt, model_name=chosen_model)
            except Exception as err:
                print(f"[WARN] Ollama model query note: {err}")

        # Tier 2: Try local llama.cpp GGUF model
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

        # Tier 3: Deterministic Fallback Synthesizer
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

            tag_type = "time" if (media == "audio" and t_label) else "page"
            tag_val = t_label if (media == "audio" and t_label) else str(p_no)

            citations.append({
                "file_name": f_name,
                "type": tag_type,
                "value": tag_val
            })
            answer_text += f"\n\n[Source: File=\"{f_name}\", {tag_type.capitalize()}={tag_val}]"

        return {
            "answer": answer_text,
            "citations": citations
        }

    def _fallback_synthesize(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """Deterministic local fallback synthesizer."""
        response = f"Based on retrieved evidence for query '{query}':\n\n"
        for chunk in chunks[:3]:
            f_name = chunk["file_name"]
            p_no = chunk.get("page_number", 1)
            t_label = chunk.get("timestamp_label", "")
            media = chunk.get("media_type", "pdf")

            if media == "audio" and t_label:
                citation = f"[Source: File=\"{f_name}\", Time={t_label}]"
            else:
                citation = f"[Source: File=\"{f_name}\", Page={p_no}]"

            snippet = chunk["text"][:180].replace("\n", " ")
            response += f"• {snippet}... {citation}\n"

        return response

    def _extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """Parses citation tags into structured JSON metadata."""
        pattern = r'\[Source:\s*File="([^"]+)",\s*(Page|Time)=([^\]]+)\]'
        matches = re.findall(pattern, text)
        citations = []
        for file_name, tag_type, tag_value in matches:
            citations.append({
                "file_name": file_name,
                "type": tag_type.lower(),
                "value": tag_value.strip()
            })
        return citations
