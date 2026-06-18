# TalentLens X — Dataset Recovery Report

This report documents the recovery of the original candidate dataset and compile the dataset inventory for the India Runs Track 1 evaluation.

---

## 1. Context & Objective
The TalentLens X ranking engine was previously restricted to evaluating only the pre-selected 100 candidates from the initial `submission.csv` file. To ensure a production-grade evaluation, we needed to run the engine over the entire candidate pool of approximately 100,000 profiles.

Our goal was to:
1. Locate the original challenge dataset files.
2. Extract the full candidate data.
3. Build a verified dataset inventory.

---

## 2. Recovery Process & Actions

We conducted a search across the user directory, OneDrive, Downloads, and temp directories. 

### A. Location Discovered
The original challenge bundle archive was found in the downloads directory:
* **Path**: `C:\Users\rudra\Downloads\[PUB] India_runs_data_and_ai_challenge.zip`
* **Size**: 56.7 MB (56,725,270 bytes)

### B. Extraction & Verification
We wrote a buffer-based Python extraction script to pull the target dataset out of the ZIP archive directly into our workspace root at `c:\Users\rudra\OneDrive\Music\talentlens`.

* **Extracted File**: [candidates.jsonl](file:///c:/Users/rudra/OneDrive/Music/talentlens/candidates.jsonl)
* **Uncompressed Size**: 464.69 MB (487,262,492 bytes)
* **Line Count (Candidate Profiles)**: Exactly **100,000** records.

---

## 3. Dataset Inventory

| File Name | Location | Size | Type / Format | Count / Records | Purpose |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **`[PUB] India_runs...zip`** | `C:\Users\rudra\Downloads` | 56.7 MB | Compressed ZIP | 26 items | Original challenge bundle containing docs, scripts, and data. |
| **`candidates.jsonl`** | Workspace Root | 464.7 MB | JSON Lines | 100,000 records | The complete candidate dataset containing profile data, career history, and behavioral signals. |
| **`sample_candidates.json`** | `Downloads\talentlens x` | 300 KB | JSON | 50 records | Mock subset of candidates for rapid schema validation. |
| **`candidate_schema.json`** | `Downloads\talentlens x` | 8.8 KB | JSON Schema | 1 schema | Defines the field types and structures for the candidate profiles. |

---

## 4. Schema Audit Verification
Upon loading `candidates.jsonl`, a schema audit confirmed that every candidate record adheres to the expected format:
* **Root Keys**: `['candidate_id', 'profile', 'career_history', 'education', 'skills', 'certifications', 'languages', 'redrob_signals']`
* **Profile Keys**: `['anonymized_name', 'headline', 'summary', 'location', 'country', 'years_of_experience', 'current_title', 'current_company', 'current_company_size', 'current_industry']`
* **Skills Format**: List of dicts (containing `name`, `proficiency`, `endorsements`, and `duration_months`).
* **Career History Format**: List of dicts (using `title` as the role key, containing `company` and `description`).
* **Redrob Signals Format**: Dictionary of 23 behavioral signals (including `notice_period_days`, `recruiter_response_rate`, `last_active_date`, etc.).
