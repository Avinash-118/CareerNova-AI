"""Resume-grounded questions and transparent local interview coaching."""
import re
import os
from match_scoring import find_skills


ROLE_SCENARIOS = [
    (r'data|analyst|scientist', 'A stakeholder sees an unexpected change in a dashboard metric. How would you check data quality, investigate causes and explain your findings?'),
    (r'software|developer|engineer|programmer', 'A service becomes slow after a release. How would you investigate, choose a fix and verify that it works?'),
    (r'market|content|seo', 'A campaign is getting clicks but few conversions. How would you investigate and design a measurable improvement?'),
    (r'sales|account executive', 'A prospective customer is interested but raises a price objection. How would you understand their needs and respond?'),
    (r'finance|accountant|audit', 'You find a discrepancy shortly before a reporting deadline. How would you investigate, document and escalate it?'),
    (r'nurs|health|clinical', 'How would you respond to a concern about patient safety while coordinating with your team and following applicable procedures?'),
    (r'customer|support', 'A frustrated customer reports a recurring issue. How would you clarify the problem, set expectations and follow through?'),
    (r'project|product|manager', 'Two stakeholders disagree on priorities with a deadline approaching. How would you make and communicate a decision?'),
]


TECHNICAL_QUESTIONS = [
    (r'data|analyst|scientist', [
        'A SQL join unexpectedly doubles your row count. Explain how you would find the cause and correct it without losing valid records.',
        'How would you handle missing values and outliers before analyzing a dataset? Explain how you would check whether your choices bias the result.']),
    (r'front.?end|react|web developer', [
        'Explain state versus props in a component-based interface. How would you diagnose unnecessary renders and verify an improvement?',
        'How would you build and test an accessible form with client-side and server-side validation?']),
    (r'software|developer|engineer|programmer', [
        'How would you design an API endpoint that safely handles retries? Explain validation, idempotency and the tests you would write.',
        'When would you use a database index, and what tradeoffs can it introduce for writes and storage? Explain how you would measure its effect.']),
    (r'market|content|seo', [
        'How would you design an A/B test for a campaign? Explain your metric, comparison groups and how you would avoid misleading conclusions.',
        'Explain the difference between conversion rate and customer acquisition cost. How would you use both when evaluating a campaign?']),
    (r'finance|accountant|audit', [
        'Walk through reconciling two financial records that disagree. What checks and documentation would you use?',
        'How would you distinguish a timing difference from an accounting error and explain its reporting implications?']),
    (r'sales|customer|support', [
        'How would you structure troubleshooting when a customer reports an intermittent problem? Explain what evidence you would gather and when you would escalate.',
        'Which measures would you use to evaluate the quality of a customer interaction, and what are the limitations of those measures?']),
]


