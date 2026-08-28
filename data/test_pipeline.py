import os
import sys

# Prepend backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.ingestion.master_ingestor import MasterIngestor
from app.services.vectorstore.vector_store import VectorStoreManager
from app.services.llm.local_llm import LocalLLMEngine

def test_full_pipeline():
    print("=" * 60)
    print("[TEST] ANVAYA End-to-End Multimodal Pipeline Test")
    print("=" * 60)

    sample_dir = os.path.join("data", "sample_case")
    files = [
        os.path.join(sample_dir, "sample_intel_report.pdf"),
        os.path.join(sample_dir, "sample_handwritten_note.png"),
        os.path.join(sample_dir, "sample_wiretap.wav")
    ]

    # 1. Test Ingestion
    ingestor = MasterIngestor(data_dir="data")
    all_chunks = []

    for f_path in files:
        if os.path.exists(f_path):
            res = ingestor.process_file(f_path)
            all_chunks.extend(res["chunks"])
            print(f"[INGEST OK] {res['file_name']} -> {len(res['chunks'])} chunks")

    # 2. Test Vector Indexing
    print("\n[INDEXING] Adding chunks into ChromaDB & SQLite FTS5...")
    vector_store = VectorStoreManager(data_dir="data")
    vector_store.add_chunks(all_chunks)

    # 3. Test Hybrid Search Query
    test_query = "What is the convoy departure time and meeting location?"
    print(f"\n[QUERY] Executing Hybrid Search for: '{test_query}'")
    retrieved = vector_store.hybrid_search(test_query, top_k=3)

    for rank, chunk in enumerate(retrieved, start=1):
        print(f"  Rank #{rank} [RRF: {chunk.get('rrf_score')}] -> File: {chunk['file_name']} (Page/Time: {chunk.get('page_number') or chunk.get('timestamp_label')})")
        print(f"    Text: {chunk['text'][:120]}...\n")

    # 4. Test LLM Grounded Synthesis
    print("[LLM SYNTHESIS] Generating grounded intelligence response...")
    llm = LocalLLMEngine()
    synthesis = llm.generate_response(test_query, retrieved)

    print("\n" + "=" * 60)
    print("GROUNDED INTELLIGENCE BRIEFING ANSWER:")
    print("=" * 60)
    print(synthesis["answer"])
    print("=" * 60)
    print(f"Parsed Citations: {synthesis['citations']}")

if __name__ == "__main__":
    test_full_pipeline()
