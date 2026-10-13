import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

print("Loading cleaned jobs...")
df = pd.read_parquet("jobs_cleaned.parquet")

# Use only 100 jobs for our first test
test_df = df.head(100).copy()

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Creating embeddings...")

embeddings = model.encode(
    test_df["search_text"].tolist(),
    show_progress_bar=True,
    convert_to_numpy=True
)

print("Embedding shape:", embeddings.shape)

# Normalize embeddings for cosine similarity
faiss.normalize_L2(embeddings)

# Create FAISS index
dimension = embeddings.shape[1]

index = faiss.IndexFlatIP(dimension)
index.add(embeddings)

print("Jobs added to FAISS:", index.ntotal)

# Test semantic search
query = "Data Analyst job requiring SQL and Python"

query_embedding = model.encode(
    [query],
    convert_to_numpy=True
)

faiss.normalize_L2(query_embedding)

scores, indices = index.search(query_embedding, 5)

print("\nTop 5 matches:\n")

for rank, idx in enumerate(indices[0], start=1):
    job = test_df.iloc[idx]

    print(f"{rank}. {job['title']}")
    print(f"   Company: {job['company']}")
    print(f"   Location: {job['location']}")
    print(f"   Score: {scores[0][rank-1]:.4f}")
    print(f"   Apply: {job['apply_url']}")
    print()