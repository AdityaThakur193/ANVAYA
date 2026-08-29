# 🛡️ ANVAYA - SECURITY ANALYST EVALUATION DEMO SUITE
### NTRO Air-Gapped Intelligence Engine (SIH25231 / SIH26154)

---

### 📂 DEMO CASE ASSETS IN THIS FOLDER (`data/sample_case/`):

1. **`01_INTERCEPTED_WIRETAP_AUDIO.wav`**: Audio recording of intercepted communications with Whisper VAD speech-to-text.
2. **`02_CLASSIFIED_INTELLIGENCE_REPORT.pdf`**: Classified NTRO report with PERT/CPM critical path schedules and operational timelines.
3. **`03_DRONE_SURVEILLANCE_SHOT.png`**: High-resolution drone surveillance capture with OCR + BLIP vision recognition.
4. **`04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf`**: Full suspect background dossier and technical qualifications.

---

### 🧪 STEP-BY-STEP EVALUATION SCRIPT FOR JUDGES / ANALYSTS:

#### STEP 1: INGEST DEMO FILES
* Open **`http://localhost:3000/`** in your browser.
* Click **`+ Upload Evidence File`** and upload all 4 files from `data/sample_case/`.
* Observe the **3-Stage Animated Progress Bar** and **SimHash Deduplication Guard**.

---

#### STEP 2: TEST MULTIMODAL QUERIES WITH CITATION PROOF

* **Query 1 (Audio Timestamp Extraction)**:
  * *Query*: `"What timestamp mentioned Harvard List No 1 in the wiretap?"`
  * *Expected Output*: Extracted transcript at timestamp **`5.81s - 15.50s`** with clickable audio citation pill (`📌 01_INTERCEPTED_WIRETAP_AUDIO.wav (time: 5.81s-15.5s)`).

* **Query 2 (Classified Report & PERT/CPM Schedule)**:
  * *Query*: `"What is the critical path duration and location of Operation Vajra?"`
  * *Expected Output*: Visakhapatnam Naval Dockyard, Critical Path = 10 Days (`📌 02_CLASSIFIED_INTELLIGENCE_REPORT.pdf (page: 1)`).

* **Query 3 (Suspect Dossier Search)**:
  * *Query*: `"What software engineering skills and degree does candidate Aditya Thakur hold?"`
  * *Expected Output*: GITAM University B.Tech CSE, Skills: Java, Python, FastAPI, React (`📌 04_SUSPECT_DOSSIER_CONFIDENTIAL.pdf (page: 1)`).

---

#### STEP 3: TEST DOCUMENT SCOPED ISOLATION
* In the **`Scope Search`** dropdown, switch between **`All Ingested Files`** and **`02_CLASSIFIED_INTELLIGENCE_REPORT.pdf`**.
* Notice that selecting a specific document restricts vector search 100% to that file alone with **zero cross-document bleeding**.

---

#### STEP 4: INSPECT VISUAL CANVAS & YELLOW MARKER HIGHLIGHTS
* Click any generated citation button (`📌 Source: File="..."`).
* Observe the **Real Visual Page Image Canvas** in the right panel with **Bright Yellow Translucent Marker Highlights** drawn directly over query terms!
