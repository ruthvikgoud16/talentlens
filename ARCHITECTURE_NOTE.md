# TalentLens — System Architecture Note
### Redrob Hackathon Submission · Ruthvik Goud · 2026

---

## Overview

TalentLens is a deterministic, multi-signal candidate ranking engine that scores and ranks 100,000 candidates against a Senior AI Engineer job description. The system is fully local — no API calls, no pre-computed embeddings, no GPU required — and produces a ranked, explainable `submission.csv` in under 3 minutes on a standard 4-core CPU.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         TALENTLENS RANKING PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────────┐    ┌─────────────────┐    ┌───────────────────────┐    ┌──────────────────┐
 │   DATA INGEST   │    │    FEATURE       │    │  MULTI-SIGNAL SCORING │    │  RANK & EXPLAIN  │
 │                 │    │   EXTRACTION     │    │                       │    │                  │
 │ candidates.jsonl│    │                 │    │ ┌─────────────────┐   │    │ Weighted          │
 │ (100K records)  │──▶ │ extract_        │──▶ │ │ Career (35%)    │   │    │ Aggregate:        │
 │                 │    │ features()      │    │ │ prod/domain hits│   │    │                  │
 │ job_            │    │                 │    │ │ exp_scale       │   │    │ final_score =     │
 │ description.txt │    │ 22 feature      │    │ │ consulting_pen. │   │──▶ │   career×0.35    │
 │                 │    │ dimensions:     │    │ └─────────────────┘   │    │ + recruit×0.25   │
 │ Streaming JSONL │    │ • skills_meta   │    │ ┌─────────────────┐   │    │ + skills×0.25    │
 │ reader          │    │ • career titles │    │ │ Recruit (25%)   │   │    │ + semantic×0.15  │
 │ GZ support      │    │ • redrob_sigs  │    │ │ recency_mult    │   │    │ - penalty×0.10   │
 │                 │    │ • profile text  │    │ │ notice_score    │   │    │                  │
 └─────────────────┘    │ • TF-IDF corpus │    │ │ behavior score  │   │    │ Monotonic sort   │
                        │                 │    │ └─────────────────┘   │    │ by score desc    │
                        │ normalize_      │    │ ┌─────────────────┐   │    │                  │
                        │ skill():        │    │ │ Skills (25%)    │   │    │ Top 100 export   │
                        │ hyphen/space/   │    │ │ is_skill_match()│   │    │ → submission.csv │
                        │ plural strip    │    │ │ prof/dur weight │   │    │                  │
                        │                 │    │ └─────────────────┘   │    │ Natural language │
                        └─────────────────┘    │ ┌─────────────────┐   │    │ reasoning per   │
                                               │ │ Semantic (15%)  │   │    │ candidate        │
                                               │ │ TF-IDF cosine   │   │    │                  │
                                               │ │ fit once over   │   │    │ full_output.csv  │
                                               │ │ full corpus     │   │    │ (all 100K for   │
                                               │ └─────────────────┘   │    │  inspection)     │
                                               │ ┌─────────────────┐   │    └──────────────────┘
                                               │ │ Honeypot (−10%) │   │
                                               │ │ contradictions  │   │
                                               │ │ claim vs evidence│  │
                                               │ └─────────────────┘   │
                                               └───────────────────────┘
