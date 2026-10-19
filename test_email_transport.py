import os
import smtplib
import unittest
from unittest.mock import patch

from email_service import send_email


class EmailTransportTests(unittest.TestCase):
    def send(self, port):
        with patch.dict(os.environ, {
            'SMTP_HOST': 'smtp.gmail.com', 'SMTP_PORT': str(port),
            'SMTP_EMAIL': 'sender@example.com',
            'SMTP_APP_PASSWORD': 'abcd efgh ijkl mnop',
        }):
            return send_email('recipient@example.com', 'Test', 'Body')

    @patch('email_service.smtplib.SMTP')
    def test_starttls_and_grouped_password(self, smtp):
        self.assertTrue(self.send(587))
        server = smtp.return_value
        server.starttls.assert_called_once()
        server.login.assert_called_once_with('sender@example.com', 'abcdefghijklmnop')
        server.send_message.assert_called_once()
        server.quit.assert_called_once()

    @patch('email_service.smtplib.SMTP_SSL')
    def test_implicit_tls(self, smtp):
        self.assertTrue(self.send(465))
        smtp.return_value.starttls.assert_not_called()
        smtp.return_value.send_message.assert_called_once()

    @patch('email_service.smtplib.SMTP')
    def test_failure_closes_connection_and_propagates(self, smtp):
        server = smtp.return_value
        server.login.side_effect = smtplib.SMTPAuthenticationError(535, b'failed')
        server.quit.side_effect = smtplib.SMTPServerDisconnected()
        with self.assertRaises(smtplib.SMTPAuthenticationError):
            self.send(587)
        server.close.assert_called_once()
        server.send_message.assert_not_called()


if __name__ == '__main__':
    unittest.main()
