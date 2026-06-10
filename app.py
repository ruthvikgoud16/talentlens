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
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, date

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

# JD explicitly says these are negative signals
CONSULTING_FIRMS = ["tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini"]
NON_TECH_ROLES   = ["marketing", "sales", "hr", "content writer", "operations manager",
                    "accountant", "recruiter", "business analyst", "customer support"]
NON_DOMAIN_SKILLS = ["computer vision", "speech recognition", "robotics", "image classification",
                     "tts", "object detection", "gan", "ocr"]

PRODUCTION_KW = [
    "deployed", "production", "scaled", "architected", "pipeline", "infrastructure",
    "latency", "optimized", "optimised", "real-time", "serving", "monitoring",
    "mlops", "a/b test", "offline eval", "online eval", "index refresh",
]
DOMAIN_KW = [
    "recommendation", "retrieval", "search", "ranking", "recommender",
    "vector search", "rerank", "embeddings", "nlp", "transformer", "llm",
    "fine-tun", "language model", "hybrid search", "bm25", "dense retrieval",
    "ndcg", "mrr", "map", "precision", "recall",
]

MAX_SKILL_WEIGHT = sum(ALL_TARGET_SKILLS.values())


def days_since(date_str):
    """Returns days between a date string and today. Returns 999 on error."""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (TODAY - d).days
    except Exception:
        return 999


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
                skills_with_meta.append({"name": name, "prof": prof, "dur": dur, "end": end})
        elif isinstance(s, str):
            skills_list.append(s.lower().strip())
            skills_with_meta.append({"name": s.lower().strip(), "prof": "beginner", "dur": 0, "end": 0})

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

    # ── Signals (with -1 handling) ──
    def safe(val, default):
        try:
            v = float(val)
            return default if v < 0 else v
        except (ValueError, TypeError):
            return default

    last_active_days = days_since(str(signals.get("last_active_date", "")))

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
        "full_text":      f"{headline} {summary} {current_title} {' '.join(skills_list)} {' '.join(titles)} {combined_desc}",
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
    }
    return feat


# ─────────────────────────────────────────────
# 4. SCORING ENGINES
# ─────────────────────────────────────────────

def score_career(feat):
    """
    Career Evidence & Trajectory (30% weight)
    
    JD signals:
    - Wants 5-9 years, product companies preferred
    - Explicitly penalizes: consulting-only backgrounds, non-tech careers
    - Rewards: production deployments, domain relevance (retrieval/search/ranking)
    - Penalizes: pure research without production, recent LangChain-only projects
    """
    years    = feat["years_exp"]
    titles   = feat["titles"]
    companies= feat["companies"]
    combined = feat["combined_desc"]

    # ── Experience scale: JD wants 5-9 years ──
    # Sweet spot 5-9 years gets full credit; outside range gets partial
    if 5 <= years <= 9:
        exp_scale = 1.0
    elif years > 9:
        exp_scale = 0.85   # over-experienced, may not fit startup stage
    elif 3 <= years < 5:
        exp_scale = 0.75
    elif years > 0:
        exp_scale = 0.40
    else:
        exp_scale = 0.20

    # ── Trajectory: did they progress in tech? ──
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
        is_non_tech_all= all(any(nt in t for nt in non_tech) for t in titles) if titles else False

        if is_tech_start and is_senior_now:
            trajectory_mult = 1.25
        elif is_non_tech_now:
            trajectory_mult = 0.30
        elif is_non_tech_all:
            trajectory_mult = 0.20

    # ── Production keyword hits ──
    prod_hits   = sum(1 for kw in PRODUCTION_KW if kw in combined)
    domain_hits = sum(1 for kw in DOMAIN_KW if kw in combined)

    # ── Consulting firm penalty (JD is explicit: consulting-only is a disqualifier) ──
    consulting_penalty = 0.0
    if companies:
        all_consulting = all(any(cf in c for cf in CONSULTING_FIRMS) for c in companies if c)
        if all_consulting and companies:
            consulting_penalty = 30.0  # heavy but not total — if they have domain evidence it can overcome

    base = min((prod_hits * 7.0) + (domain_hits * 8.0), 100.0)
    raw  = base * exp_scale * trajectory_mult
    final = max(0.0, raw - consulting_penalty)
    return round(min(final, 100.0), 2), prod_hits, domain_hits


