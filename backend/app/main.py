import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.ingestion.master_ingestor import MasterIngestor
from app.services.vectorstore.vector_store import VectorStoreManager
from app.services.llm.local_llm import LocalLLMEngine

app = FastAPI(
    title="ANVAYA — Air-Gapped Multimodal RAG API",
    description="100% Offline Multi-Case Intelligence Engine for NTRO (SIH25231 / SIH26154)",
    version="1.1.0"
)

# Real-time HTTP Request Terminal Logger Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n--> [FASTAPI REQUEST] {request.method} {request.url.path}", flush=True)
    response = await call_next(request)
    print(f"<-- [FASTAPI RESPONSE] {response.status_code} {request.url.path}", flush=True)
    return response

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
    case_id: Optional[str] = "default_case"
    file_filter: Optional[str] = "ALL"

@app.get("/")
def health_check():
    print("[ROOT CHECK] Health check ok", flush=True)
    return {
        "status": "online",
        "air_gapped": True,
        "system": "ANVAYA Multimodal Offline RAG Engine",
        "sih_ps": "SIH25231 / SIH26154",
        "agency": "NTRO (Prime Minister's Office)"
    }

@app.get("/api/health/full")
def full_system_diagnostics():
    """Automated System Integrity Diagnostic Endpoint."""
    print("[DIAGNOSTICS] Full system integrity diagnostics requested.", flush=True)
    status_report = {
        "api_gateway": "online",
        "air_gapped": True,
        "storage_directories": {
            "uploads": os.path.exists(UPLOADS_DIR),
            "processed_text": os.path.exists(PROCESSED_TEXT_DIR)
        },
        "services": {}
    }

    status_report["services"]["master_ingestor"] = {
        "status": "connected" if ingestor is not None else "disconnected",
        "parsers": ["PDFParser", "ImageOCRParser (BLIP+EasyOCR)", "AudioTranscriber (Whisper+VAD)"]
    }

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

@app.get("/api/documents")
def get_documents(case_id: Optional[str] = None):
    """Returns list of all unique ingested documents for UI document filtering."""
    docs = vector_store.get_indexed_documents(case_id=case_id)
    return {"documents": docs}

@app.delete("/api/reset")
def reset_all_data():
    """Wipes 100% of all vector databases, FTS indexes, and uploaded files."""
    print("[RESET API] Purging all vector databases & files...", flush=True)
    vector_store.purge_all_data()

    # Clear uploads folder
    for f in os.listdir(UPLOADS_DIR):
        if f != ".gitkeep":
            p = os.path.join(UPLOADS_DIR, f)
            if os.path.isfile(p):
                os.remove(p)

    return {"status": "success", "message": "All vector databases, FTS indexes, and uploaded files cleared cleanly."}

@app.post("/api/ingest")
async def ingest_evidence_file(file: UploadFile = File(...), case_id: str = Form("default_case")):
    """Uploads and ingests a multimodal evidence file (.pdf, .png, .wav) with case_id tag."""
    print(f"[INGESTION RECEIVED] File: '{file.filename}' | Case ID: '{case_id}'", flush=True)
    file_location = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        print(f"[PARSING FILE] Running MasterIngestor on '{file.filename}'...", flush=True)
        parsed_result = ingestor.process_file(file_location)
        chunks = parsed_result["chunks"]
        if chunks:
            print(f"[VECTOR INDEXING] Adding {len(chunks)} chunks into ChromaDB & SQLite FTS5 (Case: '{case_id}')...", flush=True)
            vector_store.add_chunks(chunks, case_id=case_id)

        print(f"[INGESTION SUCCESS] '{file.filename}' indexed cleanly ({len(chunks)} chunks)!", flush=True)
        return {
            "status": "success",
            "file_name": file.filename,
            "case_id": case_id,
            "media_type": parsed_result["media_type"],
            "is_duplicate": parsed_result.get("is_duplicate", False),
            "duplicate_of": parsed_result.get("duplicate_of", ""),
            "total_chunks_indexed": len(chunks)
        }
    except Exception as e:
        print(f"[INGESTION ERROR] {file.filename}: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/api/query")
def query_intelligence_briefing(request: QueryRequest):
    """Executes hybrid RRF search with case isolation & document-scoped filtering."""
    print(f"[QUERY RECEIVED] '{request.query}' (Case: {request.case_id} | File Filter: {request.file_filter})", flush=True)
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Execute Dense + Sparse Hybrid Search with Case Isolation & File Scoping
    print(f"[HYBRID SEARCH] Executing ChromaDB + SQLite FTS5 RRF search...", flush=True)
    retrieved_chunks = vector_store.hybrid_search(
        query=request.query,
        case_id=request.case_id,
        file_filter=request.file_filter,
        top_k=request.top_k
    )

    print(f"[LLM SYNTHESIS] Generating response via LocalLLMEngine...", flush=True)
    synthesis = llm_engine.generate_response(request.query, retrieved_chunks, task_type=request.task_type)

    print(f"[QUERY SUCCESS] Response generated with {len(synthesis['citations'])} citations!", flush=True)
    return {
        "query": request.query,
        "case_id": request.case_id,
        "file_filter": request.file_filter,
        "task_type": request.task_type,
        "answer": synthesis["answer"],
        "citations": synthesis["citations"],
        "retrieved_chunks": retrieved_chunks
    }
