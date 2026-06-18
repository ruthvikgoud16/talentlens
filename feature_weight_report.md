# TalentLens X — Feature Weight Report
This report describes the mathematical model, feature groups, and weighting matrix of the optimized TalentLens X ranking engine, tailored for the Redrob Senior AI Engineer job description.

## Core Scoring Architecture
The candidate ranking model uses a 4-component weighted aggregate system to evaluate candidates:

$$\text{Final Score} = (\text{Career Score} \times 0.35) + (\text{Recruitability Index} \times 0.25) + (\text{Skill Relevance} \times 0.25) + (\text{Semantic Similarity} \times 0.15) - (\text{Risk Penalty} \times 0.10)$$

---

## 1. Explicit Feature Groups
To align candidates with the specific technical requirements of the Redrob AI team, we group keywords into six distinct feature areas and search candidate profiles for occurrences.

| Feature Group | Target Keywords / Technologies | Weight / Impact |
| :--- | :--- | :--- |
| **Retrieval & Embeddings** | `embeddings`, `retrieval`, `sentence-transformers`, `bge`, `e5`, `openai embeddings`, `dense retrieval`, `bi-encoder`, `cross-encoder` | High (8.0 pts/hit in Career Base) |
| **Vector Databases** | `pinecone`, `weaviate`, `qdrant`, `milvus`, `faiss`, `opensearch`, `elasticsearch`, `vector database`, `vector search` | High (8.0 pts/hit in Career Base) |
| **Ranking & Search Systems** | `ranking`, `search engine`, `hybrid search`, `sparse retrieval`, `bm25`, `tfidf`, `recommender`, `ltr`, `learning to rank` | High (8.0 pts/hit in Career Base) |
| **Production ML / MLOps** | `deployed`, `production`, `scaled`, `latency`, `optimized`, `real-time`, `serving`, `monitoring`, `mlops`, `onnx`, `tensorrt` | Medium (6.0 pts/hit in Career Base) |
| **Evaluation Frameworks** | `evaluation framework`, `ndcg`, `mrr`, `map`, `a/b testing`, `precision`, `recall`, `offline evaluation` | High (8.0 pts/hit in Career Base) |
| **Startup & Ownership** | `founding`, `founding team`, `architect`, `lead`, `mentor`, `product company`, `saas`, `startup`, `founder` | Medium (6.0 pts/hit in Career Base) |

---

## 2. Career Evidence & Trajectory (35% Weight)
Determines whether a candidate's background, tenure, and trajectory fit the senior level requirements.

* **Experience Scaling (JD Preferred range: 5 to 9 years)**:
  * $5.0 \le \text{years} \le 9.0 \Rightarrow 1.0$ (Ideal fit)
  * $\text{years} > 9.0 \Rightarrow 0.85$ (Slightly overqualified penalty)
  * $3.0 \le \text{years} < 5.0 \Rightarrow 0.75$ (Slightly underqualified)
  * $0.0 < \text{years} < 3.0 \Rightarrow 0.40$ (Junior candidate)
* **FutureFit Career Progression**:
  * If a candidate starts as a software engineer/developer and progresses to senior, lead, staff, or architect roles, they receive a **$1.25\times$ trajectory multiplier**.
  * Candidates whose profiles indicate a transition away from engineering into non-technical fields (e.g. sales, customer service) are penalized (**$0.30\times$ multiplier**).
* **FutureFit Leadership Trajectory**:
  * Active mentoring, hiring, and architecting experiences yield up to **+10.0 points** in career score.
* **Redrob Constraints & Exclusions**:
  * **Consulting Firm Penalty**: Candidates whose career history is entirely or predominantly with outsourcing firms (e.g., TCS, Infosys, Wipro, Cognizant, Accenture) receive a penalty of up to **-40.0 points** proportional to the consulting ratio.
  * **Non-Domain Title Penalty**: Candidates holding titles in irrelevant AI fields (e.g., Computer Vision, Speech Recognition, Robotics) receive a severe **-45.0 points** career penalty.

---

## 3. Skill Relevance & Validation (25% Weight)
Combines explicit skill matching with Truth Engine validation.

* **Target Skill Matching**:
  * Must-haves (e.g. `embeddings`, `retrieval`, `milvus`, `weaviate`, `qdrant`, `faiss`) are weighted **2.5 to 3.0**.
  * Nice-to-haves (e.g. `llm`, `lora`, `recommendation`, `xgboost`) are weighted **1.5**.
* **Proficiency & Tenure Multipliers**:
  * **Proficiency**: Advanced skills are scaled by **$1.0\times$**, intermediate by **$0.75\times$**, and beginner by **$0.45\times$**.
  * **Tenure**: Skills practiced for $\ge 12$ months receive a **$1.1\times$ bonus**, while shorter-tenured skills are scaled by **$0.9\times$**.
* **Truth Engine validations**:
  * **Skill Evidence Validation**: Claims of must-have skills that are completely absent from career description details receive up to **-24.0 points** (skill evidence penalty).
  * **Certification Validation**: Verified certifications (e.g., AWS Machine Learning, TensorFlow Developer, Google Cloud ML Professional) grant a **+5.0 points** bonus.

---

## 4. Recruitability Index & Behavioral Signals (25% Weight)
A composite measure of availability, responsiveness, and logistical fit.

* **Behavioral Component (60%)**:
  * **Recruiter Response Rate**: Weight 20%
  * **Interview Completion Rate**: Weight 20%
  * **Open to Work flag**: Weight 20%
  * **GitHub Activity Score**: Weight 15% (rewards active coding and open-source contributions)
  * **Profile Completeness Score**: Weight 15%
  * **Average Response Time**: Weight 10% (under 24 hours = full marks)
* **Logistics Component (40%)**:
  * **Notice Period**: Sub-15 days = 100% score; 30 days = 90% score; 60 days = 70% score; 90+ days = 25% score.
  * **Willingness to Relocate**: 100% score for relocating; 65% for stationary candidates.
  * **Work Mode Preference**: Hybrid/Remote = 100%; purely onsite preference = 75% score.
* **Activity Recency Multiplier**:
  * Active within 30 days = **$1.0\times$ multiplier**
  * Active 60-90 days = **$0.75\times$ multiplier**
  * Active >180 days (6 months) = **$0.30\times$ multiplier**

---

## 5. Contradiction & Honeypot Detection (Truth Engine)
Automatically detects profiles that attempt to manipulate rankings or display inconsistent data.

1. **Claimed Experience vs History Count**: Penalizes candidates claiming $>3$ years experience but holding zero career history records (**-50.0 pts**), or claiming $>15$ years with only one job entry (**-35.0 pts**).
2. **AI Headline vs Zero Description Evidence**: Penalizes profiles with AI/ML headlines that contain no matching technical terms in their descriptions (**-30.0 pts**).
3. **Keyword Stuffing**: Penalizes profiles showing 100% non-technical career titles but listing advanced AI/ML skills (**-20.0 pts**).
4. **Seniority Contradictions**: Penalizes candidates claiming "Senior", "Lead", or "Architect" titles with less than 3 years of total experience (**-25.0 pts**).
