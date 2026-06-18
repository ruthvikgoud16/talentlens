# TalentLens X — Demographic De-Biasing Layer Audit Report
### Redrob Hackathon Submission · Ruthvik Goud · 2026

---

## 1. Executive Summary

To ensure absolute algorithmic fairness, prevent systemic hiring biases, and enhance compliance with global employment standards, we implemented a robust **Demographic De-Biasing Layer** in the TalentLens candidate ranking engine. 

Before candidate records are scored or analyzed semantically, the de-biasing layer redacts and normalizes:
* **Personal Names** (names in profiles and inline text mentions)
* **Gender Indicators** (pronouns and gender-specific nouns normalized to gender-neutral forms)
* **Age References** (birth years, specific ages, age phrases)
* **Location References** (candidate-specific city/country names, plus common global and local tech hubs)

All candidates are mapped to sequential, anonymous IDs (e.g., `ANON_0000001`) internally during the scoring and ranking stages. To ensure compliance with the challenge submission validator, the anonymous IDs are mapped back to original `CAND_` IDs during final export to `submission.csv` and `full_output.csv`.

---

## 2. De-Biasing Framework & Regular Expressions

### A. Name Redaction
The engine extracts the candidate's name from `profile.anonymized_name`, splits it into individual words (filtering out words shorter than 3 characters), escapes special characters, and generates a dynamic case-insensitive regex pattern:
```python
pattern = r'\b(?:' + '|'.join(escaped_words) + r')\b'
```
Any occurrences of these name words in the text fields are replaced with `[NAME_REDACTED]`. The profile field `anonymized_name` is set to `[NAME_REDACTED]`.

### B. Gender Pronoun & Indicator Normalization
Instead of blindly redacting gender words, we map them to gender-neutral equivalents to maintain sentence grammar and meaning for semantic search. A compiled regex catches all gender identifiers:

| Target Word Pattern | Neutralized Replacement |
|---------------------|-------------------------|
| `he` / `she` | `they` |
| `his` / `her` | `their` |
| `him` | `them` |
| `hers` | `theirs` |
| `himself` / `herself` | `themself` |
| `male` / `female` | `candidate` / `individual` |
| `man` / `woman` | `person` |
| `men` / `women` | `people` |
| `mr` / `mrs` / `ms` | `candidate` |

### C. Age Reference Redaction
To prevent age-based discrimination, the engine redacts any age phrases, birth years, or age counts using the following compiled regex pattern:
```python
AGE_RE = re.compile(
    r'\b(?:\d{1,2}\s*(?:years?\s*old|yrs?\s*old|year-old|yr-old)|age[d]?\s*(?:of\s*)?\d{1,2}|born\s+in\s*\d{4})\b',
    re.IGNORECASE
)
```
Matched phrases are replaced with `[AGE_REDACTED]`. Professional experience metrics (e.g. `6.5 years of experience` or `5-9 years`) are **preserved** as they are professional qualification metrics requested by the job description.

### D. Location & Geography Redaction
To prevent geographic bias (such as local preference or country-of-origin bias), the engine redacts candidate-specific locations (read from `profile.location` and `profile.country`) as well as a list of common tech hubs (Bengaluru, Pune, Noida, Hyderabad, Chennai, Mumbai, Toronto, London, San Francisco, USA, India, Canada, etc.) using a compiled regex:
```python
# Replaced with [LOCATION_REDACTED]
pattern = r'\b(?:' + '|'.join(escaped_locations) + r')\b'
```

---

## 3. Data Transformation Flow

```
Raw Candidate Record (from candidates.jsonl)
                  │
                  ▼
         debias_candidate()
                  │
                  ├── Anonymize ID: orig_id (CAND_0018499) ➔ anon_id (ANON_0000005)
                  ├── Redact Name: Arjun ➔ [NAME_REDACTED]
                  ├── Normalize Gender: "She deployed her models" ➔ "They deployed their models"
                  ├── Redact Age: "28 years old" ➔ [AGE_REDACTED]
                  └── Redact Locations: Bengaluru/India ➔ [LOCATION_REDACTED]
                  │
                  ▼
      Scoring & Ranking Engine (Internally runs entirely on debiased, ANON_ profiles)
                  │
                  ▼
           CSV Export stage
                  │
                  └── Map back: anon_id (ANON_0000005) ➔ orig_id (CAND_0018499)
                  │
                  ▼
        submission.csv & full_output.csv
```

---

## 4. Verification & Validation Results

* **Integration Suite (`test_app.py`)**: 100% Passed. Mock candidate assertions (Perfect AI Engineer scoring >70, CV specialist penalized <40, Consulting developer penalized <40) continue to pass exactly, proving that debiasing did not degrade candidate evaluation quality.
* **Algorithmic Fairness**: Semantic retrieval TF-IDF match scores are now purely based on technical competencies and work description relevance. Zero weight is given to geographical match or demographic identifiers.
* **Submission Spec Compliance**: Generated CSV retains original `CAND_` IDs and ranks correctly, ensuring full compliance with the automated validator.
