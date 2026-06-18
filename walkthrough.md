# Walkthrough — Phase 5.0: Trust, De-Biasing & Workflow Visibility

This document summarizes the changes, visual enhancements, and verification results completed during Phase 5.0 of the TalentLens candidate Discovery & Ranking platform.

---

## 1. Key Accomplishments

### A. Demographic De-Biasing Layer (`app.py` & `debiasing_report.md`)
- **Algorithmic Fairness**: Strip personal names, gender indicators (neutralizing pronouns: *he/she* ➔ *they*, *his/her* ➔ *their*), age references (*X years old*, *born in YYYY*), and candidate locations (specifically candidate's city/country plus common global tech hubs) before scoring.
- **Anonymity**: Map candidate records to sequential anonymous IDs (e.g. `ANON_0018499`) for all internal feature vector extraction, TF-IDF calculation, multi-engine scoring, and reasoning generation.
- **Submission Spec Compliance**: Map anonymous IDs back to original `CAND_` IDs during CSV write to ensure validator compatibility.
- **Documentation**: Generated [debiasing_report.md](file:///c:/Users/rudra/OneDrive/Music/talentlens/debiasing_report.md) in the workspace root.

### B. Visual Workflow Tracker (`talentlens_x.html`)
- **Stage Navigation**: Created a 7-stage visual pipeline tracker in the dashboard `#pbar` linking JD Upload, JD Understanding, Semantic Retrieval, Truth Engine, FutureFit Engine, Ranking Engine, and Top 100 Generation.
- **Latency & Counts**: Displayed candidate counts (e.g., *100K ➔ 1K ➔ 100*) and actual pipeline execution latencies (e.g., *142ms*, *4.5s*).

### C. Explainability Panel (`talentlens_x.html`)
- **5-Score Grid**: Rendered Semantic Match, Truth Score, FutureFit Score, Experience Alignment, and Final Score clearly.
- **Evidence Snippets**: Added a dedicated container utilizing `ev-snippets` and `ev-snippet-card` classes showing candidate-specific verified quotes (Truth Trail evidence) supporting the scores.

### D. Dashboard Polish & Skeleton Loaders (`talentlens_x.html`)
- **Skeleton Shimmers**: Integrated glowing skeleton loading placeholders while candidates are being retrieved in Discovery view.
- **Rank Border Highlights**: Styled candidate cards dynamically with colored borders and glowing shadows based on rank (Gold for Rank 1, Silver for Rank 2, Bronze for Rank 3, standard for others).
- **Responsive Layout**: Wrapped grids and columns using CSS media queries to support desktop, tablet, and mobile views gracefully.

### E. Autoplay Demo Mode (`talentlens_x.html`)
- **Interactive Walkthrough**: Built an end-to-end 3-minute autoplay walkthrough showing JD upload, NER parsing, semantic retrieval (with de-biasing redactions), Truth Engine checks, FutureFit scores, Rankings output, side-by-side explainability (Rank #1 vs Rank #2 comparison with all 5 scores and evidence snippets), and Top 100 CSV download.
- **Validator Compliance**: Export button generates and downloads a clean UTF-8 `submission.csv` with original `CAND_` IDs.

---

## 2. Code Changes

### Backend changes in [app.py](file:///c:/Users/rudra/OneDrive/Music/talentlens/app.py)
```diff
+GENDER_RE = re.compile(r'\b(he|she|his|her|him|hers|himself|herself|male|female|man|woman|men|women|mr|mrs|ms)\b', re.IGNORECASE)
+GENDER_MAP = { ... }
+def debias_candidate(cand, anon_id):
+    # Strip name, gender, age, location
+    ...
+
 def main():
     candidates = load_candidates()
+    # Apply anonymization mapping
+    orig_to_anon = {}
+    anon_to_orig = {}
+    debiased_candidates = []
+    for idx, c in enumerate(candidates):
+        ...
+        debiased_candidates.append(debias_candidate(c, anon_id))
+    candidates = debiased_candidates
```

### Frontend changes in [talentlens_x.html](file:///c:/Users/rudra/OneDrive/Music/talentlens/talentlens_x.html)
- Modified `renderRankings` to add class `r1`, `r2`, `r3` for top candidates.
- Modified `renderExplain` to display the verified `ev-snippets` container.
- Added `FULL_100_CANDS` array representing the top 100 candidates.
- Injected `DEMO_STEPS` state mappings, `initDemoView`, `startAutomatedDemo`, `toggleDemoAuto`, `nextDemoStep`, and `exportDemoCSV` functions.

---

## 3. Verification & Diagnostic Output

### A. Integration Tests (`python test_app.py`)
```
============================================================
           TALENTLENS ENGINE INTEGRATION TEST
============================================================
Analyzing Candidate: CAND_PERFECT_AI
  Career Score     : 68.75 (Prod hits: 5, Domain hits: 1)
  Skill Score      : 85.0 (Matched: ['retrieval', 'vector', 'sentence-transformers', 'python', 'transformers', 'llm'])
  Recruitability   : 96.4 (Notice: 15d, Behav: 94.0, Logist: 100.0)
  --> Final Score  : 75.4125
  [PASS] Perfect AI candidate behaves correctly.

Analyzing Candidate: CAND_WRONG_CV
  Career Score     : 0.0 (Prod hits: 3, Domain hits: 0)
  --> Final Score  : 24.8
  [PASS] CV penalty verified. Candidate filtered out successfully.

Analyzing Candidate: CAND_CONSULTING
  Career Score     : 0.0 (Prod hits: 0, Domain hits: 0)
  --> Final Score  : 32.4425
  [PASS] Consulting ratio-based penalty verified.

Analyzing Candidate: CAND_JUNIOR_LEAK
  Career Score     : 0.0 (Prod hits: 0, Domain hits: 1)
  --> Final Score  : 30.19
  [PASS] Junior Title penalty verified.
============================================================
  ALL SYSTEM DIAGNOSTIC TESTS PASSED SUCCESSFULLY!
============================================================
```

### B. Ingestion Output (`python app.py`)
- **Scale**: Scans 100,000 candidates.
- **Top 1 candidate**: `CAND_0018499` (debiased score: `87.2585`).
- **Submission file saved**: `submission.csv` containing correct headers and candidate rows.
- **Full output saved**: `full_output.csv`.
