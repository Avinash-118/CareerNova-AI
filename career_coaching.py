"""Explainable, evidence-based career coaching without invented experience."""
import re
from match_scoring import find_skills, calculate_match

def coach_resume(resume, description):
    found = find_skills(resume)
    missing = sorted(set(find_skills(description)) - set(found))
    lines = [line.strip() for line in resume.splitlines() if len(line.strip()) > 30][:8]
    suggestions = []
    for line in lines[:4]:
        clean = re.sub(r'^[\s•\-*]+', '', line)
        first, _, rest = clean.rstrip('.;').partition(' ')
        verbs = {'built':'building','developed':'developing','created':'creating','implemented':'implementing','managed':'managing','led':'leading','designed':'designing','analyzed':'analyzing','improved':'improving','automated':'automating','delivered':'delivering'}
        action = f"{verbs[first.lower()]} {rest}" if first.lower() in verbs else f"completing this work: {clean.rstrip('.;')}"
        suggestions.append({'original': clean, 'suggested': f'Delivered [specific outcome] by {action}; measured by [verified result].',
                            'note': 'Replace brackets with facts you can support. Do not invent numbers or responsibilities.'})
    checks = {'has_measurable_results': bool(re.search(r'\d+\s*(%|percent|hours|users|days|projects)', resume, re.I)),
              'has_experience_section': bool(re.search(r'experience|employment', resume,re.I)),
              'has_education_section': bool(re.search(r'education|university|degree',resume,re.I))}
    return {'method':'Rule-based coaching using the existing skill vocabulary; suggestions require your review.',
            'matched_skills': sorted(set(found)&set(find_skills(description))), 'missing_skills':missing,
            'checks':checks, 'bullet_suggestions':suggestions,
            'next_steps':['Use the employer’s terminology only where it accurately describes your experience.',
                          'Lead bullets with actions and add outcomes supported by your actual work.',
                          'Keep formatting simple and review the exported document before applying.']}


def explain_match(resume, description, semantic_similarity):
    result = calculate_match(resume, description, semantic_similarity)
    return {**result, 'semantic_similarity':round(semantic_similarity,4),
            'formula':'70% semantic similarity + 30% required-skill coverage when recognized job skills exist; otherwise semantic similarity only. Scores are clamped to 0–100.',
            'limitations':'A ranking aid, not an assessment of hiring eligibility. The skill vocabulary is limited and the resume may omit relevant experience.'}


def interview_questions(title, description, profile):
    skills = find_skills(description)[:6]
    questions = [
        {'id':'intro','category':'Motivation','question':f'What interests you about the {title} role, and which experience best supports your application?', 'guide':'Connect the role to one real example from your work or education.'},
        {'id':'star','category':'Behavioral','question':'Describe a difficult project, your specific contribution, and the outcome.', 'guide':'Use Situation, Task, Action, Result. Be clear about your own contribution.'},
        {'id':'tradeoff','category':'Problem solving','question':'Tell me about a technical or business tradeoff you made. How did you validate your decision?', 'guide':'Discuss alternatives, constraints, evidence, and what you would improve.'},
    ]
    profile_skills = set(find_skills(profile))
    for index, skill in enumerate(skills):
        questions.append({'id':f'skill-{index}', 'category':skill,
                          'question':f'How would you use {skill} in this role? Walk through a concrete example and how you would test your approach.',
                          'guide':'Draw on your documented experience.' if skill in profile_skills else 'This skill is not in your profile. Be honest about your current knowledge and explain how you would learn it.'})
    questions.append({'id':'ask','category':'Your questions','question':'What would you ask the hiring team about expectations, collaboration, and success in the first 90 days?', 'guide':'Prepare two specific questions based on the job description.'})
    return questions
