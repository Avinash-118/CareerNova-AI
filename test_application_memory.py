import secrets
import unittest
from unittest.mock import MagicMock, patch
from application_memory import evidence_for, question_key
from application_session import ApplicationSession


class EvidenceTests(unittest.TestCase):
    def test_exact_question_and_options(self):
        field = {'label':'Available start date?', 'tag':'input', 'type':'date'}
        self.assertNotEqual(question_key(field), question_key({**field,'label':'Available end date?'}))
        self.assertNotEqual(question_key(field), question_key({**field,'options':['Yes']}))

    def test_resume_profile_conflict(self):
        field = {'label':'Email', 'type':'email'}
        result = evidence_for(field, {'email':'one@example.com'}, [], {'name':'Engineering', 'extracted_text':'two@example.com'})
        self.assertTrue(result['conflict'])
        self.assertEqual(len(result['evidence']),2)
        ambiguous = evidence_for(field, {'email':'one@example.com'}, [], {'name':'Engineering', 'extracted_text':'two@example.com three@example.com'})
        self.assertFalse(ambiguous['conflict'])

    def test_conflict_prevents_automatic_fill(self):
        session = ApplicationSession('https://example.com')
        self.addCleanup(session.executor.shutdown)
        field = {'label':'Email','type':'email','tag':'input'}
        session.fields = [field]
        control = MagicMock(); session.field_locators = [control]
        session._status = lambda: {'stage':'ready'}
        session.prepare_evidence({'email':'one@example.com'}, [], {'name':'Resume','extracted_text':'two@example.com'})
        result = session._autofill({'email':'one@example.com'})
        control.fill.assert_not_called()
        self.assertTrue(result['next_question']['question']['conflict'])


class MemoryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import backend
        from fastapi.testclient import TestClient
        cls.backend = backend
        cls.context = TestClient(backend.app)
        cls.context.__enter__()
        cls.users = []

    @classmethod
    def tearDownClass(cls):
        from sqlalchemy import text
        with cls.backend.engine.begin() as conn:
            for uid in cls.users:
                conn.execute(text('DELETE FROM public.users WHERE id=:u'), {'u':uid})
        cls.context.__exit__(None,None,None)

    def account(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.backend.app, headers={'X-CareerNova-Client':'web'})
        r = client.post('/api/auth/register',json={'email':f'cn-memory-{secrets.token_hex(8)}@example.com','full_name':'Memory Tester','password':'Memory-Test-Only-2026!'})
        self.assertEqual(r.status_code,201,r.text)
        uid = client.get('/api/auth/me').json()['id']; self.users.append(uid)
        return client,uid

    def test_consent_isolation_forgetting_and_export(self):
        import application_session_routes as routes
        a,uid = self.account(); b,_ = self.account()
        session = ApplicationSession('https://example.com')
        self.addCleanup(session.executor.shutdown)
        session.fields = [{'label':'Preferred contact email','type':'email','tag':'input'}]
        control = MagicMock(); control.input_value.return_value = 'candidate@example.com'
        session.field_locators = [control]
        routes.session_owners[session.session_id] = uid
        self.addCleanup(routes.session_owners.pop,session.session_id,None)
        url = f'/api/agent/{session.session_id}/answer'
        with patch.object(routes,'get_session',return_value=session):
            self.assertEqual(b.post(url,json={'value':'candidate@example.com','remember':True}).status_code,404)
            self.assertEqual(a.post(url,json={'value':'candidate@example.com'}).status_code,200)
            self.assertEqual(a.get('/api/agent/memory/answers').json()['answers'],[])
            session.index=0
            self.assertEqual(a.post(url,json={'value':'candidate@example.com','remember':True,'source':'voice'}).status_code,200)
        memory = a.get('/api/agent/memory/answers').json()['answers'][0]
        self.assertEqual(memory['source'],'voice')
        self.assertEqual(b.get('/api/agent/memory/answers').json()['answers'],[])
        self.assertEqual(len(a.get('/api/privacy/export').json()['application_answer_memory']),1)
        b.delete(f"/api/agent/memory/answers/{memory['id']}")
        self.assertEqual(len(a.get('/api/agent/memory/answers').json()['answers']),1)
        a.delete(f"/api/agent/memory/answers/{memory['id']}")
        self.assertEqual(a.get('/api/agent/memory/answers').json()['answers'],[])


if __name__ == '__main__':
    unittest.main()
