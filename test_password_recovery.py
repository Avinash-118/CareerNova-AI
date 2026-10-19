import secrets
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
from fastapi.testclient import TestClient
from sqlalchemy import text
import backend
import auth_routes


class PasswordRecoveryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context=TestClient(backend.app);cls.context.__enter__();cls.users=[]

    @classmethod
    def tearDownClass(cls):
        with backend.engine.begin() as conn:
            for uid in cls.users:conn.execute(text('DELETE FROM public.users WHERE id=:u'),{'u':uid})
        cls.context.__exit__(None,None,None)

    def test_mail_link_reset_replay_expiry_and_session_revocation(self):
        email=f'cn-recovery-{secrets.token_hex(8)}@example.com'
        a=TestClient(backend.app,headers={'X-CareerNova-Client':'web'})
        b=TestClient(backend.app,headers={'X-CareerNova-Client':'web'})
        old='Recovery-Test-Only-2026!';new='Changed-Test-Only-2026!'
        registered=a.post('/api/auth/register',json={'full_name':'Recovery Tester','email':email,'password':old})
        self.assertEqual(registered.status_code,201,registered.text)
        uid=a.get('/api/auth/me').json()['id'];self.users.append(uid)
        self.assertEqual(b.post('/api/auth/login',json={'email':email,'password':old}).status_code,200)
        with backend.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT DISTINCT auth_method FROM public.auth_sessions WHERE user_id=:u'),{'u':uid}).scalar_one(),'password')
        with patch.dict('os.environ',{'SMTP_EMAIL':'mock@example.com','SMTP_APP_PASSWORD':'mock-only','FRONTEND_URL':'http://localhost:5173'}),patch('email_service.send_email') as send:
            unknown=a.post('/api/auth/forgot-password',json={'email':'absent-'+secrets.token_hex(8)+'@example.com'})
            send.assert_not_called()
            result=a.post('/api/auth/forgot-password',json={'email':email})
            self.assertEqual(result.json(),unknown.json())
            self.assertEqual(result.status_code,200,result.text)
            first_token=parse_qs(urlparse(send.call_args.args[2].split()[-1]).query)['token'][0]
            send.assert_called_once()
            a.post('/api/auth/forgot-password',json={'email':email})
            token=parse_qs(urlparse(send.call_args.args[2].split()[-1]).query)['token'][0]
        self.assertNotEqual(first_token,token)
        with backend.engine.connect() as conn:
            row=conn.execute(text('SELECT token_hash,expires_at FROM public.password_resets WHERE user_id=:u'),{'u':uid}).mappings().one()
            self.assertEqual(row['token_hash'],auth_routes.digest(token))
            self.assertNotEqual(row['token_hash'],token)
            self.assertLessEqual(row['expires_at']-datetime.now(timezone.utc),timedelta(minutes=30))
        self.assertEqual(a.post('/api/auth/reset-password',json={'token':first_token,'password':new}).status_code,400)
        self.assertEqual(a.post('/api/auth/reset-password',json={'token':token,'password':new}).status_code,200)
        self.assertEqual(a.get('/api/auth/me').status_code,401)
        self.assertEqual(b.get('/api/auth/me').status_code,401)
        self.assertEqual(a.post('/api/auth/reset-password',json={'token':token,'password':new}).status_code,400)
        self.assertEqual(a.post('/api/auth/login',json={'email':email,'password':old}).status_code,401)
        self.assertEqual(a.post('/api/auth/login',json={'email':email,'password':new}).status_code,200)
        expired=secrets.token_urlsafe(48)
        with backend.engine.begin() as conn:
            conn.execute(text('INSERT INTO public.password_resets VALUES(:h,:u,:e)'),{'h':auth_routes.digest(expired),'u':uid,'e':datetime.now(timezone.utc)-timedelta(minutes=1)})
        self.assertEqual(a.post('/api/auth/reset-password',json={'token':expired,'password':old}).status_code,400)
        self.assertEqual(TestClient(backend.app).post('/api/auth/forgot-password',json={'email':email}).status_code,403)


if __name__=='__main__':unittest.main()