def make_questions(role, resume, description=''):
    job_skills = find_skills(description + ' ' + role)
    resume_skills = find_skills(resume)
    skills = (job_skills + [s for s in resume_skills if s not in job_skills])[:3]
    questions = [
        {'id':'intro', 'round':'HR', 'category':'Role motivation', 'question':f'For the {role} role, introduce yourself and connect your actual experience to two responsibilities you expect in this position.',
         'guide':'Explain the connection with specific examples, rather than listing keywords.', 'concepts':job_skills[:4]},
    ]
    lines = [line.strip() for line in resume.splitlines() if 35 <= len(line.strip()) <= 400 and '@' not in line and not re.search(r'https?://',line)]
    if lines:
        excerpt = next((line for line in lines if any(skill.lower() in line.lower() for skill in skills)), lines[0])
        questions.append({'id':'resume', 'round':'Behavioral', 'category':'Resume discussion', 'question':'Choose the experience shown below. What was the situation, what did you personally do, and what was the outcome?',
                          'resume_evidence':excerpt, 'guide':'Clarify your own contribution and distinguish it from the team’s work.', 'concepts':find_skills(excerpt)})
    for i, skill in enumerate(skills):
        questions.append({'id':f'skill-{i}', 'round':'Technical', 'category':skill, 'question':f'How would you use {skill} in the {role} role? Explain a concrete example, a tradeoff and how you would validate the result.',
                          'guide':'Use a real example if you have one. If this is unfamiliar, explain what you know and how you would learn it.', 'concepts':[skill],
                          'resume_support':skill in resume_skills})
    technical = next((items for pattern,items in TECHNICAL_QUESTIONS if re.search(pattern,role,re.I)), [
        f'For a {role}, describe a core method or tool used in the work. Explain how it works, where it can fail and how you would validate the result.',
        f'Choose a practical problem in the {role} role. Break down your approach, justify your choices and explain how you would check quality.'])
    for i, prompt in enumerate(technical):
        questions.append({'id':f'technical-{i}', 'round':'Technical', 'category':'Role knowledge', 'question':prompt,
                          'guide':'Explain the mechanism, assumptions, failure cases and validation. State clearly if this topic is outside your expertise.', 'concepts':[]})
    scenario = next((q for pattern,q in ROLE_SCENARIOS if re.search(pattern,role,re.I)), f'Describe a challenging situation you might face as a {role}. How would you prioritize your actions and assess success?')
    questions.extend([
        {'id':'scenario','round':'Technical','category':'Role scenario','question':scenario,'guide':'State assumptions, explain your sequence of actions and say how you would check the result.','concepts':[]},
        {'id':'teamwork','round':'Behavioral','category':'Behavioral','question':'Tell me about a disagreement or setback. What did you do personally, what happened, and what would you change next time?',
         'guide':'Use a real example with context, actions, results and reflection.','concepts':[]},
    ])
    questions.extend([
        {'id':'learning','round':'Behavioral','category':'Learning & ownership',
         'question':'Describe a time you had to learn something unfamiliar or take responsibility for a mistake. What actions did you take and what changed?',
         'guide':'Use a real situation, your specific actions, the outcome and your reflection.','concepts':[]},
        {'id':'hr-goals','round':'HR','category':'Motivation & expectations',
         'question':f'Why are you interested in a {role} position now, and what would you like to learn or contribute in your next role?',
         'guide':'Connect your goals to the role and give a specific example of what motivates you.','concepts':[]},
        {'id':'hr-questions','round':'HR','category':'Questions for the employer',
         'question':'What two questions would you ask the hiring team to understand expectations, support and success in the first 90 days?',
         'guide':'Explain why each question matters to your decision.','concepts':[]},
    ])
    return questions


def assess_answer(question, answer):
    words = re.findall(r"\b[\w'-]+\b", answer.lower())
    if not words:
        return {'question_id':question['id'],'category':question['category'],'answered':False,
                'strengths':[], 'improvements':['Practise answering this question; it was skipped.'], 'signals':{}}
    signals = {
        'specific_example':bool(re.search(r'\b(for example|for instance|project|client|customer|when|during|situation)\b',answer,re.I)),
        'personal_action':bool(re.search(r'\bI\s+(?:\w+\s+){0,2}(built|created|implemented|tested|analyzed|analysed|developed|led|checked|asked|explained|designed|would|resolved|managed|reviewed|measured)\b',answer,re.I)),
        'outcome_or_validation':bool(re.search(r'\b(result|outcome|measured|validated|verified|reduced|improved|increased|learned|test|monitor|feedback)\b',answer,re.I)),
        'tradeoff_or_reflection':bool(re.search(r'\b(tradeoff|trade-off|alternative|instead|however|because|next time|learned|risk|assumption)\b',answer,re.I)),
    }
    labels = {
        'specific_example':('A concrete example or context was detected.','Add a specific situation or project to ground your answer.'),
        'personal_action':('Your own actions or planned actions are stated.','Explain your own contribution using “I” and concrete actions.'),
        'outcome_or_validation':('An outcome or validation step was detected.','Explain the outcome or how you would verify success; use only truthful results.'),
        'tradeoff_or_reflection':('Reasoning, alternatives or reflection were detected.','Explain a tradeoff, assumption or what you learned.'),
    }
    if question.get('round') == 'HR':
        signals = {
            'role_connection':bool(re.search(r'\b(role|position|team|work|contribute|learn|responsib|expectation|success|support)\w*\b',answer,re.I)),
            'reasoning':bool(re.search(r'\b(because|why|so that|helps|important|interested|motivated|goal)\b',answer,re.I)),
            'specificity':len(words)>=30,
        }
        labels = {
            'role_connection':('A connection to the role or team was detected.','Connect your answer to responsibilities, team expectations or your contribution.'),
            'reasoning':('Your motivation or reasoning is stated.','Explain why this matters to you and how it relates to the role.'),
            'specificity':('Your answer includes some supporting detail.','Add a specific example or explain the reason behind your questions.'),
        }
    strengths = [labels[k][0] for k,v in signals.items() if v]
    improvements = [labels[k][1] for k,v in signals.items() if not v]
    concepts = question.get('concepts', [])
    mentioned = [c for c in concepts if re.search(r'(?<!\w)'+re.escape(c)+r'(?!\w)',answer,re.I)]
    if concepts and not mentioned:
        improvements.insert(0,'Connect your explanation to '+', '.join(concepts)+'. Mentioning a skill alone does not demonstrate understanding.')
    if len(words)<30:
        improvements.insert(0,'Expand this short answer with enough detail to explain your reasoning and example.')
    if len(words)>450:
        improvements.append('Practise a more focused answer: context, key actions and outcome.')
    return {'question_id':question['id'],'category':question['category'],'answered':True,'word_count':len(words),
            'strengths':strengths, 'improvements':improvements, 'signals':signals,
            'mentioned_concepts':mentioned, 'excerpt':answer[:240]}


