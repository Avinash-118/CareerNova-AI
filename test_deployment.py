import os
import unittest
from unittest.mock import patch,MagicMock
from configure_deployment import vercel_config
from deployment_config import validate_production,browser_assistant_enabled


class DeploymentTests(unittest.TestCase):
    def test_proxy_precedes_spa_and_preserves_same_origin_api(self):
        config=vercel_config('https://example-api.hf.space/')
        self.assertEqual(config['rewrites'][0],{'source':'/api/:path*','destination':'https://example-api.hf.space/api/:path*'})
        self.assertEqual(config['rewrites'][1]['destination'],'/index.html')
        for invalid in ('http://example.com','https://u:secret@example.com','https://example.com/path'):
            with self.assertRaises(ValueError):vercel_config(invalid)

    @patch.dict(os.environ,{'APP_ENV':'production'},clear=True)
    def test_cloud_requires_configuration_and_disables_desktop_browser(self):
        with self.assertRaises(RuntimeError):validate_production()
        self.assertFalse(browser_assistant_enabled())
        settings={'DATABASE_URL':'postgresql://unused','FRONTEND_URL':'https://example.vercel.app','PUBLIC_BASE_URL':'https://example.vercel.app','CORS_ORIGINS':'https://example.vercel.app','COOKIE_SECURE':'true'}
        with patch.dict(os.environ,settings):
            validate_production()
            with patch.dict(os.environ,{'CORS_ORIGINS':'*'}):
                with self.assertRaises(RuntimeError):validate_production()
            with patch.dict(os.environ,{'FRONTEND_URL':'http://localhost:5173'}):
                with self.assertRaises(RuntimeError):validate_production()

    @patch.dict(os.environ,{'EMAIL_PROVIDER':'brevo','BREVO_API_KEY':'test-only','EMAIL_FROM':'sender@example.com'})
    @patch('requests.post')
    def test_cloud_email_transport_and_sanitized_errors(self,post):
        from email_service import send_email,email_configured
        self.assertTrue(email_configured())
        post.return_value=MagicMock(ok=True)
        self.assertTrue(send_email('recipient@example.com','Test','Body'))
        self.assertEqual(post.call_args.args[0],'https://api.brevo.com/v3/smtp/email')
        self.assertEqual(post.call_args.kwargs['json']['textContent'],'Body')
        post.return_value.ok=False
        with self.assertRaisesRegex(RuntimeError,'Email provider rejected delivery'):
            send_email('recipient@example.com','Test','Body')


if __name__=='__main__':unittest.main()
