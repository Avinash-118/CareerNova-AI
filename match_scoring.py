
import re

SKILLS = [
    "Python", "SQL", "Excel", "Power BI",
    "Tableau", "Pandas", "NumPy", "Scikit-learn",
    "TensorFlow", "PyTorch", "Machine Learning",
    "Deep Learning", "NLP", "RAG", "LLM",
    "FAISS", "LangChain", "Snowflake",
    "Databricks", "Spark", "PySpark",
    "AWS", "Azure", "Google Cloud",
    "Docker", "Kubernetes", "FastAPI",
    "React", "PostgreSQL", "MongoDB",
    "ETL", "Data Visualization", "dbt",
    "Git", "Statistics"
]


def find_skills(text):
    found = []
    content = text.lower()

    for skill in SKILLS:
        pattern = (
            r"(?<!\w)"
            + re.escape(skill.lower())
            + r"(?!\w)"
        )

        if re.search(pattern, content):
            found.append(skill)

    return found


def calculate_match(
    resume_text,
    job_description,
    semantic_similarity
):
    resume_skills = set(find_skills(resume_text))
    job_skills = set(find_skills(job_description))

    matched = sorted(resume_skills & job_skills)
    missing = sorted(job_skills - resume_skills)

    if job_skills:
        skill_score = (
            len(matched) / len(job_skills)
        )
        combined_score = (
            0.70 * semantic_similarity
            + 0.30 * skill_score
        )
    else:
        skill_score = None
        combined_score = semantic_similarity

    combined_score = max(
        0.0, min(1.0, combined_score)
    )

    return {
        "match_percentage": round(
            combined_score * 100, 1
        ),
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_match_percentage": (
            round(skill_score * 100, 1)
            if skill_score is not None
            else None
        )
    }