```

---

## Scoring Engine Breakdown

### 1. Career Evidence & Trajectory (35%)

**What it measures:** Whether the candidate has actually shipped production retrieval/search/ranking systems.

**Key signals:**
- `prod_hits` — count of production keywords in career descriptions: `deployed`, `production`, `scaled`, `latency`, `optimized`, `mlops`, `a/b test`, `index refresh`
- `domain_hits` — count of domain keywords: `retrieval`, `ranking`, `search`, `recommender`, `vector search`, `dense retrieval`, `ndcg`, `mrr`
- `exp_scale` — experience bracket multiplier (5–9 years = 1.0, >9 = 0.85, 3–5 = 0.75, <3 = 0.40)
- `trajectory_mult` — career progression: tech start → senior role = ×1.25; non-tech current role = ×0.30
- `consulting_penalty` — ratio-based deduction up to 40 pts (not binary: partial consulting is penalized proportionally)
- `non_domain_title_penalty` — 45 pts for Computer Vision/Speech/Robotics current title

**Formula:**
```
base = min((prod_hits × 8.0) + (domain_hits × 9.0), 100.0)
raw  = base × exp_scale × trajectory_mult
career_score = max(0, raw - consulting_penalty - non_domain_penalty)
```

---

### 2. Recruitability Index (25%)

**What it measures:** Whether the candidate is actually available and responsive — the JD explicitly states that inactive candidates are "not actually available."

**Key signals:**
- `recency_mult` — last active date multiplier: ≤30 days = 1.0, ≤60 = 0.90, ≤90 = 0.75, ≤180 = 0.55, >180 = 0.30
- `behavior` composite:
  - `recruiter_response_rate` ×0.25
  - `interview_completion_rate` ×0.20
  - `open_to_work_flag` (1.0 if true, 0.35 if false) ×0.20
  - `github_activity_score` ×0.10
  - `profile_completeness_score` ×0.10
  - `avg_response_time_hours` ×0.10
  - `verified_email + verified_phone` ×0.05
- `logistics` composite:
  - `notice_period_days`: ≤15 = 1.0, ≤30 = 0.90, ≤60 = 0.70, ≤90 = 0.45, ≤120 = 0.25, >120 = 0.10
  - `willing_to_relocate`: 1.0 vs 0.65
  - `preferred_work_mode`: onsite = 0.75, other = 1.0

**Formula:**
```
raw_index    = (behavior × 0.60) + (logistics × 0.40)
recruit_score = raw_index × recency_mult
```

---

### 3. Explicit Skill Relevance (25%)

**What it measures:** How well the candidate's declared skills match the JD's skill requirements, weighted by proficiency and duration.

**Must-have skills (weight 2.5–3.0):** embeddings, retrieval, ranking, sentence-transformers, faiss, milvus, qdrant, weaviate, pinecone, opensearch, vector

**Nice-to-have skills (weight 0.5–1.5):** machine learning, pytorch, transformers, llm, fine-tuning, lora, recommendation, rerank, tensorflow, xgboost

**Normalization:** `normalize_skill()` strips hyphens, spaces, case differences, and common plurals before matching, so `"Sentence Transformers"` correctly matches `"sentence-transformers"`.

**Key design: Skill ceiling** — set at 13.0 pts (not the full 25+ skill sum), so a candidate matching 4 must-haves + 2 nice-to-haves at advanced proficiency scores ~100%. This prevents score compression.

**Formula:**
```
prof_mult = {advanced: 1.0, intermediate: 0.75, beginner: 0.45}
dur_mult  = 1.1 if duration_months >= 12 else 0.9
earned    = Σ(weight × prof_mult × dur_mult) for each matched skill
base      = min((earned / 13.0) × 100, 100)
skill_score = base + assessment_bonus - non_domain_penalty
```

---

### 4. Semantic Match via TF-IDF (15%)

**What it measures:** Vocabulary-level similarity between the candidate's full text profile and the JD, capturing terms not covered by keyword lists.

**Implementation details:**
- Single `TfidfVectorizer` fitted **once** across all 100K candidates + JD (corpus size: 100,001 documents)
- `ngram_range=(1, 2)` — captures bigrams like "vector search", "dense retrieval"
- `max_features=5000` — limits vocabulary to top 5K terms by TF-IDF score
- `sublinear_tf=True` — logarithmic term frequency scaling prevents spamming
- `cosine_similarity` between each candidate vector and the JD vector

**Why fit once:** Fitting one shared vectorizer ensures all candidate vectors are in the same semantic space as the JD. Fitting per-candidate would give each candidate their own vocabulary, making scores incomparable.

---

### 5. Honeypot Contradiction Detection (Penalty: up to −10% of final score)

**What it detects:**

| Pattern | Penalty |
|---------|---------|
| Claims X years experience but zero career entries | −50 pts |
| Claims >15 years but only 1 career entry | −35 pts |
| AI/ML headline with zero technical description evidence | −30 pts |
| Non-technical career history but AI skills listed (keyword stuffing) | −20 pts |

**Application:** Penalty is bounded at 100 pts and applied as `penalty × 0.10` subtracted from the final weighted score — not a hard disqualification. This preserves ranking explainability and allows borderline profiles to still receive a partial score.

---

## Data Flow Summary

```
candidates.jsonl (100K)
    │
    ├── [STREAM] Read line-by-line (GZ or plain)
    │
    ├── [PARSE] extract_features() → 22-dim feature dict per candidate
    │
    ├── [NLP] TfidfVectorizer.fit_transform(all_texts + jd_text)
    │         └── cosine_similarity(cand_vectors, jd_vector)
    │
    ├── [SCORE] For each candidate:
    │         ├── score_career()           → career_score, prod_hits, domain_hits
    │         ├── score_skills()           → skill_score, matched_skills
    │         ├── score_recruitability()   → behavior, logistics, recruit_index
    │         ├── score_honeypot_penalty() → penalty, risk_reasons
    │         └── weighted_aggregate()     → final_score
    │
    ├── [SORT] DataFrame sorted by (score DESC, candidate_id ASC)
    │
    ├── [EXPORT] submission.csv → top 100: candidate_id, rank, score, reasoning
    └── [EXPORT] full_output.csv → all 100K with all component scores
```

---

## Technology Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Data parsing | Python `json`, `gzip` | Streaming reader, no OOM on 100K |
| Tabular ops | `pandas`, `numpy` | Vectorized scoring |
| Semantic similarity | `scikit-learn` TF-IDF + cosine | Zero inference cost, interpretable |
| Skill matching | Custom `normalize_skill()` | Handles spelling variants, no library dependency |
| Output | CSV (UTF-8) | Spec-compliant, directly submittable |

**Runtime:** ~3 minutes · **RAM:** <4GB peak · **GPU:** Not required · **Internet:** Not required

---

## Verification

Run the test suite to confirm all three archetypal candidate profiles score correctly:

```bash
python test_app.py
```

Expected output:
- `CAND_PERFECT_AI` → Final Score > 70 ✅ (production retrieval background, must-have skills matched)
- `CAND_WRONG_CV` → Final Score < 40 ✅ (Computer Vision title penalty applied)
- `CAND_CONSULTING` → Career Score < 40 ✅ (100% consulting ratio penalty)

---

*TalentLens · Ruthvik Goud · bathiniruthvik370@gmail.com · github.com/ruthvikgoud16/talentlens*
