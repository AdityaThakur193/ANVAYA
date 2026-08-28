# 🛡️ ANVAYA (अन्वय)
### Multimodal Offline Air-Gapped Intelligence RAG Platform

[![SIH Problem Statement](https://img.shields.io/badge/SIH%202025%2F2026-SIH25231%20%7C%20SIH26154-orange.svg)](https://sih.gov.in)
[![Sponsoring Agency](https://img.shields.io/badge/Agency-NTRO%20(Prime%20Minister's%20Office)-blue.svg)](https://ntro.gov.in)
[![Air-Gapped Status](https://img.shields.io/badge/Air--Gapped-100%25%20Offline%20(Zero%20Cloud)-green.svg)]()

---

## 📌 About The Project

**ANVAYA** (Sanskrit: *अन्वय* — meaning *Synthesis, Connection & Grounded Relation*) is an enterprise-grade, 100% offline, air-gapped **Multimodal Retrieval-Augmented Generation (RAG)** platform built for the **National Technical Research Organisation (NTRO)** under **Smart India Hackathon (`SIH25231` / `SIH26154`)**.

Designed specifically for secure, air-gapped environments with **zero internet connectivity**, ANVAYA ingests multi-format evidence caches—including PDF reports, scanned handwritten notes/screenshots, zero-text drone shots, and recorded audio wiretaps—into a unified semantic retrieval index. It leverages local quantized Large Language Models (Ollama / Llama 3.2 3B / Qwen 2.5 / DeepSeek R1) to synthesize grounded, hallucination-free intelligence briefings equipped with **clickable page and millisecond audio timestamp citations**.

---

## 🛠️ Technology Stack

* **Frontend Console**: Vite + React 19 + TypeScript + Tailwind CSS
* **Backend Engine**: Python 3.11/3.13 + FastAPI + Uvicorn
* **PDF Ingestion (`pdf_parser.py`)**: PyMuPDF (`fitz`) layout block sorting + spatial bounding boxes `[x0,y0,x1,y1]` + Markdown grid table extraction
* **Image OCR & Vision (`image_ocr.py`)**: EasyOCR + OpenCV adaptive deskewing/scaling + HuggingFace BLIP (`Salesforce/blip-image-captioning-base`) visual scene recognition
* **Audio Transcription (`audio_transcriber.py`)**: `faster-whisper` (INT8 CPU engine) + Voice Activity Detection (`vad_filter=True`) + timestamped segmenting
* **Master Ingestor (`master_ingestor.py`)**: Multimodal auto-routing + 64-bit SimHash bitwise near-duplicate deduplication ($h \le 3$)
* **Hybrid Vector Store (`vector_store.py`)**: ChromaDB + `BAAI/bge-small-en-v1.5` embeddings (384D) + SQLite FTS5 BM25 keyword search with Reciprocal Rank Fusion (RRF $k=60$) & WAL thread lock protection
* **Local LLM Engine (`local_llm.py`)**: Multi-Model Task Dispatcher (Ollama API / `llama.cpp` GGUF) with source-anchored system prompts & regex citation parser
* **API Gateway (`main.py`)**: FastAPI REST endpoints + CORS + automated full system integrity diagnostics (`/api/health/full`)

---

## 📁 Repository Folder Structure

```text
ANVAYA/
├── README.md                           # Documentation & Setup Guide
├── .gitignore                          # Clean open-source ignore filters
├── backend/                            # Python FastAPI Server Engine
│   └── app/
│       ├── main.py                     # FastAPI REST API Gateway & Health Diagnostics
│       └── services/                   # 7 Core Multimodal RAG Modules
│           ├── ingestion/
│           │   ├── pdf_parser.py       # Layout-aware PDF & Markdown table parser
│           │   ├── image_ocr.py        # OCR + BLIP visual image captioner
│           │   ├── audio_transcriber.py# Timestamped Whisper audio transcriber
│           │   └── master_ingestor.py  # Dispatcher & SimHash deduplicator
│           ├── vectorstore/
│           │   └── vector_store.py     # ChromaDB + SQLite FTS5 RRF hybrid store
│           └── llm/
│               └── local_llm.py        # Task-based Ollama model dispatcher
├── frontend/                           # Vite + React 19 Analyst UI Console
│   ├── src/
│   │   ├── App.tsx                     # Master Analyst Console UI
│   │   ├── services/
│   │   │   └── api.ts                  # Axios backend API client
│   │   └── main.tsx
│   ├── index.html
│   ├── tsconfig.json                   # Vite TypeScript configuration
│   └── package.json
└── data/                               # Local Storage & Vector Database
    ├── processed_text/                 # Extracted text outputs
    ├── chroma_db/                      # Persistent HNSW vector database
    ├── anvaya_fts.db                   # SQLite FTS5 BM25 keyword index
    └── uploads/                        # Uploaded evidence file cache
```

---

## 🚀 Quick Start Guide

### 1. Start the FastAPI Backend Engine:
```bash
# Navigate to project root
cd e:\SIH

# Run FastAPI backend server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Start the Vite React Frontend UI:
```bash
# Open a second terminal window
cd e:\SIH\frontend

# Install dependencies & run Vite dev server
npm install
npm run dev
```

Open `http://localhost:5173` in your browser to start using ANVAYA!