def make_report(questions, answers):
    feedback = [assess_answer(q,answers.get(q['id'],'')) for q in questions]
    answered = [f for f in feedback if f['answered']]
    semantic_used = False
    if answered and os.getenv('INTERVIEW_SEMANTIC_ENABLED','true').lower() == 'true':
        try:
            # Reuse the local resume-matching model; never download weights here.
            from faiss_search import get_embedding_model
            import numpy as np
            model = get_embedding_model(local_only=True)
            targets = {q['id']:q for q in questions}
            inputs = [targets[f['question_id']]['question'] for f in answered] + [answers[f['question_id']][:4000] for f in answered]
            vectors = model.encode(inputs,normalize_embeddings=True,convert_to_numpy=True)
            count = len(answered)
            for i, item in enumerate(answered):
                similarity = float(np.dot(vectors[i],vectors[count+i]))
                item['topic_overlap'] = 'Limited' if similarity < .18 else 'Some' if similarity < .4 else 'Strong'
                if similarity < .18:
                    item['improvements'].insert(0,'The local language model detected limited topic overlap. Check whether your answer directly addresses the question; this signal can be wrong.')
            semantic_used = True
        except Exception:
            # Pattern feedback remains available when local weights are missing.
            pass
    priorities = sorted(answered,key=lambda f:(f.get('topic_overlap') != 'Limited',sum(f['signals'].values()),f['word_count']))[:3]
    rounds=[]
    for name in ('Technical','Behavioral','HR'):
        ids={q['id'] for q in questions if q.get('round')==name}
        items=[f for f in feedback if f['question_id'] in ids]
        done=[f for f in items if f['answered']]
        rounds.append({'round':name,'total':len(items),'answered':len(done),
                       'strengths':list(dict.fromkeys(s for f in done for s in f['strengths']))[:4],
                       'improvements':list(dict.fromkeys(s for f in done for s in f['improvements']))[:4]})
    return {'round_feedback':rounds, 'answered_count':len(answered), 'question_count':len(questions),
            'overview':f'You answered {len(answered)} of {len(questions)} questions. Review the detected answer-structure signals and practise the priorities below.',
            'analysis_method':'Local semantic model plus text-pattern coaching' if semantic_used else 'Text-pattern coaching; semantic model not used',
            'priority_practice':[{'category':f['category'],'question_id':f['question_id'],'actions':f['improvements'][:3]} for f in priorities if f['improvements']],
            'unanswered':[f['question_id'] for f in feedback if not f['answered']],
            'feedback':feedback,
            'practice_plan':['Choose one priority question and outline context, your actions and the outcome.',
                             'Record another attempt using a real example and explain how you checked your result.',
                             'Review technical accuracy with a trusted reference or mentor, then compare attempts.'],
            'limitations':'Local template-based questions and text-pattern coaching. Signals can miss valid wording or reward superficial phrases. This does not assess technical correctness, truthfulness, voice delivery, personality or hiring readiness.'}
