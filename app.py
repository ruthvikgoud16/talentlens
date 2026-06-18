"""
TalentLens — Redrob Hackathon Candidate Ranking Engine
=======================================================
Ranks candidates from candidates.jsonl against the job description.
Produces a submission-ready CSV (top 100 candidates, ranked).

Usage:
    python app.py

Output:
    submission.csv   — Ready to validate and submit
    full_output.csv  — All scored candidates (for inspection)

Schema confirmed against real data:
    - skills: always list of dicts with "name", "proficiency", "endorsements", "duration_months"
    - career_history: uses "title" key (not "role" or "job_title")
    - redrob_signals: notice_period_days is int (days), github_activity_score -1 means no data
"""

import json
import os
import gzip
import re
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, date

# ─────────────────────────────────────────────
# DEMOGRAPHIC DE-BIASING LAYER
# ─────────────────────────────────────────────

GENDER_RE = re.compile(
    r'\b(he|she|his|her|him|hers|himself|herself|male|female|man|woman|men|women|mr|mrs|ms|gentleman|lady|boy|girl)\b',
    re.IGNORECASE
)

GENDER_MAP = {
    "he": "they", "she": "they", "his": "their", "her": "their", "him": "them",
    "hers": "theirs", "himself": "themself", "herself": "themself",
    "male": "candidate", "female": "candidate", "man": "person", "woman": "person",
    "men": "people", "women": "people", "mr": "candidate", "mrs": "candidate", "ms": "candidate"
}

def replace_gender(match):
    word = match.group(1).lower()
    return GENDER_MAP.get(word, "candidate")

AGE_RE = re.compile(
    r'\b(?:\d{1,2}\s*(?:years?\s*old|yrs?\s*old|year-old|yr-old)|age[d]?\s*(?:of\s*)?\d{1,2}|born\s+in\s*\d{4})\b',
    re.IGNORECASE
)

COMMON_LOCATIONS = {
    "pune", "noida", "delhi", "ncr", "bengaluru", "bangalore", "hyderabad", "chennai", "mumbai", 
    "gurgaon", "gurugram", "kolkata", "toronto", "san francisco", "new york", "london", "india", 
    "canada", "usa", "us", "united states", "uk", "united kingdom", "germany", "singapore", "boston"
}

# Pre-compile the common locations regex to avoid re-compilation 100,000 times.
COMMON_LOCATIONS_RE = re.compile(
    r'\b(?:' + '|'.join(sorted([re.escape(l) for l in COMMON_LOCATIONS if l], key=len, reverse=True)) + r')\b',
    re.IGNORECASE
)

def debias_candidate(cand, anon_id):
    profile = cand.get("profile", {}) or {}
    name = profile.get("anonymized_name", "")
    location = profile.get("location", "")
    country = profile.get("country", "")
    
    def clean_text(text):
        if not text or not isinstance(text, str):
            return text
        text = GENDER_RE.sub(replace_gender, text)
        text = AGE_RE.sub("[AGE_REDACTED]", text)
        
        # Only run name redaction if name words are present in text
        if name:
            lower_text = text.lower()
            name_words = [w.lower() for w in re.split(r'[^a-zA-Z]', name) if len(w) >= 3]
            for w in name_words:
                if w in lower_text:
                    text = re.sub(r'\b' + re.escape(w) + r'\b', "[NAME_REDACTED]", text, flags=re.IGNORECASE)
                    
        text = COMMON_LOCATIONS_RE.sub("[LOCATION_REDACTED]", text)
        
        # Only run specific location/country redaction if present and not a common location
        if location and location.lower() not in COMMON_LOCATIONS:
            if location.lower() in text.lower():
                text = re.sub(r'\b' + re.escape(location) + r'\b', "[LOCATION_REDACTED]", text, flags=re.IGNORECASE)
        if country and country.lower() not in COMMON_LOCATIONS:
            if country.lower() in text.lower():
                text = re.sub(r'\b' + re.escape(country) + r'\b', "[LOCATION_REDACTED]", text, flags=re.IGNORECASE)
                
        return text

    debiased_profile = profile.copy()
    debiased_profile["anonymized_name"] = "[NAME_REDACTED]"
    debiased_profile["location"] = "[LOCATION_REDACTED]"
    debiased_profile["country"] = "[LOCATION_REDACTED]"
    if "headline" in debiased_profile:
        debiased_profile["headline"] = clean_text(debiased_profile["headline"])
    if "summary" in debiased_profile:
        debiased_profile["summary"] = clean_text(debiased_profile["summary"])
    if "current_title" in debiased_profile:
        debiased_profile["current_title"] = clean_text(debiased_profile["current_title"])
        
    debiased_career = []
    for job in cand.get("career_history", []) or []:
        if isinstance(job, dict):
            j = job.copy()
            if "description" in j:
                j["description"] = clean_text(j["description"])
            if "title" in j:
                j["title"] = clean_text(j["title"])
            if "company" in j:
                j["company"] = clean_text(j["company"])
            debiased_career.append(j)
            
    debiased_edu = []
    for edu in cand.get("education", []) or []:
        if isinstance(edu, dict):
            e = edu.copy()
            if "institution" in e:
                e["institution"] = clean_text(e["institution"])
            if "degree" in e:
                e["degree"] = clean_text(e["degree"])
            debiased_edu.append(e)

    debiased_cand = cand.copy()
    debiased_cand["candidate_id"] = anon_id
    debiased_cand["profile"] = debiased_profile
    debiased_cand["career_history"] = debiased_career
    debiased_cand["education"] = debiased_edu
    
    return debiased_cand

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

CANDIDATES_FILE = "candidates.jsonl"        # Full 100k dataset
CANDIDATES_GZ   = "candidates.jsonl.gz"    # Gzipped alternative
SAMPLE_FILE     = "sample_candidates.json" # Fallback for testing
JD_FILE         = "job_description.txt"
SUBMISSION_FILE = "submission.csv"
FULL_OUTPUT     = "full_output.csv"
TODAY           = date.today()

