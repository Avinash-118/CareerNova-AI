
from io import BytesIO
from zipfile import ZipFile
import pymupdf
from docx import Document


def extract_resume_text(filename: str, file_bytes: bytes) -> str:
    """Extract text from a PDF or DOCX resume."""

    extension = filename.lower().rsplit(".", 1)[-1]

    if extension == "pdf":
        with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
            if len(pdf)>250:
                raise ValueError("Resume exceeds the 250-page limit")
            text = "\n".join(page.get_text() for page in pdf)

    elif extension == "docx":
        with ZipFile(BytesIO(file_bytes)) as archive:
            entries=archive.infolist()
            if len(entries)>2000 or sum(entry.file_size for entry in entries)>25*1024*1024:
                raise ValueError("Resume document is too large when expanded")
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
