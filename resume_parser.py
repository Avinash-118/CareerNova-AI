
from io import BytesIO
import pymupdf
from docx import Document


def extract_resume_text(filename: str, file_bytes: bytes) -> str:
    """Extract text from a PDF or DOCX resume."""

    extension = filename.lower().rsplit(".", 1)[-1]

    if extension == "pdf":
        with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
            text = "\n".join(page.get_text() for page in pdf)

    elif extension == "docx":
        document = Document(BytesIO(file_bytes))
        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    else:
        raise ValueError("Only PDF and DOCX resumes are supported.")

    if not text.strip():
        raise ValueError("No readable text found in the resume.")

    return text.strip()
