"""Grounded local drafting: retain source text and prioritize supported skills/bullets."""
import re
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from match_scoring import find_skills


def prepare_draft(source, description):
    required = set(find_skills(description))
    supported = set(find_skills(source))
    matched = sorted(required & supported)
    missing = sorted(required - supported)
    words = set(re.findall(r'\b[a-z][a-z0-9+#.-]{2,}\b', description.lower()))
    lines = source.splitlines()
    evidence = []
    # Reorder only contiguous bullet runs; never move dates/employer headings between jobs.
    result = []
    index = 0
    while index < len(lines):
        if re.match(r'^\s*[•*\-]\s+', lines[index]):
            run = []
            while index < len(lines) and re.match(r'^\s*[•*\-]\s+', lines[index]):
                run.append(lines[index]); index += 1
            ranked = sorted(run, key=lambda line: -len(words & set(re.findall(r'\b[a-z][a-z0-9+#.-]{2,}\b', line.lower()))))
            result.extend(ranked)
            evidence.extend({'text':line, 'source':'Original resume bullet'} for line in ranked[:2])
        else:
            result.append(lines[index]); index += 1
    # Supported keywords only. Keep all source information, including original skills.
    if matched:
        result.extend(['', 'Relevant skills', ', '.join(matched)])
    return {'text':'\n'.join(result).strip(), 'matched_skills':matched, 'missing_skills':missing,
            'evidence':evidence[:8], 'method':'Local keyword-based tailoring. Reorders bullets within their original groups and highlights skills already present in the source resume. No external AI service is used.',
            'changes':['Original resume facts retained.', 'Relevant bullets prioritized within each bullet group.', 'Supported role skills highlighted; missing skills excluded.']}


def make_docx(value):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(.65)
    style = doc.styles['Normal']; style.font.name = 'Calibri'; style.font.size = Pt(11)
    for index, line in enumerate(value.splitlines()):
        paragraph = doc.add_paragraph(line)
        if index == 0 and paragraph.runs:
            paragraph.runs[0].bold = True
            paragraph.runs[0].font.size = Pt(16)
    output = BytesIO(); doc.save(output)
    return output.getvalue()
