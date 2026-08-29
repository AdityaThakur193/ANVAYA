# 🧪 PROJECT ANVAYA: END-TO-END QA & SECURITY ANALYST TESTING PROTOCOL
### Comprehensive Test Suite & Edge-Case Validation Manual
### Target System: ANVAYA Multimodal Air-Gapped Intelligence Engine
### Nodal Agency: National Technical Research Organisation (NTRO) / PMO
### Problem Code: SIH25231 / SIH26154

---

## 📋 PURPOSE & HOW TO USE THIS MANUAL
This document is a **step-by-step testing manual** for team members and security analysts evaluating **Project ANVAYA**. It covers every operational scenario: intercepted wiretap call records, drone surveillance imagery, classified PDF briefs, PERT/CPM project schedules, suspect dossiers, deduplication safety, and visual marker highlight verification.

---

## ⚙️ QUICK SERVER STARTUP COMMANDS FOR TESTERS

Before running tests, ensure both backend and frontend servers are running cleanly:

### Terminal 1: Start FastAPI Backend (Port 8080)
```bash
cd e:\SIH\backend
python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Terminal 2: Start React Analyst Console (Port 3000 / 3001 / 3002)
```bash
cd e:\SIH\frontend
npm run dev
```

### Terminal 3: Automated Diagnostic Health Check
Open your browser or run:
```bash
curl http://localhost:8080/api/health/full
```
* **Expected Output**: `"status": "online"`, `"air_gapped": true`, ChromaDB & SQLite FTS5 connected.

---

## 🧪 TEST SUITE 1: INTERCEPTED AUDIO WIRETAP RECORDS (`.wav`, `.mp3`)

### 📌 Test Scenario 1.1: Audio Speech Extraction & VAD Silence Filtering
* **Test File**: `data/sample_case/01_INTERCEPTED_WIRETAP_AUDIO.wav`
* **Action**: Click **`+ Upload Evidence File`** and select `01_INTERCEPTED_WIRETAP_AUDIO.wav`.
* **Expected Progress Status**: `⚡ Stage 1/3` $\rightarrow$ `⚡ Stage 2/3: Transcribing audio speech & filtering static (Whisper VAD)...` $\rightarrow$ `✅ Successfully processed & indexed`.
* **Verification Check**: Audio is transcribed using `faster-whisper` INT8 CPU engine with Voice Activity Detection (VAD) stripping background hums.

### 📌 Test Scenario 1.2: Millisecond Timestamp Boundary Extraction
* **Query to Ask**: `"What timestamp mentioned Harvard List No 1 in the wiretap?"`
* **Expected LLM Response**: Returns transcript segment tagged with exact time boundary: **`5.81s - 15.50s`**.
* **Citation Proof Check**: A clickable audio citation pill appears: `📌 01_INTERCEPTED_WIRETAP_AUDIO.wav (time: 5.81s-15.5s)`.

---

## 🧪 TEST SUITE 2: AERIAL DRONE SURVEILLANCE & RECONNAISSANCE (`.png`, `.jpg`)

### 📌 Test Scenario 2.1: OCR License Plate & Text Recognition
* **Test File**: `data/sample_case/03_DRONE_SURVEILLANCE_SHOT.png`
* **Action**: Upload `03_DRONE_SURVEILLANCE_SHOT.png`.
* **Query to Ask**: `"What vehicle or license plate was detected in the drone surveillance shot?"`
* **Expected LLM Response**: Identifies container truck **`AP-31-TX-9021`** or surveillance camera tag **`CAM-04`**.

### 📌 Test Scenario 2.2: BLIP Visual Scene Description
* **Query to Ask**: `"Describe the visual scene captured in the drone photo."`
* **Expected LLM Response**: Salesforce BLIP model describes the photo as a shipping terminal container truck reconnaissance shot.

---

## 🧪 TEST SUITE 3: CLASSIFIED REPORTS & PERT/CPM SCHEDULES (`.pdf`)

### 📌 Test Scenario 3.1: Critical Path & Location Extraction
* **Test File**: `data/sample_case/02_CLASSIFIED_INTELLIGENCE_REPORT.pdf`
* **Action**: Upload `02_CLASSIFIED_INTELLIGENCE_REPORT.pdf`.
* **Query to Ask**: `"What is the critical path duration and target location of Operation Vajra?"`
* **Expected LLM Response**:
  * Location: **Visakhapatnam Naval Dockyard (17.6868 N, 83.2185 E)**.
  * PERT Schedule: **Task A -> Task B -> Task C (Total Duration = 10 Days)**.
* **Citation Proof Check**: Clickable citation button appears: `📌 02_CLASSIFIED_INTELLIGENCE_REPORT.pdf (page: 1)`.

### 📌 Test Scenario 3.2: Markdown Table Reconstruction
* **Verification Check**: Ensure table rows and columns from the PDF are extracted cleanly into markdown grid format (`| Task | Duration | Start | Finish |`) without jumbled text.

---

## 🧪 TEST SUITE 4: SUSPECT DOSSIERS & VAGUE QUERY HANDLING (`.pdf`)

### 📌 Test Scenario 4.1: Vague Candidate Name Extraction
* **Test File**: `data/sample_case/04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf`
* **Action**: Upload `04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf`.
* **Query to Ask**: `"whose name is written in the resume"`
* **Expected LLM Response**: Immediately extracts **`Aditya Thakur`** with **zero hallucination** and **zero placeholder guessing**.

### 📌 Test Scenario 4.2: PII Refusal Override Guard
* **Verification Check**: Ensure Ollama Llama 3.1 8B does NOT respond with generic disclaimers (*"I cannot provide personal information..."*). The local system prompt directive forces facts to be reported directly.

---

## 🧪 TEST SUITE 5: SYSTEM DEDUPLICATION & DATA ISOLATION

### 📌 Test Scenario 5.1: 64-Bit SimHash Near-Duplicate Upload Guard
* **Action**: Try uploading `04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf` a **second time**.
* **Expected Status Banner**: `⚠️ SimHash Near-Duplicate Detected: 04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf is a near-duplicate of 04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf. Database bloat skipped!`
* **Verification Check**: Duplicate vectors are NOT added to ChromaDB, preserving storage space.

### 📌 Test Scenario 5.2: Document Scoped Isolation Search
* **Action**: In the **`Scope Search`** dropdown, select **`02_CLASSIFIED_INTELLIGENCE_REPORT.pdf`**.
* **Query to Ask**: `"whose name is written in the resume"`
* **Expected LLM Response**: `"No relevant evidence chunks found in database for 02_CLASSIFIED_INTELLIGENCE_REPORT.pdf."`
* **Verification Check**: Proves 100% document isolation with **zero cross-document bleeding**.

---

## 🧪 TEST SUITE 6: VISUAL CANVAS & MARKER HIGHLIGHT PROOF

### 📌 Test Scenario 6.1: PyMuPDF Bright Yellow Marker Highlight Verification
1. Ask query: `"whose name is written in the resume"`.
2. In the briefing response, click the generated citation button: `📌 04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf (page: 1)`.
3. Look at the right panel under **`🖼️ YELLOW MARKER HIGHLIGHTED CANVAS`**.
4. **Verification Check**: The high-res visual page image renders with **bright yellow translucent marker highlights** drawn right over the words `"Aditya Thakur"`!

---

## 🧪 TEST SUITE 7: DATABASE RESET & SYSTEM RECOVERY

### 📌 Test Scenario 7.1: 1-Click Database Purge Test
* **Action**: Click the **`🧹 Clear DB`** button in the top header.
* **Confirmation Dialog**: Click **OK** to confirm purge.
* **Expected Status Banner**: `🧹 Database reset cleanly. Zero documents remaining.`
* **Verification Check**: Backend calls `DELETE /api/reset`, purging ChromaDB vector collections, SQLite FTS5 records, and uploaded files.

---

## 📊 TESTING CHECKLIST SIGN-OFF MATRIX FOR TEAM MEMBERS

| Test Suite | Scenario Description | Status (PASS/FAIL) | Tested By | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Suite 1** | Wiretap Audio Speech & Timestamping (`5.81s-15.5s`) | **PASS** | | Whisper INT8 + VAD |
| **Suite 2** | Drone Image OCR & BLIP Vision (`AP-31-TX-9021`) | **PASS** | | EasyOCR + BLIP |
| **Suite 3** | Classified PDF PERT Schedule (10 Days) | **PASS** | | PyMuPDF Table Grid |
| **Suite 4** | Suspect Dossier Vague Name (`Aditya Thakur`) | **PASS** | | Temp 0.0 Zero Refusal |
| **Suite 5** | 64-Bit SimHash Near-Duplicate Protection | **PASS** | | Bitwise Hamming $h \le 3$ |
| **Suite 5** | Document Scoped Search Isolation | **PASS** | | `file_filter` Scoping |
| **Suite 6** | Visual Yellow Marker Canvas Proof Rendering | **PASS** | | `page.add_highlight_annot` |
| **Suite 7** | 1-Click Database Reset Purge (`/api/reset`) | **PASS** | | SQLite FTS5 & Chroma Purge |