def score_skills(feat):
    """
    Skill Relevance (20% weight)
    
    Weights skills from JD must-haves higher than nice-to-haves.
    Uses proficiency and endorsements as quality signal.
    Adds bonus for verified assessment scores.
    Penalizes non-domain skills (CV/speech/robotics per JD).
    """
    skills_meta = feat["skills_meta"]
    assessments = feat["assessments"]
    skills_list = feat["skills_list"]

    earned = 0.0
    matched = []

    for skill_name, weight in ALL_TARGET_SKILLS.items():
        match = next((s for s in skills_meta if skill_name in s["name"]), None)
        if match:
            matched.append(skill_name)
            # Proficiency multiplier
            prof_mult = {"advanced": 1.0, "intermediate": 0.75, "beginner": 0.45}.get(match["prof"], 0.6)
            # Duration bonus (>12 months = real experience)
            dur_mult = 1.1 if match["dur"] >= 12 else 0.9
            earned += weight * prof_mult * dur_mult

    base = (earned / MAX_SKILL_WEIGHT) * 100.0

    # Assessment score bonus (verified skills from platform tests)
    if assessments:
        avg_assess = sum(assessments.values()) / len(assessments)
        # Only bonus if the assessed skills are relevant
        relevant_assess = {k: v for k, v in assessments.items()
                          if any(t in k.lower() for t in list(ALL_TARGET_SKILLS.keys()))}
        if relevant_assess:
            bonus = (sum(relevant_assess.values()) / len(relevant_assess) / 100.0) * 8.0
        else:
            bonus = 0.0
    else:
        bonus = 0.0

    # Non-domain skill penalty: JD says CV/speech/robotics people are wrong fit
    non_domain_penalty = 0.0
    non_domain_count = sum(1 for nd in NON_DOMAIN_SKILLS
                          if any(nd in s for s in skills_list))
    relevant_count = len(matched)
    if non_domain_count > 0 and relevant_count == 0:
        non_domain_penalty = min(non_domain_count * 5.0, 20.0)

    final = min(base + bonus, 100.0) - non_domain_penalty
    return round(max(0.0, final), 2), matched


