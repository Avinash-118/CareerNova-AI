
import faiss
import pandas as pd
from sentence_transformers import SentenceTransformer

print("Loading FAISS index...")
index = faiss.read_index("jobs_faiss.index")

print("Loading job metadata...")
jobs = pd.read_parquet("jobs_metadata.parquet")

assert index.ntotal == len(jobs), "Index and metadata do not match!"

print("Loading AI embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

query = "Entry-level Data Analyst jobs requiring SQL and Python"

print("\nSearching for:", query)

query_vector = model.encode(
    [query],
    convert_to_numpy=True,
    normalize_embeddings=True
)

scores, indices = index.search(query_vector, 10)

print("\nTOP 10 MATCHING JOBS")
print("-" * 50)

for rank, (idx, score) in enumerate(
    zip(indices[0], scores[0]), start=1
):
    if idx < 0:
        continue

    job = jobs.iloc[idx]

    print(f"\n{rank}. {job['title']}")
    print(f"Company: {job['company']}")
    print(f"Location: {job['location']}")
    print(f"Similarity: {score:.2%}")
    print(f"Apply: {job['apply_url']}")

print("\nSearch completed!")
