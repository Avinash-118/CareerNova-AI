
from pathlib import Path
import threading

import faiss
import pandas as pd
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent

INDEX_PATH = BASE_DIR / "jobs_faiss.index"
METADATA_PATH = BASE_DIR / "jobs_metadata.parquet"

_lock = threading.Lock()
_index = None
_jobs = None
_model = None


def load_search_engine():
    global _index, _jobs, _model

    if _index is not None:
        return _index, _jobs, _model

    with _lock:
        if _index is None:
            index = faiss.read_index(str(INDEX_PATH))
            jobs = pd.read_parquet(METADATA_PATH)
            model = SentenceTransformer("all-MiniLM-L6-v2")

            if index.ntotal != len(jobs):
                raise ValueError(
                    "FAISS index and metadata counts do not match"
                )

            if index.d != model.get_sentence_embedding_dimension():
                raise ValueError("Embedding dimension mismatch")

            _index, _jobs, _model = index, jobs, model

    return _index, _jobs, _model


def clean_value(value):
    if value is None:
        return None

    if isinstance(value, (list, dict)):
        return value

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    return value


def semantic_search(query: str, limit: int = 20):
    index, jobs, model = load_search_engine()

    vector = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    distances, indices = index.search(
        vector, min(limit, index.ntotal)
    )

    results = []

    for rank, (idx, score) in enumerate(
        zip(indices[0], distances[0]), start=1
    ):
        if idx < 0:
            continue

        job = jobs.iloc[int(idx)]

        record = {
            col: clean_value(job[col])
            for col in jobs.columns
        }

        record["rank"] = rank
        record["faiss_score"] = float(score)

        results.append(record)

    return results
