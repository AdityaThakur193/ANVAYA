<div align="center">

# 🛡️ PROJECT ANVAYA
### **Air-Gapped Multimodal RAG Engine for Defense Intelligence**
*National Technical Research Organisation (NTRO) / PMO • Problem Statement ID: **SIH25231***

[![Air-Gapped Compliance](https://img.shields.io/badge/Air--Gapped-100%25%20Offline-emerald?style=flat-square&logo=shield)](https://github.com/AdityaThakur193/ANVAYA)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.0%2B-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![Local LLM](https://img.shields.io/badge/Ollama-Llama--3.1--8B-purple?style=flat-square&logo=ollama)](https://ollama.com)

---

</div>

## 📌 Overview

**ANVAYA** is a **100% air-gapped multimodal intelligence analysis platform** built for defense units and counter-intelligence teams under Problem Statement **SIH25231** for **NTRO**.

Operating **completely offline** without external cloud dependencies or GPUs, ANVAYA ingests PDF reports, drone photos, and audio wiretaps, eliminates duplicate files via 64-bit SimHash deduplication, executes hybrid dense/sparse vector search, and synthesizes grounded briefings anchored with visual yellow marker page canvas proof.

---

## 🏗️ Architecture Flow

```mermaid
flowchart TD
    subgraph INGESTION["1. Multimodal Ingestion"]
        PDF["📄 PyMuPDF PDF Layout & Tables"]
        IMG["🖼️ EasyOCR & BLIP Vision Captioning"]
        AUD["🎵 Faster-Whisper INT8 & VAD Timestamps"]
    end

    subgraph STORAGE["2. Deduplication & Storage"]
        SIM["⚡ 64-Bit SimHash Deduplication"]
        CHROMA["🧠 ChromaDB (BAAI/bge-small-en-v1.5 384-d)"]
        FTS["🔍 SQLite FTS5 (BM25 Keyword Search)"]
    end

    subgraph RRF_LLM["3. Reranking & Synthesis"]
        RRF["🔀 Reciprocal Rank Fusion (RRF k=60)"]
        LLM["🛡️ Ollama Llama 3.1 8B (@ Temp 0.0)"]
    end

    subgraph UI["4. Analyst Console"]
        CONSOLE["🎨 React Console + Visual Yellow Canvas Proof"]
    end

    PDF --> SIM
    IMG --> SIM
    AUD --> SIM
    SIM --> CHROMA
    SIM --> FTS
    CHROMA --> RRF
    FTS --> RRF
    RRF --> LLM
    LLM --> CONSOLE
```

---

## ✨ Key Features

* 🛡️ **100% Offline Air-Gapped Seal**: 0 cloud API calls; runs entirely on `127.0.0.1`.
* 🎵 **Audio Wiretap Engine**: Speech transcription with millisecond timestamping (`[5.81s-15.5s]`).
* 🖼️ **Drone Reconnaissance Vision**: OCR text recognition + scene captioning for aerial photos.
* 📄 **Spatial PDF Layout Engine**: Preserves spatial block text & markdown grid table reconstruction.
* ⚡ **SimHash Deduplication**: 64-bit feature fingerprints drop duplicate files ($h \le 3$), saving 90% DB bloat.
* 🔀 **Hybrid RRF Search**: Blends ChromaDB vectors + SQLite FTS5 sparse text with 5x Filename Score Boost.
* 🟡 **Visual Yellow Marker Canvas**: Renders document page canvas with bright yellow marker highlights over query terms.
* 🎙️ **Live Voice STT Mic**: Real-time browser speech-to-text input dictation.

---

## 🚀 Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
*Open **http://localhost:3000** in your browser.*

---

## 🏆 Team & Core Contributors

| Contributor | Role | Key Contributions |
| :--- | :--- | :--- |
| **Aditya Thakur** | **Team Lead & AI Systems Architect** | Multimodal RAG Engine, ChromaDB+FTS5 RRF Search, SimHash Deduplication, Ollama LLM Gateway. |
| **Kaushik** | **Lead Frontend Engineer** | React Analyst Console UI/UX, Dynamic Asset Badges, Visual Proof Canvas, Web Speech Mic STT. |
| **Sujal Sahu** | **Lead QA & Security Tester** | Edge-Case Analysis, Break-Point Discovery, VAD Audio Stress Testing, Security Auditing. |

---

<div align="center">

*GITAM Deemed University • NTRO Sponsoring Nodal Agency • SIH25231*

</div>
