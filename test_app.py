import sys
import os

# Append the directory containing app.py to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import extract_features, score_career, score_skills, score_recruitability, score_honeypot_penalty, build_reasoning

# Mock Candidates to Test the New System
mock_candidates = [
    # 1. Qualified AI Engineer (Product background, 6 years, has must-haves with alternate spelling, highly active)
    {
        "candidate_id": "CAND_PERFECT_AI",
        "profile": {
            "headline": "Senior Machine Learning Engineer | Founding AI Team",
            "summary": "Building large-scale dense retrieval and vector search pipelines. Focused on embedding retrieval.",
            "current_title": "Senior AI Engineer",
            "years_of_experience": 6.5
        },
        "skills": [
            {"name": "Python", "proficiency": "advanced", "duration_months": 48, "endorsements": 12},
            {"name": "Sentence Transformers", "proficiency": "advanced", "duration_months": 24, "endorsements": 8},
            {"name": "Vector Databases", "proficiency": "intermediate", "duration_months": 18, "endorsements": 4},
            {"name": "Retrieval", "proficiency": "advanced", "duration_months": 36, "endorsements": 10},
            {"name": "LLMs", "proficiency": "advanced", "duration_months": 15, "endorsements": 9}
        ],
        "career_history": [
            {"title": "Senior AI Engineer", "company": "Tech Product Corp", "description": "Deployed semantic retrieval and embedding search infrastructure using Sentence Transformers. Scaled vector databases to production. Optimised latency."},
            {"title": "Software Developer", "company": "SaaS Platform Inc", "description": "Developed indexing workflows and API routing."}
        ],
        "redrob_signals": {
            "recruiter_response_rate": 0.95,
            "interview_completion_rate": 0.90,
            "open_to_work_flag": True,
            "github_activity_score": 85,
            "profile_completeness_score": 95,
            "offer_acceptance_rate": 0.85,
            "notice_period_days": 15,
            "willing_to_relocate": True,
            "preferred_work_mode": "hybrid",
            "last_active_date": "2026-06-10",
            "verified_email": True,
            "verified_phone": True,
            "avg_response_time_hours": 4.0
        }
    },
    
    # 2. Computer Vision Engineer (Wrong fit, should be heavily penalized despite having "python" or "embeddings")
    {
        "candidate_id": "CAND_WRONG_CV",
        "profile": {
            "headline": "Computer Vision Researcher & Engineer",
            "summary": "Expert in object detection, GANs, and image classification.",
            "current_title": "Computer Vision Specialist",
            "years_of_experience": 6.0
        },
        "skills": [
            {"name": "Python", "proficiency": "advanced", "duration_months": 60, "endorsements": 20},
            {"name": "Computer Vision", "proficiency": "advanced", "duration_months": 48, "endorsements": 15},
            {"name": "Object Detection", "proficiency": "advanced", "duration_months": 36, "endorsements": 10},
            {"name": "Embeddings", "proficiency": "intermediate", "duration_months": 12, "endorsements": 2}
        ],
        "career_history": [
            {"title": "Computer Vision Engineer", "company": "RoboCam Tech", "description": "Developed real-time object detection models. Deployed image segmentation pipelines."}
        ],
        "redrob_signals": {
            "recruiter_response_rate": 0.80,
            "open_to_work_flag": True,
            "last_active_date": "2026-06-15",
            "notice_period_days": 30
        }
    },

    # 3. Consulting-only Candidate (disqualified by JD)
    {
        "candidate_id": "CAND_CONSULTING",
        "profile": {
            "headline": "AI Engineer",
            "summary": "Developer specializing in Python and semantic search.",
            "current_title": "Senior Consultant",
            "years_of_experience": 7.0
        },
        "skills": [
            {"name": "Python", "proficiency": "advanced", "duration_months": 60},
            {"name": "Search", "proficiency": "intermediate", "duration_months": 24}
        ],
        "career_history": [
            {"title": "Senior Analyst", "company": "TCS (Tata Consultancy Services)", "description": "Consulted on Python workflows for retail clients."},
            {"title": "Software Engineer", "company": "Infosys", "description": "Maintained database servers and Java applications."}
        ],
        "redrob_signals": {
            "recruiter_response_rate": 0.75,
            "open_to_work_flag": True,
            "last_active_date": "2026-06-15",
            "notice_period_days": 30
        }
    },
    
    # 4. Junior Candidate leaking title
    {
        "candidate_id": "CAND_JUNIOR_LEAK",
        "profile": {
            "headline": "Junior ML Engineer",
            "summary": "Building embeddings-based retrieval systems.",
            "current_title": "Junior Machine Learning Engineer",
            "years_of_experience": 5.0
        },
        "skills": [
            {"name": "Python", "proficiency": "advanced", "duration_months": 24},
            {"name": "Retrieval", "proficiency": "intermediate", "duration_months": 12}
        ],
        "career_history": [
            {"title": "Junior ML Engineer", "company": "Product Corp", "description": "Developed search retrieval workflows."}
        ],
        "redrob_signals": {
            "recruiter_response_rate": 0.85,
            "open_to_work_flag": True,
            "last_active_date": "2026-06-15",
            "notice_period_days": 30
        }
    }
]

