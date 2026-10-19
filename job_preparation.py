"""Evidence-backed description decoding without inferring unstated requirements."""
import re
from html.parser import HTMLParser
from match_scoring import find_skills


class DescriptionText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0

    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.hidden+=1
        elif tag in ('p','div','li','br','h1','h2','h3','h4','section'):self.parts.append('\n')

    def handle_endtag(self,tag):
        if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
        elif tag in ('p','div','li','h1','h2','h3','h4','section'):self.parts.append('\n')

    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)


HEADINGS={
    'responsibilities':r'(?:responsibilities|duties|what you(?: will|’ll|\x27ll) do|your role)',
    'required':r'(?:requirements|required qualifications|minimum qualifications|essential skills|must have)',
    'preferred':r'(?:preferred qualifications|preferred skills|nice to have|bonus skills|desirable)',
}


def decode_description(value):
    parser=DescriptionText();parser.feed(value)
    cleaned=''.join(parser.parts)
    groups={k:[] for k in ('responsibilities','required','preferred','conditions','review')}
    context=None
    for line in cleaned.splitlines():
        line=re.sub(r'\s+',' ',line).strip(' \t•*-')
        if not line:continue
        inline=next(((k,re.match(r'^'+pattern+r'\s*:\s*(.+)$',line,re.I)) for k,pattern in HEADINGS.items() if re.match(r'^'+pattern+r'\s*:\s*(.+)$',line,re.I)),None)
        if inline:
            context=inline[0];line=inline[1].group(1)
        if re.fullmatch(r'(about us|about the company|benefits|our benefits|equal opportunity|how to apply|application process)\s*:?',line,re.I):
            context=None;continue
        heading=next((k for k,pattern in HEADINGS.items() if re.fullmatch(pattern+r'\s*:',line,re.I) or re.fullmatch(pattern,line,re.I)),None)
        if heading:context=heading;continue
        if len(line)<100 and line.endswith(':'):context=None
        for quote in re.split(r'(?<=[.!?])\s+(?=[A-Z])',line):
            category=context
            if re.search(r'\b(preferred|nice[- ]to[- ]have|a plus|desirable|not required)\b',quote,re.I):category='preferred'
            elif re.search(r'\b(must|required|minimum|essential|need to have)\b',quote,re.I):category='required'
            if re.search(r'\b(salary|compensation|pay range|remote|hybrid|on.site|travel|relocat|sponsor|visa|shift|weekend|timezone|time zone|deadline)\w*\b|[$€£]',quote,re.I):
                groups['conditions'].append({'quote':quote,'basis':'Explicit wording in supplied description'})
            if category in ('responsibilities','required','preferred'):
                groups[category].append({'quote':quote,'basis':'Explicit wording / section heading'})
            elif re.search(r'\b(responsible for|you will|you’ll|duties include)\b',quote,re.I):
                groups['responsibilities'].append({'quote':quote,'basis':'Responsibility wording'})
            elif not re.search(r'\b(salary|remote|hybrid|compensation)\b|[$€£]',quote,re.I):
                groups['review'].append({'quote':quote,'basis':'No clear requirement category; review original wording'})
    for key in groups:
        unique={entry['quote']:entry for entry in groups[key]}
        groups[key]=list(unique.values())[:40]
    unspecified=[]
    for name,pattern in [('Compensation',r'[$€£]|\b(salary|compensation|pay range)\b'),('Work arrangement',r'\b(remote|hybrid|on.site)\b'),('Sponsorship',r'\b(sponsor\w*|visa)\b'),('Application deadline',r'\b(deadline|apply by|closing date)\b')]:
        if not re.search(pattern,cleaned,re.I):unspecified.append(name)
    return {'sections':groups,'not_specified':unspecified,'recognized_skills':find_skills(cleaned),
            'method':'Local wording and section rules. Quotes are drawn from the supplied description; categories may need correction. No employer page is fetched or verified.',
            'has_description':bool(cleaned.strip())}


def build_preview(description,profile,resume):
    decoded=decode_description(description)
    contact=[key for key in ('first_name','last_name','email','phone','location') if not str(profile.get(key) or '').strip()]
    checks=[{'label':'Contact details','state':'prepare' if contact else 'available',
             'detail':'Add: '+', '.join(k.replace('_',' ') for k in contact) if contact else 'Saved profile has name, email, phone and location.','link':'/profile'},
            {'label':'Resume','state':'available' if resume else 'prepare',
             'detail':'Selected: '+resume['name'] if resume else 'Choose a saved resume or upload one in the Resume Library.','link':'/resumes'}]
    source=str(profile.get('skills') or '')+' '+(resume['extracted_text'] if resume else '')
    known=set(find_skills(source)); required_text=' '.join(x['quote'] for x in decoded['sections']['required'])
    required=set(find_skills(required_text))
    skill_evidence={'supported':sorted(required & known),'not_found':sorted(required-known),
                    'note':'Keyword evidence from your saved skills and selected resume; absence is not proof you lack a skill. This does not assess eligibility.'}
    documents=[]
    for label,pattern in [('Cover letter',r'\bcover letter\b'),('Portfolio / work samples',r'\b(portfolio|work samples)\b'),('Transcript',r'\btranscript\b'),('References',r'\breferences\b')]:
        quotes=[x['quote'] for rows in decoded['sections'].values() for x in rows if re.search(pattern,x['quote'],re.I)]
        if quotes:documents.append({'name':label,'quotes':list(dict.fromkeys(quotes))[:3], 'status':'Mentioned; confirm whether required'})
    return {'decoder':decoded,'checks':checks,'skill_evidence':skill_evidence,'documents':documents,
            'manual_steps':['Check that the opening is still active on the employer website.',
                            'Complete employer sign-in, verification or CAPTCHA yourself if requested.',
                            'Review eligibility, consent and employer-specific answers before confirming.',
                            'Review the completed application and submit it yourself.'],
            'limitations':'Preparation preview only. Actual form questions, required uploads and supported controls are known only after inspecting the employer application. No time estimate or application-readiness score is inferred.'}
