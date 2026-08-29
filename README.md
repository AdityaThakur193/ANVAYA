# 🛡️ ANVAYA (अन्वय)
### Multimodal Offline Air-Gapped Intelligence RAG Platform

[![SIH Problem Statement](https://img.shields.io/badge/SIH%202026-SIH25231-orange.svg)](https://sih.gov.in)
[![Sponsoring Agency](https://img.shields.io/badge/Agency-NTRO%20(Prime%20Minister's%20Office)-blue.svg)](https://ntro.gov.in)
[![Air-Gapped Status](https://img.shields.io/badge/Air--Gapped-100%25%20Offline%20(Zero%20Cloud)-green.svg)]()

---

## 📌About The Project

**ANVAYA** (Sanskrit: *अन्वय* — meaning *Synthesis, Connection & Grounded Relation*) is an enterprise-grade, 100% offline, air-gapped **Multimodal Retrieval-Augmented Generation (RAG)** platform built for the **National Technical Research Organisation (NTRO)** under **Smart India Hackathon (`SIH25231`)**.

Designed specifically for secure, air-gapped environments with **zero internet connectivity**, ANVAYA ingests multi-format evidence caches—including PDF reports, scanned handwritten notes/screenshots, and recorded audio wiretaps—into a unified semantic retrieval index. It leverages a local quantized Large Language Model to synthesize grounded, hallucination-free intelligence briefings equipped with **clickable page and millisecond audio timestamp citations**.

---

## 🛠️ Final Technology Stack (Option A: 100% Offline Single-Page Architecture)

* **Frontend Console**: Vite + React 19 + TypeScript + Tailwind CSS (0 SSR hydration bugs, instant static build)
* **Backend Engine**: Python 3.11 + FastAPI + Uvicorn
* **Document Ingestion**: PyMuPDF (`fitz`) + Regex text normalization (`pdf_parser.py`)
* **Image OCR Ingestion**: PaddleOCR / Tesseract 5 (`image_ocr.py`)
* **Audio Ingestion**: `faster-whisper-tiny` (CTranslate2 INT8 millisecond speech-to-text)
* **Vector Store**: Embedded ChromaDB (HNSW index) + `BAAI/bge-small-en-v1.5` embeddings (133MB ONNX)
* **Hybrid Search**: Dense Cosine Similarity + BM25 Lexical Keyword Search (Reciprocal Rank Fusion RRF)
* **Local Offline LLM**: `Llama-3.2-3B-Instruct.Q4_K_M.gguf` via `llama.cpp` (100% Zero Cloud)
* **Citation Navigation**: `pdfjs-dist` (PDF page highlight) + `wavesurfer.js` (Audio timestamp waveform player)

---

## 📁 Repository Folder Structure

```
ANVAYA/
├── README.md                           # Updated Project Definition & Tech Stack
├── backend/                            # Python FastAPI Server Engine
│   ├── app/
│   │   ├── main.py                     # FastAPI entry point
│   │   ├── api/                        # REST endpoints (/ingest, /query)
│   │   └── services/                   # Data processing modules
│   │       ├── pdf_parser.py           # PyMuPDF & Regex text cleaning module
│   │       ├── image_ocr.py            # PaddleOCR screenshot text extractor
│   │       ├── audio_transcriber.py    # Whisper timestamp audio transcriber
│   │       ├── vector_store.py         # ChromaDB + BM25 RRF hybrid index
│   │       └── local_llm.py            # llama.cpp local quantized LLM engine
│   └── requirements.txt                # Python backend dependencies
├── frontend/                           # Vite + React 19 Analyst UI Console
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                     # Master Analyst Console UI
│   │   └── index.css                   # Tailwind CSS
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
└── data/                               # Local Storage & Vector Database
    ├── processed_text/                 # Cleaned text outputs & metadata
    └── chroma_db/                      # Persistent HNSW vector database
```
