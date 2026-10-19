
import os
from pathlib import Path
import threading

import faiss
import pandas as pd

BASE_DIR = Path(os.getenv('JOB_DATA_DIR',str(Path(__file__).resolve().parent)))

INDEX_PATH = BASE_DIR / "jobs_faiss.index"
METADATA_PATH = BASE_DIR / "jobs_metadata.parquet"

_lock = threading.Lock()
_index = None
_jobs = None
_model = None
_model_lock = threading.Lock()


def get_embedding_model(local_only=False):
    """Share the model with website help without loading the job index."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=local_only)
    return _model


def load_search_engine():
    global _index, _jobs, _model

    if _index is not None:
        return _index, _jobs, _model

    with _lock:
        if _index is None:
            if not INDEX_PATH.is_file() or not METADATA_PATH.is_file():
                from fastapi import HTTPException
                raise HTTPException(503, 'Resume matching requires the backend job index and metadata. Live job search is available.')
            index = faiss.read_index(str(INDEX_PATH))
            jobs = pd.read_parquet(METADATA_PATH)
            model = get_embedding_model()

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
