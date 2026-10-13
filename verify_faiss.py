
from pathlib import Path

import faiss
import pandas as pd
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent

INDEX_PATH = BASE_DIR / "jobs_faiss.index"
METADATA_PATH = BASE_DIR / "jobs_metadata.parquet"

print("Checking FAISS files...")

if not INDEX_PATH.exists():
    raise FileNotFoundError(f"Missing: {INDEX_PATH}")

if not METADATA_PATH.exists():
    raise FileNotFoundError(f"Missing: {METADATA_PATH}")

index = faiss.read_index(str(INDEX_PATH))
jobs = pd.read_parquet(METADATA_PATH)

print("FAISS vectors:", index.ntotal)
print("Metadata records:", len(jobs))
print("Vector dimensions:", index.d)
print("Available columns:", jobs.columns.tolist())

if index.ntotal != len(jobs):
    raise ValueError(
        "FAISS vector count does not match metadata rows."
    )

model = SentenceTransformer("all-MiniLM-L6-v2")

if model.get_sentence_embedding_dimension() != index.d:
    raise ValueError("Embedding dimensions do not match.")

print("Testing semantic search...")

query = "Data Analyst Python SQL Power BI"
vector = model.encode(
    [query],
    convert_to_numpy=True,
    normalize_embeddings=True
).astype("float32")

distances, indices = index.search(vector, 5)

for rank, (idx, score) in enumerate(
    zip(indices[0], distances[0]), start=1
):
    if idx < 0:
        continue

    job = jobs.iloc[int(idx)]

    print(f"\nResult {rank}")
    print("Title:", job.get("title", "Unknown"))
    print("Company:", job.get("company", "Unknown"))
    print("Location:", job.get("location", "Unknown"))
    print("FAISS score:", round(float(score), 4))

print("\nFAISS verification completed.")
