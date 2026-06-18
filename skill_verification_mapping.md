# Synonym-Aware Group Verification Mapping

This document details the synonym-aware group verification mapping used by the TalentLens Candidate Ranking Engine. It replaces exact string skill matching with conceptual groups to prevent false negatives in candidate experience verification.

---

## 1. Synonym-Aware Group Registry

Candidate skills are classified into three primary technical competency groups. If a candidate declares a skill in one of these groups, their career history is scanned for **any** synonym in that group to verify the experience.

### Group A: Vector Databases
* **Concept**: Database engines and indexing mechanisms optimized for high-dimensional vector search.
* **Registry Terms**:
  - `Pinecone`
  - `Qdrant`
  - `Weaviate`
  - `Milvus`
  - `FAISS`
  - `pgvector`
  - `vector database`
  - `vector databases`
  - `vector search`
  - `vector store`
  - `vector`
  - `HNSW`
  - `IVF`
  - `Elasticsearch`
  - `OpenSearch`

### Group B: Embeddings
* **Concept**: Numerical representation of semantic units and dense retrieval models.
* **Registry Terms**:
  - `embeddings`
  - `BGE`
  - `E5`
  - `Sentence Transformers`
  - `sentence-transformers`
  - `Dense Retrieval`
  - `OpenAI embeddings`
  - `bi-encoder`
  - `cross-encoder`
  - `retrieval`
  - `dense passage`
  - `DPR`
  - `ColBERT`
  - `information retrieval`

### Group C: Ranking
* **Concept**: Algorithms, metrics, and models for scoring retrieved items by relevance.
* **Registry Terms**:
  - `ranking`
  - `ranking systems`
  - `recommender`
  - `LTR` (Learning to Rank)
  - `learning to rank`
  - `Reranking`
  - `rerank`
  - `search engine`
  - `Hybrid Search`
  - `BM25`
  - `TF-IDF`
  - `search`

---

## 2. Ungrouped Core Skills Fallbacks

Skills that do not belong to the three core groups but are required by the job description are verified using direct normalized match and specific fallbacks:

| Skill | Fallbacks / Synonyms |
| :--- | :--- |
| **Python** | `py` |
| **NLP** | `natural language processing` |

---

## 3. Benefits of Synonym-Group Verification

1. **Eliminates False Negatives**: Candidates listing `Pinecone` who describe using `Weaviate` in their projects are successfully verified.
2. **Combats Keyword Stuffing**: Prevents candidates from writing all possible spellings of vector databases or embeddings to bypass simple substring checks.
3. **Calibrates Relevance**: Evaluates candidate capability based on *concept mastery* rather than exact keyword alignment.
