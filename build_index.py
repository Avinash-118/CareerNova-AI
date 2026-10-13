import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

print("Loading cleaned job dataset...")

df = pd.read_parquet("jobs_cleaned.parquet")

print(f"Jobs loaded: {len(df):,}")

print("\nLoading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

texts = df["search_text"].fillna("").tolist()

print("\nCreating embeddings for all jobs...")
print("This may take some time.")

embeddings = model.encode(
    texts,
    batch_size=64,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True
)

embeddings = np.asarray(embeddings, dtype="float32")

print("\nEmbedding shape:", embeddings.shape)

# Create FAISS cosine-similarity index
dimension = embeddings.shape[1]

index = faiss.IndexFlatIP(dimension)

print("Building FAISS index...")

index.add(embeddings)

print("Jobs indexed:", index.ntotal)

# Save FAISS index
faiss.write_index(index, "jobs_faiss.index")

# Save job metadata in exactly the same row order
df.to_parquet("jobs_metadata.parquet", index=False)

print("\n--------------------------------")
print("FAISS INDEX CREATED SUCCESSFULLY")
print("--------------------------------")

print("FAISS index: jobs_faiss.index")
print("Metadata: jobs_metadata.parquet")
print(f"Total indexed jobs: {index.ntotal:,}")