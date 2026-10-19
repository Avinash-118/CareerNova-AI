import secrets
import unittest
from job_preparation import decode_description,build_preview


class DecoderTests(unittest.TestCase):
    def test_sections_quotes_optional_and_conditions(self):
        source='<h2>Requirements</h2><ul><li>Python and SQL are required.</li><li>Docker is preferred, not required.</li></ul><h2>Responsibilities</h2><p>Build reporting services.</p><h2>Benefits</h2><p>Remote work with optional office visits.</p>'
        result=decode_description(source)
        sections=result['sections']
        self.assertEqual(sections['required'][0]['quote'],'Python and SQL are required.')
        self.assertEqual(sections['preferred'][0]['quote'],'Docker is preferred, not required.')
        self.assertEqual(sections['responsibilities'][0]['quote'],'Build reporting services.')
        self.assertFalse(any('Remote' in x['quote'] for x in sections['responsibilities']))
        self.assertEqual(sections['conditions'][0]['quote'],'Remote work with optional office visits.')
        self.assertIn('Sponsorship',result['not_specified'])

    def test_empty_and_unsafe_html_are_not_evidence(self):
        result=decode_description('<script>SQL required</script><style>Python required</style>')
        self.assertFalse(result['has_description'])
        self.assertEqual(result['recognized_skills'],[])
        self.assertFalse(decode_description('An exciting opportunity awaits.')['sections']['required'])

    def test_inline_headings_and_document_negation_preserved(self):
        result=build_preview('Requirements: Python\nPreferred skills: SQL\nA cover letter is not required.',{},None)
        self.assertEqual(result['skill_evidence']['not_found'],['Python'])
        self.assertEqual(result['documents'][0]['quotes'],['A cover letter is not required.'])
        self.assertIn('confirm',result['documents'][0]['status'])

    def test_readiness_uses_only_saved_sources(self):
        result=build_preview('Python and SQL are required.',{'first_name':'Asha','last_name':'Candidate','email':'a@example.com','phone':'123','location':'Remote','skills':'Python'}, {'name':'Engineering','extracted_text':'Built SQL tools.'})
        self.assertTrue(all(c['state']=='available' for c in result['checks']))
        self.assertEqual(result['skill_evidence']['supported'],['Python','SQL'])
        self.assertEqual(result['skill_evidence']['not_found'],[])
        self.assertNotIn('score',result)


class PreparationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import backend
        from fastapi.testclient import TestClient
        cls.backend=backend;cls.context=TestClient(backend.app);cls.context.__enter__();cls.users=[]

    @classmethod
    def tearDownClass(cls):
        from sqlalchemy import text
        with cls.backend.engine.begin() as conn:
            for uid in cls.users:conn.execute(text('DELETE FROM public.users WHERE id=:u'),{'u':uid})
        cls.context.__exit__(None,None,None)

    def account(self):
        from fastapi.testclient import TestClient
        a=TestClient(self.backend.app,headers={'X-CareerNova-Client':'web'})
        email=f'cn-prep-{secrets.token_hex(8)}@example.com'
        r=a.post('/api/auth/register',json={'full_name':'Preparation Tester','email':email,'password':'Preparation-Test-Only-2026!'})
        self.assertEqual(r.status_code,201,r.text)
        self.users.append(a.get('/api/auth/me').json()['id'])
        return a,email

    def test_auth_user_isolation_and_saved_profile(self):
        from fastapi.testclient import TestClient
        from resume_tailoring import make_docx
        self.assertEqual(TestClient(self.backend.app,headers={'X-CareerNova-Client':'web'}).post('/api/application-preview',json={}).status_code,401)
        a,email=self.account();b,_=self.account()
        a.post('/api/profile/save',json={'first_name':'Asha','last_name':'Candidate','email':email,'phone':'123','location':'Houston','skills':'Python'})
        r=a.post('/api/resumes',data={'name':'Preparation resume'},files={'file':('resume.docx',make_docx('Experience\nBuilt SQL tools for 100 users.'))})
        rid=r.json()['id'];data={'job_description':'Python and SQL are required.','resume_id':rid}
        r=a.post('/api/application-preview',json=data)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['skill_evidence']['supported'],['Python','SQL'])
        self.assertEqual(b.post('/api/application-preview',json=data).status_code,404)
        r=b.post('/api/application-preview',json={'job_description':'Python is required.'})
        self.assertEqual(r.json()['skill_evidence']['supported'],[])
        self.assertEqual(r.json()['checks'][0]['state'],'prepare')
        self.assertEqual(a.post('/api/application-preview',json={'job_description':'x'*30001}).status_code,422)


if __name__=='__main__':unittest.main()
