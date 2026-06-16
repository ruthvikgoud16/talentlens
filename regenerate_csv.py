import csv
import re

# Read and parse the old CSV
rows = []
with open("submission.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        if row:
            rows.append(row)

MUST_HAVE_SKILLS = {"embeddings", "retrieval", "ranking", "vector", "sentence-transformers", "faiss", "milvus", "qdrant", "weaviate", "pinecone", "opensearch", "elasticsearch", "python", "nlp", "search"}

updated_candidates = []

for row in rows:
    cid, rank, old_score, reasoning = row
    
    # Use regex to extract details from the reasoning text
    years_match = re.search(r"(\d+)-year", reasoning)
    years = float(years_match.group(1)) if years_match else 5.0
    
    title_match = re.search(r"year\s+(.*?)\s+with", reasoning)
    title = title_match.group(1) if title_match else "AI Engineer"
    
    skills_match = re.search(r"verified skills in\s+(.*?)\s+—", reasoning)
    skills_str = skills_match.group(1) if skills_match else ""
    skills = [s.strip() for s in skills_str.split(",") if s.strip()]
    
    recruit_match = re.search(r"recruitability\s*\((\d+)", reasoning)
    recruit_index = float(recruit_match.group(1)) if recruit_match else 70.0
    
    # Determine alignment
    alignment = "strong" if "strong JD alignment" in reasoning else "partial" if "partial alignment" in reasoning else "limited"
    
    # ── 1. Re-calculate Career Score ──
    if alignment == "strong":
        base_career = 90.0
    elif alignment == "partial":
        base_career = 70.0
    else:
        base_career = 45.0
        
    if 5 <= years <= 9:
        exp_scale = 1.0
    elif years > 9:
        exp_scale = 0.85
    elif 3 <= years < 5:
        exp_scale = 0.75
    else:
        exp_scale = 0.40
        
    career_score = base_career * exp_scale
    
    # Apply non-domain penalty if they have CV/Speech in their title
    non_domain_titles = ["computer vision", "speech", "robotics", "cv", "vision"]
    if any(t in title.lower() for t in non_domain_titles):
        career_score = max(0.0, career_score - 45.0)

    # ── 2. Re-calculate Skill Score ──
    earned = 0.0
    for s in skills:
        if s.lower() in MUST_HAVE_SKILLS:
            earned += 3.0
        else:
            earned += 1.5
            
    # Apply proficiency factor (approximate average of intermediate/advanced)
    earned *= 0.85
    
    SKILL_CEILING_WEIGHT = 13.0
    skill_score = min((earned / SKILL_CEILING_WEIGHT) * 100.0, 100.0)
    
    # ── 3. Re-calculate Semantic Score ──
    if alignment == "strong":
        semantic_score = 48.0
    elif alignment == "partial":
        semantic_score = 35.0
    else:
        semantic_score = 22.0
        
    # ── 4. Final Weighted Score ──
    # Weights: Career 35%, Recruitability 25%, Skills 25%, Semantic 15%
    weighted = (
        career_score   * 0.35 +
        recruit_index  * 0.25 +
        skill_score    * 0.25 +
        semantic_score * 0.15
    )
    final_score = round(weighted, 4)
    
    # ── 5. Re-build Recruiter Reasoning ──
    skills3 = ", ".join(skills[:3]) if skills else "relevant skills"
    s1 = f"{years:.0f}-year {title.strip()} with production evidence in retrieval/ranking systems and verified skills in {skills3} — {alignment} JD alignment."
    
    if recruit_index >= 72:
        s2 = f"High recruitability ({recruit_index:.0f}/100) — active, responsive, and available."
    elif recruit_index >= 50:
        s2 = f"Moderate recruitability ({recruit_index:.0f}/100) — some availability concerns."
    else:
        s2 = f"Low recruitability ({recruit_index:.0f}/100) — inactive or slow to respond."
        
    updated_reasoning = f"{s1} {s2}"
    
    updated_candidates.append({
        "candidate_id": cid,
        "score": final_score,
        "reasoning": updated_reasoning
    })

# Sort by score desc, then candidate_id asc for ties
updated_candidates = sorted(updated_candidates, key=lambda x: (-x["score"], x["candidate_id"]))

# Write back to submission.csv
with open("submission.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["candidate_id", "rank", "score", "reasoning"])
    for idx, cand in enumerate(updated_candidates):
        writer.writerow([
            cand["candidate_id"],
            idx + 1,
            cand["score"],
            cand["reasoning"]
        ])

print(f"Successfully regenerated submission.csv with new scoring algorithm! Updated {len(updated_candidates)} ranks.")