def score_recruitability(feat):
    """
    Recruitability Index (35% weight)
    
    JD is explicit: a perfect-on-paper candidate who hasn't logged in for 6 months
    and has low response rate is "not actually available."
    Notice period: JD says sub-30 days preferred, can buy out up to 30 days.
    """
    # Recency penalty: if inactive for >90 days, candidate may not be available
    if feat["last_active_days"] <= 30:
        recency_mult = 1.0
    elif feat["last_active_days"] <= 60:
        recency_mult = 0.90
    elif feat["last_active_days"] <= 90:
        recency_mult = 0.75
    elif feat["last_active_days"] <= 180:
        recency_mult = 0.55
    else:
        recency_mult = 0.30   # inactive > 6 months = very unlikely to convert

    # Response speed: lower hours = more responsive
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
        feat["resp_rate"]   * 0.25 +
        feat["completion_rate"] * 0.20 +
        open_flag           * 0.20 +
        github              * 0.10 +
        profile_c           * 0.10 +
        resp_time_score     * 0.10 +
        verified            * 0.05
    ) * 100.0

    # Notice period (JD: sub-30 preferred, up to 30 buyable, 30+ bar gets higher)
    nd = feat["notice_days"]
    if nd <= 15:
        notice_score = 1.00
    elif nd <= 30:
        notice_score = 0.90
    elif nd <= 60:
        notice_score = 0.70
    elif nd <= 90:
        notice_score = 0.45
    elif nd <= 120:
        notice_score = 0.25
    else:
        notice_score = 0.10

    relocate_score = 1.0 if feat["relocate"] else 0.65
    # JD: Pune/Noida preferred; hybrid fine; purely onsite preference is minor minus
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
    Contradiction / Honeypot Detection
    
    JD warning: dataset has ~80 honeypots with impossible profiles.
    Also penalizes profiles where claims contradict evidence.
    """
    penalty = 0.0
    reasons = []
    years   = feat["years_exp"]
    career  = feat["career_count"]
    combined= feat["combined_desc"]
    headline= feat["headline"]
    summary = feat["summary"]

    # Honeypot: claimed years vs career history impossible
    if career == 0 and years > 3:
        penalty += 50.0
        reasons.append(f"claims {years:.0f} yrs experience but zero career entries")

    if career == 1 and years > 15:
        penalty += 35.0
        reasons.append(f"claims {years:.0f} yrs but only 1 career entry")

    # AI headline claim with zero technical evidence
    ai_claim   = any(t in headline for t in ["ai", "ml", "machine learning", "nlp", "deep learning", "data scientist", "researcher"])
    ai_evidence= any(t in combined for t in ["model", "train", "deploy", "embedding", "vector", "nlp", "retrieval", "pipeline"])
    if ai_claim and not ai_evidence and career > 0:
        penalty += 30.0
        reasons.append("AI/ML headline not backed by any career description evidence")

    # Entirely non-technical career with AI keyword skills
    non_tech_all = all(any(nt in t for nt in NON_TECH_ROLES) for t in feat["titles"]) if feat["titles"] else False
    skills_have_ai = any(t in " ".join(feat["skills_list"]) for t in ["nlp", "embeddings", "pytorch", "llm", "transformer"])
    if non_tech_all and skills_have_ai:
        penalty += 20.0
        reasons.append("non-technical career history but AI skills listed — likely keyword stuffing")

    return round(min(penalty, 100.0), 2), reasons


# ─────────────────────────────────────────────
# 5. RECRUITER REASONING
# ─────────────────────────────────────────────

def build_reasoning(feat, matched_skills, prod_hits, domain_hits,
                    penalty, risk_reasons, recruit_index, career_score, rank):
    years   = feat["years_exp"]
    title   = feat["current_title"].title() if feat["current_title"] else "unknown role"
    nd      = feat["notice_days"]
    skills3 = ", ".join(matched_skills[:3]) if matched_skills else None

    # Sentence 1: career/skill fit
    if prod_hits >= 2 and domain_hits >= 2 and skills3:
        s1 = (f"{years:.0f}-year {title} with production evidence in retrieval/ranking systems "
              f"and verified skills in {skills3} — strong JD alignment.")
    elif (prod_hits >= 1 or domain_hits >= 1) and skills3:
        s1 = (f"{years:.0f}-year {title} with partial alignment to JD — "
              f"some {skills3} exposure but limited production retrieval/ranking evidence.")
    elif skills3:
        s1 = (f"{years:.0f}-year {title} with matching skills ({skills3}) "
              f"but no clear production retrieval or ranking system history.")
    elif risk_reasons:
        s1 = (f"{years:.0f}-year {title} — profile raises concerns: {risk_reasons[0].lower()}.")
    else:
        s1 = (f"{years:.0f}-year {title} with limited alignment to senior AI engineer requirements "
              f"in retrieval, search, or ranking.")

    # Sentence 2: logistics or concern
    if penalty >= 30:
        concern = risk_reasons[0] if risk_reasons else "profile inconsistency detected"
        s2 = f"Flag: {concern.capitalize()}."
    elif nd > 90:
        s2 = (f"Notice period of {nd} days will slow hiring velocity; "
              f"recruitability score {recruit_index:.0f}/100.")
    elif recruit_index >= 72:
        s2 = f"High recruitability ({recruit_index:.0f}/100) — active, responsive, and available."
    elif recruit_index >= 50:
        s2 = f"Moderate recruitability ({recruit_index:.0f}/100) — some availability concerns."
    else:
        s2 = f"Low recruitability ({recruit_index:.0f}/100) — inactive or slow to respond."

    return f"{s1} {s2}"


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
        # Weights: Career 30%, Recruitability 35%, Skills 20%, Semantic 15%
        weighted = (
            career_score   * 0.30 +
            recruit_index  * 0.35 +
            skill_score    * 0.20 +
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
    top100.to_csv(SUBMISSION_FILE, index=False, encoding="utf-8")
    print(f"\n  Submission file saved: {SUBMISSION_FILE} ({len(top100)} rows)")

    # ── Export full output for inspection ──
    full_cols = ["rank", "candidate_id", "score", "career_score", "skill_score",
                 "recruitability_index", "semantic_score", "risk_penalty",
                 "years_exp", "notice_days", "matched_skills", "reasoning"]
    df[full_cols].to_csv(FULL_OUTPUT, index=False, encoding="utf-8")
    print(f"  Full output saved: {FULL_OUTPUT} ({len(df):,} rows)")
    print("\n  TalentLens complete.\n")


if __name__ == "__main__":
    main()
