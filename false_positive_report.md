# Redrob Evaluation Committee — False Positive Report

This report documents candidates in the Top 100 who represent clear false positives due to domain mismatches, junior seniority, or outsourcing backgrounds.

---

## 1. Candidate: `CAND_0052195` (Rank #91) & `CAND_0032955` (Rank #94)
* **Incorrect Rank**: Ranks #91 and #94.
* **Why the Candidate is Incorrectly Ranked**: These are **Computer Vision Engineers** whose primary experiences involve image classification, GANs, and object detection. The job description is strictly for a Senior AI Engineer specializing in **Retrieval, Vector Databases, Search Ranking, and NLP**.
* **What Evidence Was Missed**: The candidate profiles explicitly state their core domains are Computer Vision. By including them in the Top 100, the system displays a lack of domain filtering.
* **Flaw in Scoring Logic**: 
  * **Soft Penalty vs. Hard Disqualification**: The engine applies a `-45.0 points` career score penalty for CV titles. However, because the final score is a weighted sum (where Career is 35% and Recruitability is 25%), a candidate with high recruitability (e.g. `CAND_0052195` has `94/100`) and a strong general semantic score still lands in the Top 100.
  * **Remedy**: The engine needs a **hard exclusion filter** that completely removes profiles containing terms from `NON_DOMAIN_SKILLS` or `non_domain_titles` from the submission file.

---

## 2. Candidate: `CAND_0043860` (Rank #21)
* **Incorrect Rank**: Rank #21.
* **Why the Candidate is Incorrectly Ranked**: This candidate is a **Junior ML Engineer**. Redrob is hiring a founding member who will act as a Senior AI Engineer / Architect. Placing a junior-titled candidate in the top 25 is a severe mismatch.
* **What Evidence Was Missed**: The current title `"Junior Ml Engineer"` is parsed, but the engine fails to detect the "Junior" prefix as a disqualifying signal.
* **Flaw in Scoring Logic**: 
  * **Lack of Seniority Checks**: While the engine checks for years of experience (6.0 years matches the 5–9 years bracket), it does not check the current title for junior prefixes. A candidate with 6 years experience who is still a "Junior" represents a slow career trajectory, yet they bypass checks due to simple tenure calculations.
  * **Remedy**: Implement a **Junior Title Penalty (-30.0 points)** or require that the current title must not contain junior keywords.

---

## 3. Candidate: `CAND_0005649` (Rank #11)
* **Incorrect Rank**: Rank #11.
* **Why the Candidate is Incorrectly Ranked**: This candidate has a career history at **Tata Consultancy Services (TCS)**, a major outsourcing/consulting firm. The JD explicitly says: *"product company not consulting... Capgemini/TCS/Wipro are negative signals."*
* **What Evidence Was Missed**: The TCS tenure is parsed in their companies list, but the penalty is too soft.
* **Flaw in Scoring Logic**: 
  * **Ratio-based Consulting Penalty**: The consulting penalty is scaled by the ratio of consulting companies to total companies (`consulting_count / len(companies)`). Since they have 2 product companies and 1 consulting company in their history, their ratio is `0.33`, resulting in a minor penalty. 
  * **Remedy**: A candidate with *any* significant consulting tenure should receive a flat, high penalty, rather than a soft ratio-based deduction.
