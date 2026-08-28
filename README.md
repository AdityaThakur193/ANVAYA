# 🛡️ ANVAYA (अन्वय)
### Multimodal Offline Air-Gapped Intelligence RAG Platform

[![SIH Problem Statement](https://img.shields.io/badge/SIH%202025%2F2026-SIH25231%20%7C%20SIH26154-orange.svg)](https://sih.gov.in)
[![Sponsoring Agency](https://img.shields.io/badge/Agency-NTRO%20(Prime%20Minister's%20Office)-blue.svg)](https://ntro.gov.in)
[![Air-Gapped Status](https://img.shields.io/badge/Air--Gapped-100%25%20Offline%20(Zero%20Cloud)-green.svg)]()

---

## 📌 About The Project

**ANVAYA** (Sanskrit: *अन्वय* — meaning *Synthesis, Connection & Grounded Relation*) is an enterprise-grade, 100% offline, air-gapped **Multimodal Retrieval-Augmented Generation (RAG)** platform built for the **National Technical Research Organisation (NTRO)** under **Smart India Hackathon (`SIH25231` / `SIH26154`)**.

Designed specifically for secure, air-gapped environments with **zero internet connectivity**, ANVAYA ingests multi-format evidence caches—including PDF reports, scanned handwritten notes/screenshots, and recorded audio wiretaps—into a unified semantic retrieval index. It leverages a local quantized Large Language Model to synthesize grounded, hallucination-free intelligence briefings equipped with **clickable page and millisecond audio timestamp citations**.

---

## ✨ Key Capabilities

* **🔒 100% Air-Gapped Execution**: Operates completely offline on local hardware with zero outbound cloud or network API calls.
* **📄 Multi-Format Ingestion**: Extracts text and tables from `.pdf` and `.docx` documents, performs OCR on scanned handwritten notes and screenshots, and transcribes recorded audio wiretaps into timestamped text.
* **🔍 Unified Cross-Modal Search**: Supports natural-language text queries, text-to-image matching, and image-to-text retrieval across all ingested file types.
* **🤖 Grounded Local LLM Synthesis**: Generates accurate, source-anchored summaries using a local quantized LLM running directly on-device.
* **🔗 Interactive Citation Navigation**: Displays numbered citations that allow users to jump directly to the cited PDF page number or play the exact millisecond audio timestamp snippet.
