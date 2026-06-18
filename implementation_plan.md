# Implementation Plan — Full Dataset Recovery & Global Ranking

This plan outlines the dataset recovery, pipeline execution, and validation tasks for Phase 4 of the TalentLens challenge.

---

## 1. Dataset Recovery Findings & Inventory

We have located the original challenge bundle zip file in the `Downloads` directory:
* **Path**: `C:\Users\rudra\Downloads\[PUB] India_runs_data_and_ai_challenge.zip`

### Dataset Inventory:
1. **Full Candidate Dataset**: Extracted from the zip file.
   * **Filename**: [candidates.jsonl](file:///c:/Users/rudra/OneDrive/Music/talentlens/candidates.jsonl)
   * **Size**: 464.69 MB uncompressed
   * **Profiles**: Exactly 100,000 candidate records.
2. **Mock Candidate Dataset**: Used for fast testing.
   * **Filename**: `sample_candidates.json`
   * **Profiles**: 50 mock candidate records.

---

## 2. Proposed Execution Workflow

We will run the optimized TalentLens candidate ranking engine against the complete 100,000 candidate dataset:

1. **Global Run**: Run the main ranking engine ([app.py](file:///c:/Users/rudra/OneDrive/Music/talentlens/app.py)) directly on the full [candidates.jsonl](file:///c:/Users/rudra/OneDrive/Music/talentlens/candidates.jsonl) dataset.
   * **Outputs**:
     * `submission.csv` (Global Top 100 candidates, sorted by score descending, then candidate ID ascending).
     * `full_output.csv` (All 100,000 candidates scored for detailed audit).
2. **Finalize Submission**: Copy the generated `submission.csv` to `final_submission.csv` to create the final deliverable.
3. **Audit and Compare**:
   * Compile a comparative analysis comparing:
     * **Original submission** (initial 100 candidates in the repository).
     * **Optimized submission** (`remediated_submission.csv` derived from the remediated engine on the initial 100 candidates).
     * **Full-dataset submission** (the newly generated global Top 100 candidates).
4. **Generate Documentation**:
   * Create `dataset_recovery_report.md` detailing the recovery actions and inventory.
   * Create `global_ranking_report.md` detailing the global Top 100 rankings and shifts.
5. **Verify and Format check**:
   * Run the challenge format validator `validate_submission.py` on `final_submission.csv` to ensure 100% compliance with challenge rules.

---

## 3. Verification Plan

### Automated Checks
* **Profile Count**: Confirm `candidates.jsonl` contains exactly 100,000 lines (profiles).
* **Format Validator**: Run the official challenge validator:
  ```bash
  uv run python "C:\Users\rudra\Downloads\talentlens x\validate_submission.py" final_submission.csv
  ```
  Must output: `"Submission is valid."`
* **Score Monotonicity**: Verify that scores in `final_submission.csv` are monotonically non-increasing and tie-breaks follow alphabetical sorting of candidate IDs.

### Manual Verification
* Inspect the top 10 global candidates for profile integrity:
  * Check that no junior keywords appear in their current titles or headlines.
  * Check that all claimed must-have skills are backed by description evidence.
  * Check that non-domain (e.g. Computer Vision) profiles do not leak into the Top 20.
