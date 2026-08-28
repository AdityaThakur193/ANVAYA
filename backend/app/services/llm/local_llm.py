import os
import re
from typing import List, Dict, Any

class LocalLLMEngine:
    """
    ANVAYA Air-Gapped Local LLM Engine
    Executes quantized Llama 3.2 3B Instruct GGUF locally via llama.cpp.
    Enforces strict Source-Anchored System Prompts with zero external API calls.
    """
    def __init__(self, model_path: str = "models/llama-3.2-3b-instruct.Q4_K_M.gguf"):
        self.model_path = model_path
        self._llm = None

    def _get_llm(self):
        """Lazy loader for llama.cpp local quantized LLM engine."""
        if self._llm is None and os.path.exists(self.model_path):
            try:
                from llama_cpp import Llama
                print("[LLM] Loading Llama 3.2 3B GGUF model (100% offline air-gapped)...")
                self._llm = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,
                    n_threads=4,         # Physical CPU cores for optimal latency
                    n_batch=512,
                    use_mlock=True,      # Lock weights in RAM to prevent disk paging
                    verbose=False
                )
            except Exception as e:
                print(f"[WARN] llama.cpp loading warning: {e}. Using deterministic local RAG fallback synthesizer.")
                self._llm = "fallback"
        return self._llm

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
            "You are ANVAYA, an air-gapped NTRO Technical Intelligence Analysis Assistant.\n"
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

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesizes grounded response strictly anchored to retrieved evidence chunks."""
        if not context_chunks:
            return {
                "answer": "No relevant evidence chunks found in database.",
                "citations": []
            }

        prompt = self.build_source_anchored_prompt(query, context_chunks)
        llm = self._get_llm()

        if llm != "fallback" and hasattr(llm, "__call__"):
            try:
                output = llm(
                    prompt,
                    max_tokens=300,
                    temperature=0.1,    # Low temperature for zero hallucination
                    top_p=0.9,
                    stop=["[END]", "USER QUERY:"]
                )
                answer_text = output["choices"][0]["text"].strip()
            except Exception as err:
                print(f"[WARN] Local LLM execution error: {err}")
                answer_text = self._fallback_synthesize(query, context_chunks)
        else:
            answer_text = self._fallback_synthesize(query, context_chunks)

        citations = self._extract_citations(answer_text)

        return {
            "answer": answer_text,
            "citations": citations
        }

    def _fallback_synthesize(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """Deterministic local fallback synthesizer when GGUF binary is not loaded."""
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
        """Parses citation tags from answer text into structured JSON metadata."""
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
