"""Integration checks against the configured local PostgreSQL database.
Creates uniquely named test users and removes only those accounts on exit.
"""
import secrets
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import text
import backend
import auth_routes
import platform_routes

class PlatformIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(backend.app)
        cls.client = cls.context.__enter__()
        cls.emails = []

    @classmethod
    def tearDownClass(cls):
        with backend.engine.begin() as conn:
            for email in cls.emails:
                uid = conn.execute(text('SELECT id FROM public.users WHERE email=:e'), {'e':email}).scalar_one_or_none()
                if uid:
                    conn.execute(text('DELETE FROM public.career_job_tracker WHERE user_id=:u'), {'u':str(uid)})
                    conn.execute(text('DELETE FROM public.users WHERE id=:u'), {'u':uid})
        cls.context.__exit__(None, None, None)

    def test_complete_account_flow_and_isolation(self):
        a = TestClient(backend.app, headers={'X-CareerNova-Client':'web'})
        b = TestClient(backend.app, headers={'X-CareerNova-Client':'web'})
        for client in (a,b):
            email = f'cn-test-{secrets.token_hex(8)}@example.com'
            self.emails.append(email)
            response=client.post('/api/auth/register',json={'full_name':'Test Candidate','email':email,'password':'Safe-test-password-2026!'})
            self.assertEqual(response.status_code,201,response.text)
            self.assertIn('HttpOnly',response.headers['set-cookie'])
            self.assertNotIn('access_token',response.json())
        self.assertEqual(TestClient(backend.app).get('/api/dashboard/jobs').status_code,401)
        self.assertEqual(TestClient(backend.app).get('/api/jobs/discover').status_code,401)
        self.assertEqual(TestClient(backend.app).post('/api/auth/logout').status_code,403)
        self.assertEqual(a.post('/api/dashboard/save',json={'job_id':'test-job','job_title':'Python Engineer','company':'Test Co'}).status_code,201)
        jobs=a.get('/api/dashboard/jobs').json()['jobs']; self.assertEqual(len(jobs),1)
        tracker_id=jobs[0]['id']
        self.assertEqual(b.get('/api/dashboard/jobs').json()['jobs'],[])
        self.assertEqual(b.patch(f'/api/dashboard/jobs/{tracker_id}',json={'status':'Offer'}).status_code,404)
        self.assertEqual(a.patch(f'/api/dashboard/jobs/{tracker_id}',json={'status':'Interview','notes':'Tuesday'}).status_code,200)
        self.assertEqual(a.get('/api/dashboard/stats').json()['interviews'],1)
        profile={'first_name':'Test','last_name':'Candidate','email':self.emails[0],'skills':'Python, SQL'}
        self.assertEqual(a.post('/api/profile/save',json=profile).status_code,200)
        self.assertEqual(a.get('/api/profile/me').json()['skills'],'Python, SQL')
        self.assertEqual(b.get('/api/profile/me').status_code,404)
        alert=a.post('/api/alerts',json={'query':'Python','location':''})
        self.assertEqual(alert.status_code,201,alert.text)
        aid=alert.json()['id']
        self.assertEqual(b.delete(f'/api/alerts/{aid}').status_code,404)
        with patch.object(platform_routes,'fetch_live_jobs',return_value=[{'id':'one','title':'Python Engineer','company':'Test Co','location':'Remote','description':'Python','employment_type':'full-time','url':'https://example.com/job'}]):
            self.assertIn('1 new matches',a.post('/api/alerts/check').json()['message'])
            self.assertIn('0 new matches',a.post('/api/alerts/check').json()['message'])
        self.assertEqual(len(a.get('/api/alerts').json()['notifications']),1)
        self.assertEqual(b.get('/api/alerts').json()['notifications'],[])
        self.assertEqual(a.post('/api/notifications/read').status_code,200)
        self.assertTrue(a.get('/api/alerts').json()['notifications'][0]['read'])
        import application_session_routes as agent
        from types import SimpleNamespace
        fake = SimpleNamespace(run=lambda method: {"stage":"ready"}, _status=lambda: None)
        with patch.object(agent, 'create_session', return_value={"session_id":"test-owned-session"}), patch.object(agent, 'get_session', return_value=fake), patch.object(agent, 'close_session', return_value={"message":"closed"}):
            self.assertEqual(a.post('/api/agent/start',json={"job_url":"https://example.com/job"}).status_code,200)
            self.assertEqual(b.get('/api/agent/test-owned-session/status').status_code,404)
            self.assertEqual(b.post('/api/agent/test-owned-session/close').status_code,404)
            self.assertEqual(a.get('/api/agent/test-owned-session/status').status_code,200)
            self.assertEqual(a.post('/api/agent/test-owned-session/close').status_code,200)
        self.assertEqual(a.post('/api/resume-match', files={"file":("resume.txt",b"invalid resume")}).status_code,400)
        from io import BytesIO
        from docx import Document
        document=Document(); document.add_paragraph("Python SQL engineer")
        upload=BytesIO(); document.save(upload)
        with patch.object(backend,'semantic_search',return_value=[{"id":"sample","title":"Engineer","description":"Python SQL","faiss_score":0.8}]):
            result=a.post('/api/resume-match',files={"file":("resume.docx",upload.getvalue())})
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()['jobs'][0]['matched_skills'],['Python','SQL'])
        uid=a.get('/api/auth/me').json()['id']
        token=secrets.token_urlsafe(48)
        with backend.engine.begin() as conn:
            conn.execute(text('INSERT INTO public.password_resets VALUES (:h,:u,:e)'),{'h':auth_routes.digest(token),'u':uid,'e':datetime.now(timezone.utc)+timedelta(minutes=10)})
        self.assertEqual(a.post('/api/auth/reset-password',json={'token':token,'password':'A-new-safe-password-2026!'}).status_code,200)
        self.assertEqual(a.get('/api/auth/me').status_code,401)
        self.assertEqual(a.post('/api/auth/reset-password',json={'token':token,'password':'A-new-safe-password-2026!'}).status_code,400)
        self.assertEqual(a.post('/api/auth/login',json={'email':self.emails[0],'password':'Safe-test-password-2026!'}).status_code,401)
        self.assertEqual(a.post('/api/auth/login',json={'email':self.emails[0],'password':'A-new-safe-password-2026!'}).status_code,200)
        cookie=a.cookies.get('careernova_session')
        self.assertEqual(a.post('/api/auth/logout').status_code,200)
        a.cookies.set('careernova_session',cookie)
        self.assertEqual(a.get('/api/auth/me').status_code,401)
        self.assertEqual(b.post('/api/auth/logout').status_code,200)

if __name__=='__main__': unittest.main(verbosity=2)