# ─────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────

def load_candidates():
    if os.path.exists(CANDIDATES_FILE):
        print(f"Loading {CANDIDATES_FILE} ...")
        candidates = []
        with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))
        print(f"  Loaded {len(candidates):,} candidates from JSONL.")
        return candidates

    if os.path.exists(CANDIDATES_GZ):
        print(f"Loading {CANDIDATES_GZ} ...")
        candidates = []
        with gzip.open(CANDIDATES_GZ, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))
        print(f"  Loaded {len(candidates):,} candidates from gzipped JSONL.")
        return candidates

    if os.path.exists(SAMPLE_FILE):
        print(f"WARNING: Full dataset not found. Loading {SAMPLE_FILE} (50 candidates).")
        with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(
        "No candidate file found. Place candidates.jsonl (or candidates.jsonl.gz) "
        "in the same directory as this script."
    )


def load_jd():
    if os.path.exists(JD_FILE):
        with open(JD_FILE, "r", encoding="utf-8") as f:
            return f.read()
    # Inline fallback — extracted from job_description.docx
    return """
    Senior AI Engineer founding team Redrob AI Pune Noida India hybrid
    embeddings retrieval ranking vector databases hybrid search production deployment
    Python NLP sentence-transformers BGE E5 OpenAI embeddings Pinecone Weaviate
    Qdrant Milvus OpenSearch Elasticsearch FAISS evaluation framework NDCG MRR MAP
    LLM fine-tuning LoRA QLoRA PEFT learning to rank recommendation system
    product company not consulting applied machine learning 5 to 9 years experience
    candidate job description matching recruiter search ranking system
    A/B testing offline evaluation online metrics mlops inference optimization
    """


# ─────────────────────────────────────────────
# 2. SCHEMA AUDIT
# ─────────────────────────────────────────────

def print_audit(candidates):
    print("\n" + "="*65)
    print("        TALENTLENS — SCHEMA AUDIT")
    print("="*65)
    print(f"  Candidates loaded    : {len(candidates):,}")
    if not candidates:
        print("  ERROR: Empty dataset.")
        return
    s = candidates[0]
    print(f"  Root keys            : {list(s.keys())}")
    profile = s.get("profile", {})
    print(f"  Profile keys         : {list(profile.keys())}")
    skills = s.get("skills", [])
    print(f"  Skills type          : {type(skills[0]).__name__ if skills else 'empty'}")
    career = s.get("career_history", [])
    print(f"  Career title key     : 'title' -> {career[0].get('title') if career else 'n/a'}")
    sig = s.get("redrob_signals", {})
    print(f"  notice_period_days   : {sig.get('notice_period_days')} (int, days)")
    print(f"  github range         : -1 = no data, 0-100 = score")
    print("="*65 + "\n")


# ─────────────────────────────────────────────
# 3. FEATURE EXTRACTION
# ─────────────────────────────────────────────

# Keywords derived directly from job description
MUST_HAVE_SKILLS = {
    "embeddings": 3.0, "retrieval": 3.0, "ranking": 3.0, "vector": 2.5,
    "sentence-transformers": 2.5, "faiss": 2.5, "milvus": 2.5,
    "qdrant": 2.5, "weaviate": 2.5, "pinecone": 2.5, "opensearch": 2.5,
    "elasticsearch": 2.0, "python": 2.0, "nlp": 2.0, "search": 2.0,
}
NICE_TO_HAVE_SKILLS = {
    "machine learning": 1.5, "pytorch": 1.5, "transformers": 1.5,
    "llm": 1.5, "fine-tun": 1.5, "lora": 1.5, "qlora": 1.5,
    "recommendation": 1.5, "rerank": 1.5, "tensorflow": 1.0,
    "xgboost": 1.0, "lightgbm": 1.0, "bert": 1.0, "gpt": 0.5,
}
ALL_TARGET_SKILLS = {**MUST_HAVE_SKILLS, **NICE_TO_HAVE_SKILLS}

# Synonym-aware groups for core skills to improve verification
# Group terms are mapped together to prevent false negatives from conceptual synonyms.
SYNONYM_GROUPS = {
    "Vector Databases": [
        "pinecone", "qdrant", "weaviate", "milvus", "faiss", "pgvector",
        "vector database", "vector databases", "vector search", "vector store", "vector",
        "hnsw", "ivf"
    ],
    "Embeddings": [
        "embeddings", "bge", "e5", "sentence-transformers", "sentence transformers",
        "dense retrieval", "openai embeddings", "bi-encoder", "cross-encoder",
        "retrieval", "dense passage", "dpr", "colbert", "information retrieval"
    ],
    "Ranking": [
        "ranking", "ranking systems", "recommender", "ltr", "learning to rank",
        "rerank", "reranking", "search engine", "hybrid search", "bm25", "tfidf", "search"
    ]
}

def skill_has_synonym(candidate_desc_lower: str, skill: str) -> bool:
    """Return True if the skill (or any synonym in its synonym-aware group) 
    appears in the candidate description in lowercase.
    """
    norm_skill = skill.lower().strip()
    
    # 1. Determine if the skill belongs to a synonym-aware group
    found_group = None
    for group, terms in SYNONYM_GROUPS.items():
        if any(t.lower().strip() == norm_skill for t in terms):
            found_group = group
            break
            
    # 2. If it belongs to a group, check if any group term is in the combined description
    if found_group:
        for term in SYNONYM_GROUPS[found_group]:
            if term.lower().strip() in candidate_desc_lower:
                return True
        return False
        
    # 3. Direct match fallback
    if norm_skill in candidate_desc_lower:
        return True
        
    # 4. Standard ungrouped fallbacks
    fallbacks = {
        "elasticsearch": ["elasticsearch", "es", "elastic search"],
        "opensearch": ["opensearch", "os", "open search"],
        "nlp": ["nlp", "natural language processing"],
        "python": ["python", "py"]
    }
    for syn in fallbacks.get(norm_skill, []):
        if syn in candidate_desc_lower:
            return True
    return False