def run_tests():
    print("=" * 60)
    print("           TALENTLENS ENGINE INTEGRATION TEST")
    print("=" * 60)
    
    for cand in mock_candidates:
        print(f"\nAnalyzing Candidate: {cand['candidate_id']}")
        feat = extract_features(cand)
        
        # Test Career Scoring
        career_score, prod_hits, domain_hits = score_career(feat)
        print(f"  Career Score     : {career_score} (Prod hits: {prod_hits}, Domain hits: {domain_hits})")
        
        # Test Skill Scoring (with normalization checks)
        skill_score, matched_skills = score_skills(feat)
        print(f"  Skill Score      : {skill_score} (Matched: {matched_skills})")
        
        # Test Recruitability
        behavior, logistics, recruit_index, nd = score_recruitability(feat)
        print(f"  Recruitability   : {recruit_index} (Notice: {nd}d, Behav: {behavior}, Logist: {logistics})")
        
        # Test Honeypots
        penalty, risk_reasons = score_honeypot_penalty(feat)
        if penalty > 0:
            print(f"  Honeypot Penalty : -{penalty} (Reasons: {risk_reasons})")
            
        # Overall weighted score mockup (Weights: Career 35%, Recruitability 25%, Skills 25%, Semantic 15%)
        # For tests, let's assume a generic semantic match score of 40% (since we are not running TF-IDF over the 100k corpus)
        mock_semantic = 40.0
        weighted = (
            career_score   * 0.35 +
            recruit_index  * 0.25 +
            skill_score    * 0.25 +
            mock_semantic  * 0.15
        )
        final_score = round(max(0.0, weighted - (penalty * 0.10)), 4)
        print(f"  --> Final Score  : {final_score}")
        
        # Test Reasoning
        reasoning = build_reasoning(
            feat, matched_skills, prod_hits, domain_hits,
            penalty, risk_reasons, recruit_index, career_score, rank=0
        )
        print(f"  --> Reasoning    : {reasoning}")
        
        # Check Assertions
        if cand['candidate_id'] == "CAND_PERFECT_AI":
            # Must score high (typically > 75)
            assert final_score > 70.0, f"Perfect AI Engineer should rank high! Score: {final_score}"
            # Spelling normalization verified
            assert "sentence-transformers" in matched_skills, "Spelling normalization failed for sentence-transformers!"
            assert "llm" in matched_skills, "Spelling normalization failed for LLMs!"
            print("  [PASS] Perfect AI candidate behaves correctly.")
            
        elif cand['candidate_id'] == "CAND_WRONG_CV":
            # Must score low (specifically penalized for Computer Vision title and skills)
            assert final_score < 40.0, f"Computer Vision engineer should be heavily penalized! Score: {final_score}"
            print("  [PASS] CV penalty verified. Candidate filtered out successfully.")
            
        elif cand['candidate_id'] == "CAND_CONSULTING":
            # Must be penalized for 100% consulting ratio
            assert career_score < 40.0, f"Consulting-only candidate should have very low career score! Score: {career_score}"
            print("  [PASS] Consulting ratio-based penalty verified.")
            
        elif cand['candidate_id'] == "CAND_JUNIOR_LEAK":
            # Must score low due to Junior Title penalty
            assert career_score < 40.0, f"Junior Candidate should have low career score! Score: {career_score}"
            print("  [PASS] Junior Title penalty verified.")

    print("\n" + "=" * 60)
    print("  ALL SYSTEM DIAGNOSTIC TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
