import io
import os
import secrets
import unittest
from unittest.mock import patch
from mock_interview_service import make_questions, assess_answer, make_report


class InterviewCoachingTests(unittest.TestCase):
    def test_role_resume_and_job_grounding(self):
        resume='Built Python and SQL reporting tools for 100 users at Acme.'
        questions=make_questions('Data Analyst',resume,'Use Python and SQL to investigate data quality.')
        self.assertEqual(len({q['id'] for q in questions}),len(questions))
        self.assertTrue(any(q.get('resume_evidence')==resume for q in questions))
        self.assertTrue(any(q['category']=='SQL' for q in questions))
        self.assertIn('dashboard',next(q['question'] for q in questions if q['id']=='scenario'))

    @patch.dict(os.environ,{'INTERVIEW_SEMANTIC_ENABLED':'false'})
    def test_role_only_mix_and_round_feedback(self):
        questions=make_questions('Software Engineer','')
        self.assertEqual({q['round'] for q in questions},{'Technical','Behavioral','HR'})
        self.assertTrue(any('idempotency' in q['question'] for q in questions))
        self.assertTrue(all(q['round']=='HR' for q in questions if q['id'].startswith('hr-')))
        report=make_report(questions,{q['id']:'I would contribute to the team because I am interested in the role. I would learn the responsibilities and ask how success is measured to understand expectations and support.' for q in questions})
        self.assertEqual({r['round'] for r in report['round_feedback']},{'Technical','Behavioral','HR'})
        self.assertTrue(all(r['answered']==r['total'] for r in report['round_feedback']))
        hr=next(f for f in report['feedback'] if f['question_id']=='hr-goals')
        self.assertNotIn('personal_action',hr['signals'])

    def test_feedback_distinguishes_detail_and_skips(self):
        q={'id':'q','category':'Behavioral','concepts':[]}
        short=assess_answer(q,'I am good.')
        detailed=assess_answer(q,'During a client project I analyzed the discrepancy because it affected reporting. I tested the result, measured the outcome and learned to monitor data quality.')
        self.assertGreater(sum(detailed['signals'].values()),sum(short['signals'].values()))
        self.assertFalse(assess_answer(q,'')['answered'])
        self.assertTrue(short['improvements'])

    @patch.dict(os.environ,{'INTERVIEW_SEMANTIC_ENABLED':'false'})
    def test_report_no_false_hiring_claim_and_skips(self):
        questions=make_questions('Support Specialist','Resolved customer issues and documented common troubleshooting steps.')
        report=make_report(questions,{'intro':'I enjoy helping customers.'})
        self.assertEqual(report['answered_count'],1)
        self.assertEqual(len(report['unanswered']),len(questions)-1)
        self.assertIn('does not assess technical correctness',report['limitations'])
        self.assertNotIn('score',report)

    def test_semantic_signal_and_fallback(self):
        import numpy as np
        questions=[{'id':'q','category':'Role','question':'Investigate a database error','concepts':[]}]
        class Model:
            def encode(self,*args,**kwargs):return np.array([[1.,0.],[0.,1.]])
        with patch.dict(os.environ,{'INTERVIEW_SEMANTIC_ENABLED':'true'}),patch('faiss_search.get_embedding_model',return_value=Model()):
            report=make_report(questions,{'q':'The weather is nice today.'})
            self.assertEqual(report['feedback'][0]['topic_overlap'],'Limited')
            self.assertIn('semantic model',report['analysis_method'])
        with patch.dict(os.environ,{'INTERVIEW_SEMANTIC_ENABLED':'true'}),patch('faiss_search.get_embedding_model',side_effect=RuntimeError('No local weights')):
            self.assertNotIn('topic_overlap',make_report(questions,{'q':'My answer'})['feedback'][0])


class InterviewIntegration(unittest.TestCase):
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
        client=TestClient(self.backend.app,headers={'X-CareerNova-Client':'web'})
        r=client.post('/api/auth/register',json={'email':f'cn-interview-{secrets.token_hex(8)}@example.com','full_name':'Interview Tester','password':'Interview-Test-Only-2026!'})
        self.assertEqual(r.status_code,201,r.text)
        uid=client.get('/api/auth/me').json()['id'];self.users.append(uid)
        return client,uid

    @patch.dict(os.environ,{'INTERVIEW_SEMANTIC_ENABLED':'false'})
    def test_start_with_role_only(self):
        a,_=self.account()
        response=a.post('/api/mock-interviews',json={'role':'Software Engineer'})
        self.assertEqual(response.status_code,201,response.text)
        session=response.json()
        self.assertIsNone(session['resume_id'])
        self.assertEqual(session['resume_name'],'Role-only practice')
        self.assertEqual({q['round'] for q in session['questions']},{'HR','Behavioral','Technical'})
        self.assertEqual(a.delete(f"/api/mock-interviews/{session['id']}").status_code,200)

    @patch.dict(os.environ,{'INTERVIEW_SEMANTIC_ENABLED':'false'})
    def test_complete_private_interview_resume_and_report(self):
        from resume_tailoring import make_docx
        from sqlalchemy import text
        a,uid=self.account();b,_=self.account()
        r=a.post('/api/resumes',data={'name':'Interview resume'},files={'file':('resume.docx',make_docx('Built Python SQL tools for 100 users.\nEducation: University degree.'))})
        rid=r.json()['id'];payload={'role':'Data Analyst','resume_id':rid,'job_description':'Investigate data quality using SQL.'}
        self.assertEqual(b.post('/api/mock-interviews',json=payload).status_code,404)
        r=a.post('/api/mock-interviews',json=payload)
        self.assertEqual(r.status_code,201,r.text);session=r.json();sid=session['id'];url=f'/api/mock-interviews/{sid}'
        self.assertEqual(b.get(url).status_code,404)
        self.assertEqual(b.post(url+'/answer',json={'question_id':'intro','answer':'Bad'}).status_code,404)
        self.assertEqual(b.post(url+'/finish').status_code,404)
        self.assertEqual(b.delete(url).status_code,404)
        self.assertEqual(b.get('/api/mock-interviews').json()['interviews'],[])
        self.assertEqual(a.post(url+'/finish').status_code,400)
        self.assertEqual(a.post(url+'/answer',json={'question_id':'invented','answer':'No'}).status_code,400)
        self.assertEqual(a.post(url+'/answer',json={'question_id':'intro','answer':'a'*10001}).status_code,422)
        for q in session['questions']:
            response=a.post(url+'/answer',json={'question_id':q['id'],'answer':'During a client project I analyzed SQL data because quality mattered. I tested the result and measured the outcome.' if q['id']!='teamwork' else ''})
            self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(len(a.get(url).json()['answers']),len(session['questions']))
        report=a.post(url+'/finish');self.assertEqual(report.status_code,200,report.text)
        self.assertEqual(report.json()['report']['answered_count'],len(session['questions'])-1)
        self.assertEqual(a.post(url+'/finish').json()['report'],report.json()['report'])
        self.assertEqual(a.post(url+'/answer',json={'question_id':'intro','answer':'Changed'}).status_code,409)
        self.assertEqual(len(a.get('/api/privacy/export').json()['mock_interviews']),1)
        a.delete(f'/api/resumes/{rid}')
        self.assertIsNone(a.get(url).json()['resume_id'])
        self.assertEqual(a.delete(url).status_code,200)
        with self.backend.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM public.mock_interviews WHERE user_id=:u'),{'u':uid}).scalar_one(),0)


if __name__=='__main__':unittest.main()