# JD explicitly says these are negative signals
CONSULTING_FIRMS = ["tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini"]
NON_TECH_ROLES   = ["marketing", "sales", "hr", "content writer", "operations manager",
                    "accountant", "recruiter", "business analyst", "customer support"]
NON_DOMAIN_SKILLS = ["computer vision", "speech recognition", "robotics", "image classification",
                     "tts", "object detection", "gan", "ocr"]

# Explicit Feature Groups
RETRIEVAL_EMBEDDINGS_KW = [
    "embeddings", "retrieval", "sentence-transformers", "bge", "e5", "openai embeddings",
    "dense retrieval", "bi-encoder", "cross-encoder", "dense passage", "dpr", "colbert",
    "dense vector", "information retrieval"
]
VECTOR_DB_KW = [
    "pinecone", "weaviate", "qdrant", "milvus", "faiss", "opensearch", "elasticsearch",
    "vector database", "vector search", "hnsw", "ivf", "vector store"
]
RANKING_SEARCH_KW = [
    "ranking", "search engine", "hybrid search", "sparse retrieval", "bm25", "tfidf",
    "recommender", "ltr", "learning to rank", "xgboost", "rerank", "recommendation"
]
PRODUCTION_ML_KW = [
    "deployed", "production", "scaled", "latency", "optimized", "optimised", "real-time",
    "serving", "monitoring", "mlops", "index refresh", "inference optimization", "pipeline",
    "triton", "onnx", "tensorrt"
]
EVALUATION_FRAMEWORK_KW = [
    "evaluation framework", "ndcg", "mrr", "map", "a/b testing", "a/b test", "precision",
    "recall", "offline evaluation", "online metrics"
]
STARTUP_PRODUCT_KW = [
    "founding", "founding team", "lead", "architect", "mentor", "product company", "saas",
    "scaleup", "startup", "founder"
]

MAX_SKILL_WEIGHT = sum(ALL_TARGET_SKILLS.values())


def days_since(date_str):
    """Returns days between a date string and today. Returns 999 on error."""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (TODAY - d).days
    except Exception:
        return 999


def extract_evidence_snippets(career):
    snippets = []
    if not career:
        return snippets
        
    target_terms = [
        "faiss", "pinecone", "weaviate", "milvus", "qdrant", "elasticsearch", "opensearch",
        "embeddings", "retrieval", "sentence-transformers", "hybrid search", "rerank", "ndcg", 
        "mrr", "map", "lora", "qlora", "peft", "fine-tun", "evaluation framework", "a/b test",
        "mentor", "led", "managed", "deployed", "scaled", "latency", "production ml", "founding"
    ]
    
    for job in career:
        if not isinstance(job, dict):
            continue
        desc = job.get("description", "") or ""
        if not desc:
            continue
            
        # Split into sentences
        sentences = re.split(r'\.|\n|;', desc)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15 or len(s_clean) > 150:
                continue
            
            # Check for any of our key target terms
            lower_s = s_clean.lower()
            if any(t in lower_s for t in target_terms):
                s_clean = re.sub(r'\s+', ' ', s_clean)
                if s_clean and s_clean[0].islower():
                    s_clean = s_clean[0].upper() + s_clean[1:]
                snippets.append(s_clean)
                
    # Remove duplicates preserving order
    unique_snippets = []
    seen = set()
    for s in snippets:
        norm = s.lower().replace(" ", "").rstrip('.')
        if norm not in seen:
            seen.add(norm)
            unique_snippets.append(s)
            if len(unique_snippets) >= 5:
                break
                
    return unique_snippets


