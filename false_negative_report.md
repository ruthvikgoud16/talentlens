# Redrob Evaluation Committee — False Negative Report

This report documents under-ranked candidates in the Top 100 who have exceptional technical fit for the Senior AI Engineer (Founding Team) role, but were heavily demoted by availability signals and logistics parameters.

---

## 1. Candidate: `CAND_0080766` (Rank #75)
* **Incorrect Rank**: Rank #75 (Score: 64.88).
* **Profile Details**: Staff Machine Learning Engineer, 9.0 years of experience, with verified production experience in Milvus, OpenSearch, and search/retrieval scaling.
* **Why the Candidate is Incorrectly Ranked**: This profile represents the absolute top-tier of technical talent in the candidate pool. They hold a Staff title and 9 years experience, which is the perfect upper boundary of the target experience. Yet, they are ranked near the bottom of the Top 100.
* **What Evidence Was Missed**: The candidate's deep vector database architecture experience and team leadership signals were undervalued compared to their logistical signals.
* **Flaw in Scoring Logic**: 
  * **Notice Period Dominated Demotion**: This candidate has a **90-day notice period**. The logistics engine penalizes this heavily (`notice_score = 0.45`), resulting in a low recruitability index (`34/100`). This index drags down their overall score from a potential ~78 to a `64.88`.
  * **Remedy**: Real-world hiring allows notice buyout or waiting 2–3 months for a high-caliber Staff engineer. Availability should not act as a severe penalty for highly qualified senior roles.

---

## 2. Candidate: `CAND_0094759` (Rank #90)
* **Incorrect Rank**: Rank #90 (Score: 58.72).
* **Profile Details**: Lead AI Engineer, 9.0 years of experience, with verified skills in Faiss, Qdrant, and vector search systems.
* **Why the Candidate is Incorrectly Ranked**: Like `CAND_0080766`, they have a Lead AI Engineer title and 9 years experience, which represents a strong fit. Ranking them at #90 means they are practically hidden from the recruiter.
* **What Evidence Was Missed**: Clear leadership trajectory, vector search architecture projects, and target experience tenure.
* **Flaw in Scoring Logic**: 
  * **Low Platform Activity Penalty**: The candidate had a low platform activity score, combined with a 90-day notice period. The engine applied a **0.30 recency multiplier** for inactivity, reducing their recruitability to a minimal score.
  * **Remedy**: Active candidates are easier to contact, but passive candidates (who haven't logged in recently) are often the highest-quality hires for critical founding roles. Demoting passive candidates by 70% is a strategic mistake.

---

## 3. Candidate: `CAND_0033861` (Rank #83)
* **Incorrect Rank**: Rank #83 (Score: 60.72).
* **Profile Details**: Senior NLP Engineer, 8.0 years of experience, with verified skills in Milvus, Qdrant, and vector database systems.
* **Why the Candidate is Incorrectly Ranked**: Perfect experience bracket (8 years), Senior title in a highly relevant domain (NLP and vector databases), and strong Must-Have skills matches.
* **What Evidence Was Missed**: 8 years of search-adjacent NLP engineering projects.
* **Flaw in Scoring Logic**: 
  * **Notice Period Penalty**: Demoted due to a 90-day notice period which dragged down their overall score.
  * **Remedy**: Adjust the notice period penalty scale to be less punitive for highly matching Senior profiles.
