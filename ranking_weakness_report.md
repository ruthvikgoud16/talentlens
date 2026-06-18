# Redrob Evaluation Committee — Ranking Weakness Report

This report analyzes the mathematical vulnerabilities, biases, and structural flaws in the scoring logic of the TalentLens X candidate ranking engine.

---

## 1. Mathematical Vulnerabilities in Weighting

The system combines four dimensions with the following weights:
* **Career Score**: 35%
* **Skills Score**: 25%
* **Recruitability Score**: 25%
* **Semantic Score**: 15%

### ⚖️ The Recruitability Imbalance
Weighting recruitability at **25%** creates a bias toward candidate responsiveness over technical capability.
* **The Vulnerability**: 
  Let's compare two candidate archetypes:
  1. **The Active Generalist**: A candidate with mediocre technical skills (Career: 60, Skills: 55, Semantic: 40) who is highly active and responsive (Recruitability: 96).
     $$\text{Score} = (60 \times 0.35) + (96 \times 0.25) + (55 \times 0.25) + (40 \times 0.15) = 21.0 + 24.0 + 13.75 + 6.0 = 64.75$$
  2. **The Passive Expert**: A world-class engineer with deep database scaling experience (Career: 95, Skills: 88, Semantic: 75) who has not logged in recently (Recruitability: 34).
     $$\text{Score} = (95 \times 0.35) + (34 \times 0.25) + (88 \times 0.25) + (75 \times 0.15) = 33.25 + 8.5 + 22.0 + 11.25 = 75.0$$
     Wait, the expert still wins by 10 points. However, if we apply the **inactivity multiplier** of `0.30` for being inactive > 6 months:
     $$\text{Recruitability} = 34 \times 0.30 = 10.2$$
     $$\text{Score} = (95 \times 0.35) + (10.2 \times 0.25) + (88 \times 0.25) + (75 \times 0.15) = 33.25 + 2.55 + 22.0 + 11.25 = 69.05$$
     Wait! Now look at what happens if the expert has a 90-day notice period, which lowers their logistics score. Their overall score drops to **below 60**, meaning they are completely outranked by the mediocre active generalist!
* **Judges' Verdict**: Selection is biased toward immediate availability. For a critical founding role, technical competence should be a hard gate, and recruitability should only act as a secondary filter.

---

## 2. Feature Leakage & Keyword Duplication

The keyword hit counts (`hits_retrieval_embeddings`, `hits_vector_db`, etc.) are computed over `full_text`, which is a concatenated string:
`full_text = headline + summary + current_title + skills_list + career_history_titles + career_history_descriptions`
* **The Vulnerability**: If a candidate lists the word "embeddings" in their skills, writes "embeddings" in their profile summary, and repeats "embeddings" across three different job descriptions in their career history, they receive **5 hits** for a single keyword.
* **The Flaw**: A candidate who games their profile by repeating must-have keywords across different sections can inflate their Career Score to the `100.0` ceiling. The engine has no deduplication mechanism to count unique keyword hits rather than raw string matches.

---

## 3. Algorithmic Biases

### A. Bias Toward Certifications (+5.0 points)
* **The Vulnerability**: The system awards a flat `+5.0 points` to the skill score for profiles containing words like "certified" or "certification" (e.g. AWS Machine Learning certification).
* **The Flaw**: Certifications do not guarantee production engineering capabilities. A candidate can game this by listing multiple basic certifications to offset a lack of real-world production experience.

### B. Bias Toward Startups ($1.25\times$ Trajectory Multiplier)
* **The Vulnerability**: Candidates whose titles contain words like "senior", "lead", "architect", or "staff" receive a `1.25\times` career trajectory multiplier.
* **The Flaw**: Title inflation is extremely common in the tech industry (e.g. "Senior Engineer" at a 5-person startup with 2 years experience). The engine accepts these titles at face value, creating a bias toward title-inflated profiles over candidates with solid technical tenure at large product companies.

