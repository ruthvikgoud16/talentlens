# TalentLens X — Explainability Stress Test Audit

This document audits the auto-generated reasoning strings produced by the TalentLens X candidate ranking engine. The objective is to ensure that every ranking decision is fully transparent, logically consistent, and explainable to both non-technical recruiters and technical judges in under 30 seconds.

---

## 1. Critique of Auto-Generated Reasoning

The current `app.py` script automatically generates a `reasoning` string for each candidate using the `build_reasoning` function. While highly structured, our stress test identified several explainability vulnerabilities.

### A. Technical Jargon ("Too Technical")
* **Vulnerability**: The reasoning strings output raw hit counts from keyword groups, such as:
  * `"...retrieval & embeddings experience (hits: 4), vector database scale (hits: 2)..."`
* **Why it Fails**: A non-technical recruiter does not understand what "hits: 4" means. It looks like search engine debugging output rather than a professional candidate evaluation.
* **Remediation**: Convert numeric hit counts into descriptive qualifiers:
  * `hits >= 5` $\rightarrow$ "extensive project history"
  * `hits 3-4` $\rightarrow$ "strong project history"
  * `hits 1-2` $\rightarrow$ "some project exposure"

### B. Vague Claims ("Too Vague")
* **Vulnerability**: The engine outputs generic FutureFit claims without career evidence, such as:
  * `"...FutureFit signals: shows leadership trajectory..."`
* **Why it Fails**: The recruiter is left wondering *why* the candidate has a leadership trajectory.
* **Remediation**: Reference the specific career history descriptions that triggered the rule:
  * `shows leadership trajectory` $\rightarrow$ "shows leadership trajectory (mentored junior engineers at Uber)" or "shows leadership trajectory (led a team of 4 at Paytm)"

### C. Rigid Mismatches ("Unsupported/Rigid")
* **Vulnerability**: The engine flags core must-have skills as "unverified" even when semantic synonyms are clearly present in the career history.
  * **Example (`CAND_0086022` - Rank #1)**: Flagged with `Concerns: Unverified skills: vector, sentence-transformers`.
  * **Why it Fails**: The candidate's career descriptions explicitly mention "vector search", "dense retrieval", and "BGE embeddings". To a human recruiter, saying `vector` is unverified seems factually incorrect and unsupported by the CV.
* **Remediation**: Map semantic synonyms during the verification phase (e.g., matching `vector search` and `pgvector` to verify `vector`; matching `BGE embeddings` and `dense retrieval` to verify `embeddings`).

---

## 2. Explanation Framework (30-Second Rule)

To satisfy the goals of Phase 4.3, we have designed two separate explanation playbooks:
1. **Recruiter Playbook (`recruiter_explanations.md`)**: Emphasizes pedigree, years of experience, functional capabilities, availability (notice period), and team alignment. Avoids mathematical weights and raw hit counts.
2. **Judge Playbook (`judge_explanations.md`)**: Emphasizes quantitative parameter scores, feature weights (Career 35%, Recruitability 25%, Skills 25%, Semantic 15%), Truth Engine verifications, and mathematical pairwise score margins.