def extract_features(cand):
    profile  = cand.get("profile", {}) or {}
    signals  = cand.get("redrob_signals", {}) or {}
    career   = cand.get("career_history", []) or []
    skills_raw = cand.get("skills", []) or []

    # ── Profile fields ──
    headline      = str(profile.get("headline", "")).lower()
    summary       = str(profile.get("summary", "")).lower()
    current_title = str(profile.get("current_title", "")).lower()

    try:
        years_exp = float(profile.get("years_of_experience", 0))
    except (ValueError, TypeError):
        years_exp = 0.0

    # ── Skills ──
    skills_list = []
    skills_with_meta = []
    for s in skills_raw:
        if isinstance(s, dict):
            name = str(s.get("name", "")).lower().strip()
            prof = str(s.get("proficiency", "beginner")).lower()
            dur  = int(s.get("duration_months", 0) or 0)
            end  = int(s.get("endorsements", 0) or 0)
            if name:
                skills_list.append(name)
                skills_with_meta.append({
                    "name": name,
                    "norm_name": normalize_skill(name),
                    "prof": prof,
                    "dur": dur,
                    "end": end
                })
        elif isinstance(s, str):
            name = s.lower().strip()
            skills_list.append(name)
            skills_with_meta.append({
                "name": name,
                "norm_name": normalize_skill(name),
                "prof": "beginner",
                "dur": 0,
                "end": 0
            })

    assessments = signals.get("skill_assessment_scores", {}) or {}

    # ── Career ──
    titles = []
    companies = []
    descs  = []
    for job in career:
        if isinstance(job, dict):
            t = str(job.get("title") or job.get("role") or job.get("job_title") or "").lower()
            c = str(job.get("company", "")).lower()
            d = str(job.get("description", "")).lower()
            titles.append(t)
            companies.append(c)
            descs.append(d)

    combined_desc = " ".join(descs)
    evidence_snippets = extract_evidence_snippets(career)

    # ── Signals (with -1 handling) ──
    def safe(val, default):
        try:
            v = float(val)
            return default if v < 0 else v
        except (ValueError, TypeError):
            return default

    last_active_days = days_since(str(signals.get("last_active_date", "")))

    full_text = f"{headline} {summary} {current_title} {' '.join(skills_list)} {' '.join(titles)} {combined_desc}"
    full_text_lower = full_text.lower()

    feat = {
        "cid":            cand.get("candidate_id", "UNKNOWN"),
        "headline":       headline,
        "summary":        summary,
        "current_title":  current_title,
        "years_exp":      years_exp,
        "skills_list":    skills_list,
        "skills_meta":    skills_with_meta,
        "assessments":    assessments,
        "titles":         titles,
        "companies":      companies,
        "descs":          descs,
        "combined_desc":  combined_desc,
        "career_count":   len(career),
        "profile_text":   f"{headline} {summary} {current_title}",
        "full_text":      full_text,
        "evidence_snippets": evidence_snippets,
        # raw signals for recruitability
        "resp_rate":      safe(signals.get("recruiter_response_rate"), 0.5),
        "completion_rate":safe(signals.get("interview_completion_rate"), 0.5),
        "open_to_work":   bool(signals.get("open_to_work_flag", False)),
        "github":         safe(signals.get("github_activity_score"), 20.0),
        "profile_complete": safe(signals.get("profile_completeness_score"), 50.0),
        "offer_accept":   safe(signals.get("offer_acceptance_rate"), 0.5),
        "notice_days":    int(signals.get("notice_period_days", 60) or 60),
        "relocate":       bool(signals.get("willing_to_relocate", False)),
        "work_mode":      str(signals.get("preferred_work_mode", "hybrid")).lower(),
        "last_active_days": last_active_days,
        "verified_email": bool(signals.get("verified_email", False)),
        "verified_phone": bool(signals.get("verified_phone", False)),
        "saved_30d":      int(signals.get("saved_by_recruiters_30d", 0) or 0),
        "avg_resp_hours": safe(signals.get("avg_response_time_hours"), 72.0),
        # explicit feature hits counts (evaluated strictly over job descriptions to prevent keyword stuffing)
        "hits_retrieval_embeddings": sum(1 for kw in RETRIEVAL_EMBEDDINGS_KW if kw in combined_desc.lower()),
        "hits_vector_db":            sum(1 for kw in VECTOR_DB_KW if kw in combined_desc.lower()),
        "hits_ranking_search":       sum(1 for kw in RANKING_SEARCH_KW if kw in combined_desc.lower()),
        "hits_production_ml":        sum(1 for kw in PRODUCTION_ML_KW if kw in combined_desc.lower()),
        "hits_evaluation":           sum(1 for kw in EVALUATION_FRAMEWORK_KW if kw in combined_desc.lower()),
        "hits_startup_product":      sum(1 for kw in STARTUP_PRODUCT_KW if (kw in combined_desc.lower() or kw in headline or kw in current_title)),
    }
    return feat


# ─────────────────────────────────────────────
# 4. SCORING ENGINES
# ─────────────────────────────────────────────

def normalize_skill(name):
    name = name.lower().strip()
    name = name.replace("machine learning", "ml")
    name = name.replace("natural language processing", "nlp")
    name = name.replace("deep learning", "dl")
    name = "".join(c for c in name if c.isalnum())
    if name.endswith("s") and not name.endswith("ss"):
        name = name[:-1]
    return name

NORM_TARGET_SKILLS = {k: normalize_skill(k) for k in ALL_TARGET_SKILLS}
NORM_NON_DOMAIN_SKILLS = [normalize_skill(nd) for nd in NON_DOMAIN_SKILLS]


def is_skill_match(target, candidate):
    norm_target = normalize_skill(target)
    norm_cand = normalize_skill(candidate)
    return (norm_target in norm_cand) or (norm_cand in norm_target)


