import os
import re
import json
import urllib.request
from typing import List, Dict, Any

class LocalLLMEngine:
    """
    ANVAYA Air-Gapped Local LLM & Multi-Model Task Dispatcher
    - Queries local Ollama API (http://localhost:11434) to auto-select the best model
      for each task (e.g. reasoning/math vs. intelligence briefings).
    - Preserves full model tags (llama3.2:latest, qwen2.5:latest, etc.) for zero-error execution.
    - Falls back to llama.cpp GGUF and deterministic RAG synthesis if Ollama is offline.
    """
    def __init__(self, ollama_url: str = "http://localhost:11434", default_model: str = "llama3.2:latest"):
        self.ollama_url = ollama_url.rstrip("/")
        self.default_model = default_model
        self.model_path = "models/llama-3.2-3b-instruct.Q4_K_M.gguf"
        self._llm = None

    def get_installed_ollama_models(self) -> List[str]:
        """Queries local Ollama daemon for full installed model tag names."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return [m.get("name") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def select_best_model_for_task(self, task_type: str = "briefing") -> str:
        """
        Dynamically pairs task types with the best model installed on the user's machine:
        - 'math' / 'reasoning' -> deepseek-r1, qwen2.5, llama3.1, mistral
        - 'briefing' / 'rag'   -> llama3.2, gemma3, mistral, llama3.1
        - 'code'               -> qwen2.5-coder, codellama
        """
        installed = self.get_installed_ollama_models()
        if not installed:
            return self.default_model

        task_preferences = {
            "reasoning": ["qwen2.5", "deepseek-r1", "llama3.1", "mistral", "llama3.2"],
            "math": ["qwen2.5", "deepseek-r1", "llama3.1", "mistral", "llama3.2"],
            "briefing": ["llama3.2", "gemma3", "llama3.1", "qwen2.5", "mistral"],
            "code": ["qwen2.5-coder", "codellama", "deepseek-r1", "llama3.2"]
        }

        preferences = task_preferences.get(task_type, task_preferences["briefing"])
        
        for pref in preferences:
            for inst in installed:
                if pref in inst.lower():
                    return inst

        return installed[0]

    def query_ollama(self, prompt: str, model_name: str) -> str:
        """Queries local Ollama HTTP API with zero cloud API dependencies."""
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for zero hallucination
                "num_predict": 400
            }
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data.get("response", "").strip()

    def build_source_anchored_prompt(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Constructs strict source-anchored system prompt enforcing citation proof."""
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

            context_str += f"--- Evidence Chunk [{idx}] ({anchor}) ---\n{chunk['text']}\n\n"

        system_prompt = (
            "You are ANVAYA, an air-gapped Technical Intelligence Analysis Assistant.\n"
            "Your task is to answer the officer's query strictly using the provided Evidence Chunks below.\n\n"
            "STRICT CONSTRAINTS:\n"
            "1. Do NOT use outside knowledge or make up facts. If information is not in the chunks, state 'Information not found in available evidence.'\n"
            "2. Every factual claim MUST be followed immediately by a Citation Tag formatted EXACTLY as:\n"
            "   - For PDF Documents or Images: [Source: File=\"<file_name>\", Page=<page_num>]\n"
            "   - For Audio Wiretaps: [Source: File=\"<file_name>\", Time=<t_start>-<t_end>]\n\n"
            f"{context_str}"
            f"USER QUERY: {query}\n\n"
            "GROUNDED INTELLIGENCE BRIEFING:\n"
        )
        return system_prompt

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]], task_type: str = "briefing") -> Dict[str, Any]:
        """Synthesizes grounded response using task-based Ollama model routing, llama.cpp, or Fallback Synthesizer."""
        if not context_chunks:
            return {
                "answer": "No relevant evidence chunks found in database.",
                "citations": []
            }

        prompt = self.build_source_anchored_prompt(query, context_chunks)
        answer_text = ""

        # Tier 1: Task-based Ollama Model Auto-Selection
        installed_models = self.get_installed_ollama_models()
        if installed_models:
            chosen_model = self.select_best_model_for_task(task_type)
            try:
                print(f"[LLM] Dispatching task '{task_type}' to Ollama model '{chosen_model}'...")
                answer_text = self.query_ollama(prompt, model_name=chosen_model)
            except Exception as err:
                print(f"[WARN] Ollama model query note: {err}")

        # Tier 2: Try local llama.cpp GGUF model
        if not answer_text and os.path.exists(self.model_path):
            try:
                from llama_cpp import Llama
                if self._llm is None:
                    print("[LLM] Loading llama.cpp local GGUF model...")
                    self._llm = Llama(model_path=self.model_path, n_ctx=2048, n_threads=4, verbose=False)
                out = self._llm(prompt, max_tokens=300, temperature=0.1)
                answer_text = out["choices"][0]["text"].strip()
            except Exception as err:
                print(f"[WARN] llama.cpp execution note: {err}")

        # Tier 3: Deterministic Fallback Synthesizer
        if not answer_text:
            answer_text = self._fallback_synthesize(query, context_chunks)

        citations = self._extract_citations(answer_text)

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
