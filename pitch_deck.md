# TalentLens Pitch Deck — Redrob Hackathon 2026

An explainable, de-biased, multi-signal candidate discovery and ranking platform matching 100,000 profiles in under 3 minutes locally.

## Slides Overview

### 1. Title & Vision
- **TalentLens**: Explainable Multi-Signal Candidate Discovery & Ranking
- **Built by**: Ruthvik Goud (Solo Entry)
- **Core Values**: Demographic de-biasing, fast local CPU evaluation (~3m), deterministic trace, anti-gaming checker.

### 2. The Problem
- **Fragile ATS systems**: Mismatches on synonyms, keyword-stuffed resumes, impossible timeline claims, and unconscious demography biases.

### 3. The Solution
- **TalentLens Discovery Engine**: Pronoun neutralization, name redacting, and multi-signal scoring (Career, Skills, Availability, Semantics) to generate clear reasons.

### 4. 9-Module AI Pipeline
- **Modular Pipeline**: NLP parser, Skill NER, Dense Retrieval (1024d HNSW index), Truth Engine verification, FutureFit Career Trajectory, Recruiter Dashboard, SVG charts.

### 5. Demographic De-Biasing
- **De-Biased Ingestion**: Pronouns mapped to they/their; location and names automatically redacted.

### 6. Explicit Skill Relevance
- **Normalizer**: Removes hyphens/spacing; scales relevance dynamically on duration and proficiency up to a core ceiling weight.

### 7. Career Evidence & Trajectory
- **Domain Verification**: Proportional penalties for consulting histories, core CV/Speech/Robotics track locks, and production retrieval weighting.

### 8. Honeypot Contradiction Audit
- **Anti-Gaming checks**: Cross-references claim seniority against timeline lengths; reductions applied as multiplier bounds to preserve explainability.

### 9. Candidate Filtering Funnel
- **System Throughput**: Ingestion of 100K ➔ 1K semantic candidates (TF-IDF similarity) ➔ 100 shortlisted ➔ 10 final finalists.

### 10. Recruiter Workspace UI
- **Stunning Interfaces**: Landing page, live stepper overlay, radar competency charts, detail expansions.

### 11. Verification & Compliance
- **Test suite (test_app.py)**: Assertion checks on perfect AI candidates, CV specialists, and consulting developers.

### 12. Summary & Impact
- **Ready for scale**: Completely offline local inference, 100% auditable results, de-biased evaluation.