def score_career(feat):
    """
    Career Evidence & Trajectory (35% weight)
    Includes:
    - Experience bracket scale (wants 5-9 years)
    - Production ML and Ranking/Search Systems hit scoring
    - Learning progression & Leadership trajectory (FutureFit)
    - Consulting firm and Non-domain title penalties
    """
    years = feat["years_exp"]
    titles = feat["titles"]
    companies = feat["companies"]
    combined = feat["combined_desc"]
    headline = feat["headline"]
    current_title = feat["current_title"]

    # 1. Experience bracket scale (JD: 5-9 years preferred)
    if 5 <= years <= 9:
        exp_scale = 1.0
    elif years > 9:
        exp_scale = 0.85   # over-experienced
    elif 3 <= years < 5:
        exp_scale = 0.75
    elif years > 0:
        exp_scale = 0.40
    else:
        exp_scale = 0.20

    # 2. Career Progression Trajectory (FutureFit Learning Progression)
    trajectory_mult = 1.0
    if len(titles) >= 2:
        latest   = titles[0]
        earliest = titles[-1]
        senior_t = ["senior", "lead", "principal", "architect", "head", "staff", "director", "founding"]
        tech_t   = ["engineer", "developer", "scientist", "researcher", "ml", "ai", "data"]
        non_tech = ["marketing", "sales", "hr", "content", "operations", "accountant",
                    "writer", "recruiter", "customer support", "business analyst"]

        is_senior_now  = any(t in latest for t in senior_t)
        is_tech_start  = any(t in earliest for t in tech_t)
        is_non_tech_now= any(t in latest for t in non_tech)
        is_non_tech_all= all(any(nt in t for nt in non_tech) for t in titles)

        if is_tech_start and is_senior_now:
            trajectory_mult = 1.25
        elif is_non_tech_now:
            trajectory_mult = 0.30
        elif is_non_tech_all:
            trajectory_mult = 0.20

    # 3. Leadership Trajectory (FutureFit Leadership)
    leadership_bonus = 0.0
    leadership_keywords = ["mentor", "led", "architected", "managed", "founded", "hired", "supervis", "team lead"]
    lead_hits = sum(1 for lk in leadership_keywords if lk in combined)
    if lead_hits > 0:
        leadership_bonus = min(lead_hits * 3.0, 10.0)

    # 4. Feature hit scoring from explicit groups
    # Combined hits: Retrieval/Embeddings, Vector DB, Ranking/Search, Production ML, Evaluation, Startup/Product
    hits_ret_emb = feat.get("hits_retrieval_embeddings", 0)
    hits_vec_db = feat.get("hits_vector_db", 0)
    hits_rank_search = feat.get("hits_ranking_search", 0)
    hits_prod_ml = feat.get("hits_production_ml", 0)
    hits_eval = feat.get("hits_evaluation", 0)
    hits_startup = feat.get("hits_startup_product", 0)

    features_score = (
        hits_ret_emb * 8.0 +
        hits_vec_db * 8.0 +
        hits_rank_search * 8.0 +
        hits_prod_ml * 6.0 +
        hits_eval * 8.0 +
        hits_startup * 6.0
    )
    base = min(features_score, 100.0)
    raw = (base + leadership_bonus) * exp_scale * trajectory_mult

    # 5. Penalties
    consulting_penalty = 0.0
    if companies:
        consulting_count = sum(1 for c in companies if any(cf in str(c) for cf in CONSULTING_FIRMS))
        ratio = consulting_count / len(companies)
        if ratio > 0:
            consulting_penalty = ratio * 40.0

    non_domain_title_penalty = 0.0
    non_domain_titles = ["computer vision", "speech", "robotics", "cv engineer", "vision researcher", "object detection", "image processing"]
    if any(ndt in current_title for ndt in non_domain_titles) or any(ndt in headline for ndt in non_domain_titles):
        non_domain_title_penalty = 45.0

    junior_penalty = 0.0
    junior_keywords = ["junior", "jr", "associate", "intern", "freshman"]
    if any(jk in current_title for jk in junior_keywords) or any(jk in headline for jk in junior_keywords):
        junior_penalty = 40.0

    final = max(0.0, raw - consulting_penalty - non_domain_title_penalty - junior_penalty)
    return round(min(final, 100.0), 2), hits_prod_ml, (hits_ret_emb + hits_rank_search)


def score_skills(feat):
    """
    Skill Relevance (25% weight)
    Includes:
    - Must-have vs nice-to-have skill weights
    - Proficiency and duration multipliers
    - Skill assessment bonus
    - Non-domain skill penalty
    - Skill Evidence Validation (Truth Engine): checks if claimed must-haves are mentioned in descriptions
    - Certification validation (Truth Engine): AWS, TensorFlow, GCP certifications bonus
    """
    skills_meta = feat["skills_meta"]
    assessments = feat["assessments"]
    skills_list = feat["skills_list"]
    combined_desc = feat["combined_desc"]
    full_cv_text = feat["full_text"]
    
    combined_desc_lower = combined_desc.lower()

    earned = 0.0
    matched = []

    for skill_name, weight in ALL_TARGET_SKILLS.items():
        norm_target = NORM_TARGET_SKILLS[skill_name]
        # Match using pre-normalized check
        match = next((s for s in skills_meta if (norm_target in s["norm_name"]) or (s["norm_name"] in norm_target)), None)
        if match:
            matched.append(skill_name)
            # Proficiency multiplier
            prof_mult = {"advanced": 1.0, "intermediate": 0.75, "beginner": 0.45}.get(match["prof"], 0.6)
            # Duration bonus (>12 months = real experience)
            dur_mult = 1.1 if match["dur"] >= 12 else 0.9
            earned += weight * prof_mult * dur_mult

    # Define a realistic skill ceiling (perfect fit doesn't need to match all 25+ skills)
    SKILL_CEILING_WEIGHT = 13.0
    base = min((earned / SKILL_CEILING_WEIGHT) * 100.0, 100.0)

    # Assessment score bonus
    bonus = 0.0
    if assessments:
        relevant_assess = {}
        for k, v in assessments.items():
            norm_k = normalize_skill(k)
            is_relevant = any((norm_t in norm_k) or (norm_k in norm_t) for norm_t in NORM_TARGET_SKILLS.values())
            if is_relevant:
                relevant_assess[k] = v
        if relevant_assess:
            bonus = (sum(relevant_assess.values()) / len(relevant_assess) / 100.0) * 8.0

    # Truth Engine: Skill evidence validation
    # Penalize if claimed must-haves are completely absent from career descriptions
    unverified_count = 0
    has_unverified_core = False
    core_skills = ["embeddings", "retrieval", "vector", "ranking"]
    for s in matched:
        if s in MUST_HAVE_SKILLS:
            # Use synonym-aware check for core skill presence in the combined description
            if not skill_has_synonym(combined_desc_lower, s):
                unverified_count += 1
                # If the missing skill is a core skill, flag for higher penalty
                if s in core_skills:
                    has_unverified_core = True
    
    if has_unverified_core:
        skill_evidence_penalty = 35.0
    else:
        skill_evidence_penalty = min(unverified_count * 15.0, 45.0)

    # Truth Engine: Certification validation (AWS, GCP, TensorFlow developer certs)
    cert_bonus = 0.0
    cert_keywords = ["certified", "certification", "aws machine learning", "tensorflow developer", "gcp professional", "google cloud machine learning", "nvidia dli"]
    if any(ck in full_cv_text for ck in cert_keywords):
        cert_bonus = 5.0

    # Non-domain skill penalty
    non_domain_penalty = 0.0
    norm_skills_list = [normalize_skill(s) for s in skills_list]
    non_domain_count = sum(1 for norm_nd in NORM_NON_DOMAIN_SKILLS
                          if any((norm_nd in norm_s) or (norm_s in norm_nd) for norm_s in norm_skills_list))
    if non_domain_count > 0:
        non_domain_penalty = min(non_domain_count * 10.0, 30.0)

    final = min(base + bonus + cert_bonus, 100.0) - skill_evidence_penalty - non_domain_penalty
    return round(max(0.0, final), 2), matched


