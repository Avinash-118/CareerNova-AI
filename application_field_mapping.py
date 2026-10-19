"""Conservative matching of employer field metadata to saved profile facts."""
import re


def profile_key(field):
    label = re.sub(r'[^a-z0-9]+', ' ', field.get('label', '').lower()).strip()
    label = re.sub(r'\s+required$', '', label)
    if label in ('name', 'your name', 'legal name', 'full legal name'):
        return '__full_name__'
    autocomplete = field.get('autocomplete', '').split()
    tokens = {'given-name': 'first_name', 'family-name': 'last_name',
              'name': '__full_name__', 'email': 'email', 'tel': 'phone'}
    for token in autocomplete:
        if token in tokens:
            return tokens[token]
    aliases = {
        'first name': 'first_name', 'given name': 'first_name',
        'last name': 'last_name', 'family name': 'last_name', 'surname': 'last_name',
        'full name': '__full_name__', 'email': 'email', 'email address': 'email',
        'phone': 'phone', 'phone number': 'phone', 'mobile': 'phone',
        'location': 'location', 'current location': 'location',
        'linkedin': 'linkedin_url', 'linkedin url': 'linkedin_url',
        'github': 'github_url', 'portfolio': 'portfolio_url',
        'university': 'university', 'school': 'university', 'degree': 'degree',
        'experience years': 'experience_years', 'years of experience': 'experience_years',
        'skills': 'skills', 'education': 'education',
    }
    for attribute in ('name', 'id', 'label'):
        value = re.sub(r'([a-z])([A-Z])', r'\1 \2', field.get(attribute, ''))
        value = re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()
        value = re.sub(r'\s+(required|optional)$', '', value)
        if value in aliases:
            return aliases[value]
    return None
