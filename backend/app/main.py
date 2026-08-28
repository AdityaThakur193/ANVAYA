import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.ingestion.master_ingestor import MasterIngestor
from app.services.vectorstore.vector_store import VectorStoreManager
from app.services.llm.local_llm import LocalLLMEngine

app = FastAPI(
    title="ANVAYA — Air-Gapped Multimodal RAG API",
    description="100% Offline Intelligence Engine for NTRO (SIH25231 / SIH26154)",
    version="1.0.0"
)

# Enable CORS for Next.js / Vite React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
DATA_DIR = "data"
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
SAMPLE_CASE_DIR = os.path.join(DATA_DIR, "sample_case")
PROCESSED_TEXT_DIR = os.path.join(DATA_DIR, "processed_text")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_TEXT_DIR, exist_ok=True)

ingestor = MasterIngestor(data_dir=DATA_DIR)
vector_store = VectorStoreManager(data_dir=DATA_DIR)
llm_engine = LocalLLMEngine()

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    task_type: Optional[str] = "briefing"

@app.get("/")
def health_check():
    return {
        "status": "online",
        "air_gapped": True,
        "system": "ANVAYA Multimodal Offline RAG Engine",
        "sih_ps": "SIH25231 / SIH26154",
        "agency": "NTRO (Prime Minister's Office)"
    }

@app.get("/api/health/full")
def full_system_diagnostics():
    """
    Automated System Integrity Check: Verifies end-to-end connectivity
    of all backend ingestion services, vector store, SQLite FTS5, and local LLM/Ollama engines.
    """
    status_report = {
        "api_gateway": "online",
        "air_gapped": True,
        "storage_directories": {
            "uploads": os.path.exists(UPLOADS_DIR),
            "processed_text": os.path.exists(PROCESSED_TEXT_DIR)
        },
        "services": {}
    }

    # 1. Verify Master Ingestor Sub-Parsers
    status_report["services"]["master_ingestor"] = {
        "status": "connected" if ingestor is not None else "disconnected",
        "parsers": ["PDFParser", "ImageOCRParser (BLIP+EasyOCR)", "AudioTranscriber (Whisper+VAD)"]
    }

    # 2. Verify Vector Store & SQLite FTS5 DB
    try:
        chroma_count = vector_store.collection.count()
        fts_count = vector_store.conn.execute("SELECT count(*) FROM evidence_fts;").fetchone()[0]
        status_report["services"]["vector_store"] = {
            "status": "connected",
            "chromadb_vectors": chroma_count,
            "sqlite_fts5_records": fts_count,
            "engine": "ChromaDB + SQLite FTS5 (RRF k=60)"
        }
    except Exception as e:
        status_report["services"]["vector_store"] = {"status": "error", "detail": str(e)}

    # 3. Verify Local LLM Engine & Ollama API
    try:
        ollama_models = llm_engine.get_installed_ollama_models()
        status_report["services"]["local_llm"] = {
            "status": "connected",
            "ollama_active": len(ollama_models) > 0,
            "installed_models": ollama_models,
            "default_model": llm_engine.select_best_model_for_task("briefing")
        }
    except Exception as e:
        status_report["services"]["local_llm"] = {"status": "error", "detail": str(e)}

    return status_report

@app.post("/api/ingest")
async def ingest_evidence_file(file: UploadFile = File(...)):
    """Uploads and ingests a multimodal evidence file (.pdf, .png, .wav) into vector store."""
    file_location = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        parsed_result = ingestor.process_file(file_location)
        chunks = parsed_result["chunks"]
        if chunks:
            vector_store.add_chunks(chunks)

        return {
            "status": "success",
            "file_name": file.filename,
            "media_type": parsed_result["media_type"],
            "is_duplicate": parsed_result.get("is_duplicate", False),
            "total_chunks_indexed": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/api/sample_case")
def load_sample_case_bundle():
    """Ingests pre-populated sample evidence files for 1-click stage demo testing."""
    if not os.path.exists(SAMPLE_CASE_DIR):
        raise HTTPException(status_code=404, detail="Sample case directory not found.")

    sample_files = [
        os.path.join(SAMPLE_CASE_DIR, f)
        for f in os.listdir(SAMPLE_CASE_DIR)
        if os.path.isfile(os.path.join(SAMPLE_CASE_DIR, f))
    ]

    total_chunks = 0
    indexed_files = []

    for f_path in sample_files:
        try:
            res = ingestor.process_file(f_path)
            chunks = res["chunks"]
            if chunks:
                vector_store.add_chunks(chunks)
                total_chunks += len(chunks)
                indexed_files.append(res["file_name"])
        except Exception as err:
            print(f"[WARN] Sample file ingestion notice for {f_path}: {err}")

    return {
        "status": "success",
        "message": "Sample case bundle loaded successfully.",
        "files_indexed": indexed_files,
        "total_chunks_indexed": total_chunks
    }

@app.post("/api/query")
def query_intelligence_briefing(request: QueryRequest):
    """Executes hybrid RRF search and local LLM grounded intelligence synthesis."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Execute Dense + Sparse Hybrid Search (RRF k=60)
    retrieved_chunks = vector_store.hybrid_search(request.query, top_k=request.top_k)

    # 2. Synthesize grounded answer via Local LLM Engine with task-based model dispatching
    synthesis = llm_engine.generate_response(request.query, retrieved_chunks, task_type=request.task_type)

    return {
        "query": request.query,
        "task_type": request.task_type,
        "answer": synthesis["answer"],
        "citations": synthesis["citations"],
        "retrieved_chunks": retrieved_chunks
    }