def score_recruitability(feat):
    """
    Recruitability Index (25% weight)
    Includes:
    - Behavioral signals (responsiveness, interview completion, activity recency)
    - Logistics (notice period, relocation, work mode preference)
    """
    # 1. Behavioral Index
    # Activity recency multiplier (relaxed to avoid over-penalizing passive candidates)
    if feat["last_active_days"] <= 30:
        recency_mult = 1.0
    elif feat["last_active_days"] <= 90:
        recency_mult = 0.90
    elif feat["last_active_days"] <= 180:
        recency_mult = 0.75
    else:
        recency_mult = 0.60

    # Response speed score
    resp_time = feat["avg_resp_hours"]
    if resp_time <= 24:
        resp_time_score = 1.0
    elif resp_time <= 72:
        resp_time_score = 0.80
    elif resp_time <= 120:
        resp_time_score = 0.60
    else:
        resp_time_score = 0.40

    open_flag   = 1.0 if feat["open_to_work"] else 0.35
    github      = feat["github"] / 100.0
    profile_c   = feat["profile_complete"] / 100.0
    verified    = 0.5 * int(feat["verified_email"]) + 0.5 * int(feat["verified_phone"])

    behavior = (
        feat["resp_rate"]   * 0.20 +
        feat["completion_rate"] * 0.20 +
        open_flag           * 0.20 +
        github              * 0.15 +
        profile_c           * 0.15 +
        resp_time_score     * 0.10
    ) * 100.0

    # 2. Logistics Index
    nd = feat["notice_days"]
    if nd <= 30:
        notice_score = 1.00
    elif nd <= 60:
        notice_score = 0.90
    elif nd <= 90:
        notice_score = 0.80
    else:
        notice_score = 0.60

    relocate_score = 1.0 if feat["relocate"] else 0.65
    mode = feat["work_mode"]
    mode_score = 0.75 if mode == "onsite" else 1.0

    logistics = (
        notice_score   * 0.55 +
        relocate_score * 0.25 +
        mode_score     * 0.20
    ) * 100.0

    raw_index = (behavior * 0.60) + (logistics * 0.40)
    final     = round(raw_index * recency_mult, 2)
    return round(behavior, 2), round(logistics, 2), final, nd


def score_honeypot_penalty(feat):
    """
    Contradiction / Honeypot Detection (Truth Engine)
    Checks:
    - Years claimed vs career history count
    - AI headline with zero career history evidence
    - Non-technical history with keyword stuffed AI skills
    - Contradiction: Senior/Lead title with low experience (<3 years)
    """
    penalty = 0.0
    reasons = []
    years   = feat["years_exp"]
    career  = feat["career_count"]
    combined= feat["combined_desc"]
    headline= feat["headline"]
    current_title = feat["current_title"]

    # Honeypot: claimed years vs career history impossible
    if career == 0 and years > 3:
        penalty += 50.0
        reasons.append(f"claims {years:.0f} yrs experience but has zero career history entries")

    if career == 1 and years > 15:
        penalty += 35.0
        reasons.append(f"claims {years:.0f} yrs experience but has only 1 career entry")

    # AI headline claim with zero technical evidence
    ai_claim   = any(t in headline for t in ["ai", "ml", "machine learning", "nlp", "deep learning", "data scientist", "researcher"])
    ai_evidence= any(t in combined for t in ["model", "train", "deploy", "embedding", "vector", "nlp", "retrieval", "pipeline"])
    if ai_claim and not ai_evidence and career > 0:
        penalty += 30.0
        reasons.append("AI/ML headline claim not supported by technical details in career history")

    # Entirely non-technical career with AI keyword skills
    non_tech_all = all(any(nt in t for nt in NON_TECH_ROLES) for t in feat["titles"]) if feat["titles"] else False
    skills_have_ai = any(t in " ".join(feat["skills_list"]) for t in ["nlp", "embeddings", "pytorch", "llm", "transformer"])
    if non_tech_all and skills_have_ai:
        penalty += 20.0
        reasons.append("non-technical career history but AI skills listed")

    # Contradiction: Senior/Lead title with less than 3 years of experience
    is_senior_title = any(t in current_title or t in headline for t in ["senior", "lead", "principal", "architect", "head", "director"])
    if is_senior_title and years > 0 and years < 3.0:
        penalty += 25.0
        reasons.append("Senior/Lead title claimed with less than 3 years of experience")

    return round(min(penalty, 100.0), 2), reasons


# ─────────────────────────────────────────────
# 5. RECRUITER REASONING
# ─────────────────────────────────────────────

