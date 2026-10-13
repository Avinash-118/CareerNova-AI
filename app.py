
import fitz
import streamlit as st
import faiss
import pandas as pd
from sentence_transformers import SentenceTransformer
from pathlib import Path
from urllib.parse import urlparse

st.set_page_config(
    page_title="AI Job Matching Platform",
    page_icon="💼",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent

@st.cache_resource
def load_search_engine():
    index = faiss.read_index(str(BASE_DIR / "jobs_faiss.index"))
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return index, model

@st.cache_data
def load_jobs():
    return pd.read_parquet(BASE_DIR / "jobs_metadata.parquet")

st.title("💼 AI-Powered Job Matching Platform")
st.write("Discover relevant jobs using AI-powered semantic search.")

try:
    index, model = load_search_engine()
    jobs = load_jobs()

    if index.ntotal != len(jobs):
        st.error("FAISS index and job metadata do not match.")
        st.stop()

    st.success(f"Ready to search {len(jobs):,} job postings!")

except Exception as e:
    st.error(f"Unable to load search engine: {e}")
    st.stop()

st.divider()
st.subheader("📄 AI Resume Job Matching")

uploaded_resume = st.file_uploader(
    "Upload your resume (PDF)",
    type=["pdf"]
)

resume_text = ""

if uploaded_resume is not None:
    try:
        with fitz.open(
            stream=uploaded_resume.getvalue(),
            filetype="pdf"
        ) as pdf:
            resume_text = "\n".join(
                page.get_text() for page in pdf
            )

        if resume_text.strip():
            st.success("Resume uploaded and text extracted successfully!")

            st.write("Resume text extracted:",
                     len(resume_text), "characters")

            with st.expander("Preview Extracted Resume"):
                st.text(resume_text[:1500])
        else:
            st.warning(
                "No readable text found in this PDF."
            )

    except Exception as e:
        st.error(f"Unable to read resume: {e}")

st.divider()

st.sidebar.header("🔎 Job Search Filters")

location = st.sidebar.text_input(
    "Preferred Location",
    placeholder="Texas, Houston, Remote..."
)

top_k = st.sidebar.slider(
    "Number of Jobs",
    min_value=5,
    max_value=30,
    value=10
)

query = st.text_input(
    "What kind of job are you looking for?",
    placeholder="Data Scientist with Python, SQL and Machine Learning"
)

if st.button("🔍 Find Matching Jobs", type="primary"):

    # Use both resume and job preferences when available
    if resume_text.strip() and query.strip():
        search_text = (
            f"Desired job: {query}\n\n"
            f"Candidate resume:\n{resume_text[:6000]}"
        )

    elif resume_text.strip():
        search_text = resume_text[:6000]

    elif query.strip():
        search_text = query

    else:
        search_text = ""

    if not search_text:
        st.warning("Please upload a resume or enter a job title or skills.")

    else:
        with st.spinner("Searching job postings..."):

            query_vector = model.encode(
                           [search_text],
                            convert_to_numpy=True,
                            normalize_embeddings=True
                )

            # Retrieve a larger pool to allow location filtering
            search_count = min(len(jobs), max(1000, top_k * 50))

            scores, indices = index.search(
                query_vector,
                search_count
            )

            results = []

            for idx, score in zip(indices[0], scores[0]):
                if idx < 0:
                    continue

                job = jobs.iloc[int(idx)]

                job_location = str(job.get("location", ""))

                if location.strip() and location.lower() != "any":
                    if location.lower() not in job_location.lower():
                        continue

                results.append((job, float(score)))

                if len(results) >= top_k:
                    break

        if not results:
            st.warning(
                "No matching jobs found. Try another location or search."
            )

        else:
            st.subheader(f"🎯 Top {len(results)} Matching Jobs")

            for rank, (job, score) in enumerate(results, start=1):

                title = str(job.get("title", "Unknown Title"))
                company = str(job.get("company", "Unknown Company"))
                job_location = str(job.get("location", "Not specified"))
                apply_url = str(job.get("apply_url", ""))

                with st.container(border=True):

                    st.subheader(f"{rank}. {title}")

                    col1, col2, col3 = st.columns(3)

                    col1.write(f"🏢 **Company:** {company}")
                    col2.write(f"📍 **Location:** {job_location}")
                    col3.metric("Similarity Score", f"{score:.2%}")

                    description = str(
                        job.get("job_description", "")
                    )

                    if description and description.lower() != "nan":
                        with st.expander("View Job Description"):
                            st.write(description)

                    parsed = urlparse(apply_url)

                    if (
                        parsed.scheme == "https"
                        and parsed.netloc
                    ):
                        st.link_button(
                            "Apply Now ↗",
                            apply_url
                        )
                    else:
                        st.caption("Application link unavailable")