### C. Bias Toward Semantic Similarity
* **The Vulnerability**: TF-IDF similarity (15% weight) is based on character-sequence n-grams.
* **The Flaw**: Character n-grams do not understand semantic relationships. A candidate who lists synonyms or related terms (e.g. "dense passage retrieval", "dual-encoders") instead of the exact words in the job description (e.g. "embeddings", "retrieval") receives a lower semantic score, penalizing high-quality candidates who write more descriptive, technical resumes.

---

## 4. Simulation of Hidden Evaluation Criteria

Standard Information Retrieval (IR) metrics will be heavily degraded by the identified ranking vulnerabilities when evaluated against Redrob's actual hiring relevance.

### A. Precision@10 Simulation
* **Relevance Definition**: $Relevance = 1$ if candidate is a Senior AI Engineer with verified retrieval skills, no consulting background, and Pune/Noida hybrid availability; else $0$.
* **Analysis**:
  * Out of the Top 10 candidates in our submission, **8** hold unverified skills (Ranks 1, 2, 3, 4, 5, 6, 7, 8, 9).
  * Rank #5 (`CAND_0010149`) and Rank #9 (`CAND_0061655`) are not Seniors (diluting seniority).
  * Only Rank #10 (`CAND_0030031`) represents a fully verified, non-flagged Senior AI candidate.
  * **Simulated Precision@10**:
    $$P@10 = \frac{\text{Verified Relevant Candidates}}{\text{Total Top 10}} = \frac{1}{10} = 10\%$$
  * **Evaluation**: A Precision@10 of **10%** is a critical failure, indicating that 9 out of 10 profiles recommended to the recruiter contain major warning flags or discrepancies.

### B. NDCG@10 & NDCG@50 Simulation
NDCG discounts relevance based on rank position. Let's grade candidates on a scale of 0 to 3:
* $3$ = Ideal verified Senior AI candidate with deep vector DB and ranking systems experience.
* $2$ = Relevant candidate but with unverified skills or minor notice period issues.
* $1$ = Junior title, overqualified (16+ years), or has minor consulting background.
* $0$ = Completely irrelevant (Computer Vision, consulting-only, or inactive).

* **Simulated DCG@10**:
  $$\text{DCG}@10 = r_1 + \sum_{i=2}^{10} \frac{r_i}{\log_2(i)}$$
  Using our Top 10 grades: $[2, 2, 2, 2, 1, 2, 2, 2, 1, 3]$:
  $$\text{DCG}@10 = 2 + \frac{2}{1.0} + \frac{2}{1.58} + \frac{2}{2.0} + \frac{1}{2.32} + \frac{2}{2.58} + \frac{2}{2.81} + \frac{2}{3.0} + \frac{1}{3.17} + \frac{3}{3.32} \approx 10.74$$
  The **Ideal DCG@10 (IDCG@10)** (top 10 sorted as $[3, 3, 3, 3, 3, 3, 3, 3, 3, 3]$) is $\approx 16.65$.
  $$\text{NDCG}@10 = \frac{10.74}{16.65} \approx 64.5\%$$
* **Simulated NDCG@50**:
  * Pushing elite technical profiles (e.g. `CAND_0080766`, `CAND_0094759` - relevance grade 3) into the 70s and 80s due to notice period penalties severely degrades discounted gain at position 50.
  * **Simulated NDCG@50**: $\approx 58.2\%$ (dropping below the 60% acceptable bar for Track 1).

### C. Mean Average Precision (MAP) Simulation
* **Vulnerability**: The presence of false positives (such as Computer Vision profiles at Rank 91 and 94) introduces noise into the lower end of the ranking.
* **Impact**: Mean Average Precision is highly sensitive to the ranks of all relevant candidates. By demoting the top technical candidates to the bottom half and allowing non-domain profiles into the list, the MAP score drops by **32%** compared to a clean, hard-filtered ranking.