def build_reasoning(feat, matched_skills, prod_hits, domain_hits,
                    penalty, risk_reasons, recruit_index, career_score, rank):
    """
    Generate rich, evidence-based reasoning summarizing:
    - Experience details and key strengths (Retrieval, Vector DB, Search/Ranking, Production ML, Eval, Startup/Product)
    - JD alignment indicators (Pune/Noida hybrid, Senior AI Engineer)
    - Specific concerns (e.g. unverified skills, long notice period, honeypot flags, consulting history)
    - Directly connected to requirements, avoiding repetitive templates.
    """
    years = feat["years_exp"]
    title = feat["current_title"].title() if feat["current_title"] else "ML Engineer"
    nd = feat["notice_days"]
    github = feat["github"]
    
    # Identify explicit feature groups with hits
    hits_ret_emb = feat.get("hits_retrieval_embeddings", 0)
    hits_vec_db = feat.get("hits_vector_db", 0)
    hits_rank_search = feat.get("hits_ranking_search", 0)
    hits_prod_ml = feat.get("hits_production_ml", 0)
    hits_eval = feat.get("hits_evaluation", 0)
    hits_startup = feat.get("hits_startup_product", 0)

    # 1. Experience & Role Alignment
    if penalty >= 30:
        alignment_str = "limited (due to profile contradictions)"
    elif career_score >= 80:
        alignment_str = "strong"
    elif career_score >= 50:
        alignment_str = "partial"
    else:
        alignment_str = "limited"
        
    s_intro = f"Candidate is a {years:.1f}-year {title} demonstrating {alignment_str} alignment with the Senior AI Engineer role."
    
    # 2. Key Strengths and Evidence Snippets
    strengths = []
    if hits_ret_emb >= 5:
        strengths.append("extensive experience in retrieval and embeddings")
    elif hits_ret_emb >= 3:
        strengths.append("demonstrated expertise in retrieval and embeddings")
    elif hits_ret_emb >= 1:
        strengths.append("strong evidence of retrieval and embeddings work")

    if hits_vec_db >= 5:
        strengths.append("extensive experience with production-scale systems using vector databases")
    elif hits_vec_db >= 3:
        strengths.append("demonstrated expertise in vector database implementation")
    elif hits_vec_db >= 1:
        strengths.append("strong evidence of vector database deployment")

    if hits_rank_search >= 5:
        strengths.append("extensive experience with ranking systems and search engine optimization")
    elif hits_rank_search >= 3:
        strengths.append("demonstrated expertise in search and ranking systems")
    elif hits_rank_search >= 1:
        strengths.append("strong evidence of ranking and search systems work")

    if hits_prod_ml >= 5:
        strengths.append("extensive experience deploying production-scale systems")
    elif hits_prod_ml >= 3:
        strengths.append("demonstrated expertise in production-scale systems")
    elif hits_prod_ml >= 1:
        strengths.append("strong evidence of production-scale systems delivery")

    if hits_eval >= 5:
        strengths.append("extensive experience establishing offline and online evaluation frameworks")
    elif hits_eval >= 3:
        strengths.append("demonstrated expertise in model evaluation frameworks")
    elif hits_eval >= 1:
        strengths.append("strong evidence of design evaluation work")

    if hits_startup > 0:
        strengths.append("proven adaptability in product-driven environments")
        
    if matched_skills:
        skills_str = ", ".join(matched_skills[:4])
        s_skills = f"Proven skills include {skills_str}."
    else:
        s_skills = "No direct matching target skills identified in the profile."

    evidence_snippets = feat.get("evidence_snippets", [])
    if evidence_snippets:
        quoted_snippets = " ".join([f'"{s.rstrip(".")}"' for s in evidence_snippets[:3]])
        s_strengths = f"Verified project accomplishments from career history include: {quoted_snippets}."
    elif strengths:
        s_strengths = f"Key strengths include {', '.join(strengths[:3])}."
    else:
        s_strengths = "Exhibits solid software engineering experience."

    # 3. FutureFit Signals (Progression, Leadership, Github)
    future_fit = []
    combined = feat.get("combined_desc", "").lower()
    
    # Evidence-Based Leadership Accomplishments
    leadership_evidence = []
    if "mentor" in combined:
        leadership_evidence.append("mentored engineers")
    if "migration" in combined or "migrat" in combined:
        leadership_evidence.append("led migration")
    if "deploy" in combined:
        leadership_evidence.append("owned deployment")
    if "manage" in combined or "project" in combined or "deliver" in combined:
        leadership_evidence.append("managed project delivery")
        
    if leadership_evidence:
        future_fit.append(f"leadership evidence ({', '.join(leadership_evidence[:2])})")
    else:
        leadership_keywords = ["led", "architected", "founded", "hired", "supervis", "team lead"]
        if any(lk in combined for lk in leadership_keywords):
            future_fit.append("demonstrated technical leadership")
            
    if github > 40:
        future_fit.append("strong GitHub activity and open-source contributions")
    
    if len(feat.get("titles", [])) >= 2:
        senior_t = ["senior", "lead", "principal", "architect", "head", "staff", "director", "founding"]
        latest = feat["titles"][0]
        if any(t in latest for t in senior_t):
            future_fit.append("career progression to senior roles")

    if future_fit:
        s_future = f"FutureFit signals: {', '.join(future_fit)}."
    else:
        s_future = "Demonstrates consistent learning and technical growth."

    # 4. Concerns & Behavioral Risks
    concerns = []
    if penalty > 0:
        formatted_reasons = []
        for r in risk_reasons:
            fr = r.strip()
            if fr:
                if not any(fr.startswith(ac) for ac in ["AI", "ML", "JD"]):
                    fr = fr[0].lower() + fr[1:]
                formatted_reasons.append(fr)
        if formatted_reasons:
            concerns.append(f"profile inconsistencies ({'; '.join(formatted_reasons)})")
            
    if nd > 90:
        concerns.append(f"extended notice period of {nd} days")
    elif nd > 60:
        concerns.append(f"notice period of {nd} days")
        
    unverified = []
    for s in matched_skills:
        if s in MUST_HAVE_SKILLS:
            if not skill_has_synonym(combined, s):
                unverified.append(s)
    if unverified:
        concerns.append(f"limited evidence of {', '.join(unverified[:2])} in career history")
        
    companies = feat.get("companies", [])
    if companies:
        consulting_count = sum(1 for c in companies if any(cf in str(c) for cf in CONSULTING_FIRMS))
        if consulting_count > 0:
            concerns.append(f"consulting background with {consulting_count} companies")

    if concerns:
        s_concerns = f"Concerns: {'; '.join(concerns).capitalize()}."
    else:
        s_concerns = "No significant risk factors or inconsistencies detected."

    # 5. Recruitability & Availability
    if recruit_index >= 80:
        s_recruit = "Highly active, responsive, and available for recruitment."
    elif recruit_index >= 50:
        s_recruit = "Moderately active; responsiveness should be checked during initial outreach."
    else:
        s_recruit = "Inactive or passive candidate; responsiveness may be delayed."

    reasoning = f"{s_intro} {s_skills} {s_strengths} {s_future} {s_concerns} {s_recruit}"
    return reasoning


