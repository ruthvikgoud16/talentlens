# TalentLens X — Global Ranking Report

This report presents the comparative analysis and results of executing the remediated TalentLens X ranking engine against the full recovered pool of 100,000 candidate profiles.

---

## 1. Execution Summary

* **Total Candidates Scored**: 100,000
* **Pipeline Runtime**: ~3 minutes (active CPU execution)
* **TF-IDF Vocabulary Space**: 5,000 features fitted corpus-wide
* **Outputs Generated**:
  * `final_submission.csv` (Global Top 100)
  * `full_output.csv` (All 100,000 candidates scored)

---

## 2. Top 10 Candidate Comparison

The table below tracks the movement of top-tier candidates across three stages of optimization:
1. **Original Submission**: Initial unoptimized engine run over the selected 100-candidate subset.
2. **Optimized Submission**: Remediated engine run over the same 100-candidate subset (Phase 3.5).
3. **Global Final Submission**: Remediated engine run over the entire 100,000-candidate pool (Phase 4).

| Rank | Original (100 Subset) | Remediated (100 Subset) | Global Final (100K Pool) | Score (100K) | Current Title (Global Final) | Audit & Shift Rationale |
| :---: | :--- | :--- | :--- | :---: | :--- | :--- |
| **#1** | `CAND_0018499` | `CAND_0018499` | `CAND_0086022` | **77.2411** | Senior Applied Scientist | **Newly Discovered #1**: Rising from Rank #32. Holds 5.3 years of experience with deep verified skills in embeddings, pinecone, and sentence-transformers. Supported by an elite semantic match score of `48.27%`. |
| **#2** | `CAND_0043860` | `CAND_0055905` | `CAND_0079387` | **76.7894** | AI Engineer | **Newly Discovered #2**: 7.4-year AI Engineer with validated vector and search hits and extremely high recruitability (78.94). |
| **#3** | `CAND_0002025` | `CAND_0081846` | `CAND_0005649` | **76.5585** | Senior Data Scientist | **Newly Discovered #3**: 7 years experience. Deployed complex search and opensearch systems. |
| **#4** | `CAND_0093912` | `CAND_0030031` | `CAND_0088025` | **76.0555** | Staff Machine Learning Engineer | **Promoted to #4**: Moved up from Rank #5 in remediated run. Elite Staff candidate with 9 years experience and extensive verified vector search skills. |
| **#5** | `CAND_0098454` | `CAND_0088025` | `CAND_0018499` | **76.0085** | Senior Machine Learning Engineer | **Stable Core**: The previous Rank #1 candidate remains in the Top 5 globally. Rebalanced slightly due to corpus-wide dynamic TF-IDF score computation (`45.12%`). |
| **#6** | `CAND_0033179` | `CAND_0010149` | `CAND_0066376` | **75.8575** | Applied ML Engineer | **Newly Discovered #6**: 6 years experience. Deployed faiss and nlp systems with zero profile contradictions. |
| **#7** | `CAND_0064888` | `CAND_0046525` | `CAND_0081846` | **75.4682** | Lead AI Engineer | **Rebalanced**: The previous Rank #3 candidate moves to Rank #7 due to high-quality competitor discoveries from the 100K pool. |
| **#8** | `CAND_0077337` | `CAND_0077337` | `CAND_0079064` | **74.9516** | ML Engineer | **Newly Discovered #8**: High-performing ML Engineer with 100% verified core search skills. |
| **#9** | `CAND_0041610` | `CAND_0093912` | `CAND_0028793` | **74.8653** | Search Engineer | **Newly Discovered #9**: 7-year search engineer with robust embeddings and retrieval evidence. |
| **#10** | `CAND_0067866` | `CAND_0002025` | `CAND_0081686` | **74.6402** | Search Engineer | **Newly Discovered #10**: 6-year search engineer with verified faiss and milvus deployment experience. |

---

## 3. Overlap Analysis

Comparing the composition of the Top 100 lists reveals the impact of widening the candidate pool:

* **Original vs. Remediated (100 Subset)**: **100% Overlap**
  * Both runs evaluated the exact same 100 candidates. The only differences were score adjustments and rank re-ordering (e.g. promoting clean profiles and demoting junior leakages).
* **Remediated (100 Subset) vs. Global Final (100K Pool)**: **70% Overlap**
  * Out of the 100 candidates selected in the initial submission, **70 candidates** remain in the global Top 100.
  * **30 candidates** were displaced from the Top 100 by superior profiles discovered from the wider 100,000-candidate pool.
  * This demonstrates that the original 100-candidate pool was a highly dense, high-relevance subset, but running the engine globally unlocked **30 technically superior matches** (e.g. `CAND_0086022` taking Rank #1).

---

## 4. Newly Discovered Candidates entering the Top 100

Here are some of the elite profiles that were discovered when scanning the full 100,000 candidates:

1. **`CAND_0086022` (Rank #1, Score: 77.2411)**: Senior Applied Scientist with 5.3 years of experience. Verified skills in embeddings, sentence-transformers, and pinecone. High-fidelity semantic score (`48.27%`).
2. **`CAND_0079387` (Rank #2, Score: 76.7894)**: 7.4-year AI Engineer. Deployed milvus and weaviate vector stores with 0 unverified skill flags and high responsiveness (78.94 recruitability).
3. **`CAND_0007009` (Rank #34, Score: 69.0545)**: 7.9-year Recommendation Systems Engineer. Deeply experienced in ranking models, hybrid search, and production latency optimization.
4. **`CAND_0020877` (Rank #44, Score: 67.0795)**: 5.1-year Applied ML Engineer. Strong production MLOps track record and verified search index scaling.

---

## 5. Ranking Quality Observations

1. **Zero Junior Title Leakage**: The flat **-40.0 point career penalty** worked flawlessly. No candidate with a "Junior", "Associate", "Intern", or "Freshman" keyword exists in the global Top 50. Candidate `CAND_0043860` (Junior ML Engineer), who previously held **Rank #2**, has been successfully demoted to **Rank #88**.
2. **Truth Engine Effectiveness**: The flat **-35.0 point penalty** for unverified must-have core skills successfully demoted profiles that listed skills (e.g. `embeddings`, `vector`, `retrieval`) but lacked description evidence. Fully verified, clean candidates rose to the top.
3. **Recruitability Rebalancing**: By relaxing the notice period penalty to 80% for 90-day notices, elite passive candidates (such as `CAND_0088025` at Rank #4) are now correctly surfaced in the Top 10 instead of being pushed down into the 70s.
4. **TF-IDF Rigor**: Running TF-IDF over all 100,000 candidates (rather than hardcoding estimates) allowed cosine similarity to accurately reflect the semantic distance between each candidate's career trajectory and the Series A Founding AI Engineer job description.
