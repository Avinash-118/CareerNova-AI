"""Explicit answer memory and conservative, explainable consistency checks."""
import hashlib
import json
import re
from application_field_mapping import profile_key


def question_key(field):
    # Exact wording and options: do not reuse answers to merely similar questions.
    context = {k: field.get(k, '') for k in ('label', 'type', 'tag', 'options')}
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


def evidence_for(field, profile, memories, resume=None):
    key = profile_key(field)
    evidence = []
    value = (' '.join(str(profile.get(k) or '') for k in ('first_name', 'last_name')).strip()
             if key == '__full_name__' else str(profile.get(key) or '').strip())
    if value:
        evidence.append({'source': 'Saved candidate profile', 'value': value})
    memory = next((m for m in memories if m['question_key'] == question_key(field)), None)
    if memory:
        evidence.append({'source': 'Previously confirmed ' + memory['source'] + ' answer',
                         'value': memory['answer'], 'updated_at': str(memory['updated_at'])})
    # Resume extraction is intentionally narrow: one distinct email, never inferred experience.
    if resume and key == 'email':
        emails = set(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', resume['extracted_text']))
        if len(emails) == 1:
            evidence.append({'source': 'Resume: ' + resume['name'], 'value': emails.pop()})
    distinct = {e['value'].strip().casefold() for e in evidence}
    return {'evidence': evidence, 'conflict': len(distinct) > 1,
            'memory_available': memory is not None}