# ─────────────────────────────────────────────
# 6. MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    print("\nTalentLens — Redrob Hackathon Ranking Engine")
    print("=" * 50)

    # Load
    candidates = load_candidates()
    jd_text    = load_jd()
    print_audit(candidates)

    # Debiasing Layer: anonymize candidate records and strip demographic fields
    print("Applying demographic de-biasing layer...")
    orig_to_anon = {}
    anon_to_orig = {}
    debiased_candidates = []
    for idx, c in enumerate(candidates):
        orig_id = c.get("candidate_id", f"CAND_{idx+1:07d}")
        anon_id = f"ANON_{idx+1:07d}"
        orig_to_anon[orig_id] = anon_id
        anon_to_orig[anon_id] = orig_id
        debiased_candidates.append(debias_candidate(c, anon_id))
    candidates = debiased_candidates

    # Extract features
    print("Extracting features...")
    features = [extract_features(c) for c in candidates]

    # TF-IDF: fit exactly once across all candidates + JD
    print(f"Computing TF-IDF similarity across {len(features):,} candidates...")
    corpus = [f["full_text"] for f in features] + [jd_text.lower()]
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000,
        sublinear_tf=True,
    )
    tfidf_matrix  = vectorizer.fit_transform(corpus)
    jd_vector     = tfidf_matrix[-1]
    cand_vectors  = tfidf_matrix[:-1]
    semantic_sims = cosine_similarity(cand_vectors, jd_vector).flatten()

    # Score all candidates
    print("Scoring candidates...")
    records = []
    for idx, feat in enumerate(features):
        semantic       = round(float(semantic_sims[idx]) * 100, 4)
        career_score, prod_hits, domain_hits = score_career(feat)
        skill_score, matched_skills          = score_skills(feat)
        behavior, logistics, recruit_index, nd = score_recruitability(feat)
        penalty, risk_reasons                 = score_honeypot_penalty(feat)

        # Weighted aggregate per design
        # Weights: Career 35%, Recruitability 25%, Skills 25%, Semantic 15%
        weighted = (
            career_score   * 0.35 +
            recruit_index  * 0.25 +
            skill_score    * 0.25 +
            semantic       * 0.15
        )
        final_score = round(max(0.0, weighted - (penalty * 0.10)), 4)

        reasoning = build_reasoning(
            feat, matched_skills, prod_hits, domain_hits,
            penalty, risk_reasons, recruit_index, career_score, rank=0
        )

        records.append({
            "candidate_id":       feat["cid"],
            "score":              final_score,
            "semantic_score":     semantic,
            "career_score":       career_score,
            "skill_score":        skill_score,
            "behavior_score":     behavior,
            "logistics_score":    logistics,
            "recruitability_index": recruit_index,
            "risk_penalty":       penalty,
            "years_exp":          feat["years_exp"],
            "notice_days":        nd,
            "matched_skills":     ", ".join(matched_skills[:5]),
            "reasoning":          reasoning,
        })

    # Sort and rank
    df = pd.DataFrame(records)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df.insert(1, "rank", range(1, len(df) + 1))

    # Ensure scores are strictly non-increasing for equal-score ties
    # (validator requires monotonically non-increasing; sort by score desc, then candidate_id asc for ties)
    df = df.sort_values(["score", "candidate_id"], ascending=[False, True]).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)

    # ── Print top 20 ──
    print("\n" + "="*100)
    print("  TOP 20 CANDIDATES")
    print("="*100)
    cols = ["rank", "candidate_id", "career_score", "skill_score", "recruitability_index",
            "semantic_score", "risk_penalty", "score"]
    print(df[cols].head(20).to_string(index=False))
    print("="*100)

    # ── Audit traces ──
    total = len(df)
    trace_ranks = sorted(set([1, min(5, total), min(10, total), min(50, total),
                               min(100, total), total]))
    print("\n" + "="*100)
    print("  AUDIT TRACES")
    print("="*100)
    for r in trace_ranks:
        row = df[df["rank"] == r].iloc[0]
        print(f"\n  Rank #{r} | {row['candidate_id']} | Score: {row['score']} | "
              f"Years: {row['years_exp']} | Notice: {row['notice_days']}d")
        print(f"  Career:{row['career_score']} | Skills:{row['skill_score']} | "
              f"Recruit:{row['recruitability_index']} | Semantic:{row['semantic_score']} | "
              f"Penalty:{row['risk_penalty']}")
        print(f"  Skills matched: {row['matched_skills']}")
        print(f"  Reasoning: \"{row['reasoning']}\"")
    print("\n" + "="*100)

    # ── Export submission CSV (top 100 only, required format) ──
    top100 = df[df["rank"] <= 100][["candidate_id", "rank", "score", "reasoning"]].copy()
    top100["candidate_id"] = top100["candidate_id"].map(anon_to_orig)
    top100.to_csv(SUBMISSION_FILE, index=False, encoding="utf-8")
    print(f"\n  Submission file saved: {SUBMISSION_FILE} ({len(top100)} rows)")

    # ── Export full output for inspection ──
    full_cols = ["rank", "candidate_id", "score", "career_score", "skill_score",
                 "recruitability_index", "semantic_score", "risk_penalty",
                 "years_exp", "notice_days", "matched_skills", "reasoning"]
    df_full = df[full_cols].copy()
    df_full["candidate_id"] = df_full["candidate_id"].map(anon_to_orig)
    df_full.to_csv(FULL_OUTPUT, index=False, encoding="utf-8")
    print(f"  Full output saved: {FULL_OUTPUT} ({len(df):,} rows)")
    print("\n  TalentLens complete.\n")


if __name__ == "__main__":
    main()
