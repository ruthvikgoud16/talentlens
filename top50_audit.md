# Redrob Evaluation Committee — Top 50 Ranking Audit

This document audits the candidates ranked #11 through #50 in the optimized TalentLens X pipeline, identifying seniority mismatch, over-experience, and soft consulting background penalisations.

---

## Key Anomalies and Flags (Ranks 11–50)

### 1. The "Junior" Title Leakage (Rank #21: `CAND_0043860`)
* **The Profile**: Current title is `"Junior Ml Engineer"`, with 6.0 years of experience.
* **The Issue**: A founding team role requires a Senior AI Engineer who can design and deploy architecture independently. Placing a candidate with "Junior" in their title in the top 25 is a severe mismatch.
* **The Flaw**: The career engine only checks the title for trajectory transitions (e.g. tech to non-tech). It does not penalize junior prefixes like "junior" or "associate" in the candidate's current title, allowing this candidate to rank extremely high simply by matching must-have keywords.

### 2. The Over-Experienced Profile (Rank #47: `CAND_0039754`)
* **The Profile**: Current title is `"Senior Applied Scientist"`, with **16.0 years** of experience.
* **The Issue**: The job description specifically requests **5 to 9 years of experience**. A candidate with 16 years of experience is heavily overqualified, has different compensation expectations, and is unlikely to fit a hands-on, fast-paced founding team hybrid role.
* **The Flaw**: The engine applies a minor penalty for over-experience (`exp_scale = 0.85`), but because the base career score and feature hits are high, they still easily land in the top 50.
* **Committee Critique**: Over-experienced profiles must be penalized more aggressively to match the specific 5–9 years bracket requested.

### 3. Soft Penalisation of Outsourcing Background (Rank #11: `CAND_0005649`)
* **The Profile**: Senior Data Scientist, has a career history including a stint at **Tata Consultancy Services (TCS)**.
* **The Issue**: The job description explicitly states **"product company not consulting"** and lists TCS/Infosys/Wipro as negative signals.
* **The Flaw**: The consulting penalty is calculated as `ratio * 40.0`, where `ratio` is `consulting_companies / total_companies`. Since this candidate spent 1 year at TCS and 6 subsequent years at product companies (Juspay, HDFC Securities), their ratio is low, resulting in a minor penalty. 
* **Committee Critique**: The engine permits candidates with outsourcing backgrounds to rank near the top 10, violating the strict "no consulting" mandate.

### 4. Logic Inconsistency on Unverified Skills (Rank #13: `CAND_0002025`)
* **The Profile**: Senior AI Engineer, has `"Unverified skills: faiss"`.
* **The Issue**: They dropped from Rank #3 to Rank #13 due to the unverified skill penalty. However, they are still ranked higher than many fully verified candidates in the 20s and 30s.
* **The Flaw**: The skill validation penalty is capped at `-24.0` points, which is easily offset by high keyword-stuffing hits in other areas.
