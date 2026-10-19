
import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def email_configured():
    if os.getenv('EMAIL_PROVIDER','smtp').lower() == 'brevo':
        return bool(os.getenv('BREVO_API_KEY') and os.getenv('EMAIL_FROM'))
    return bool(os.getenv('SMTP_EMAIL') and os.getenv('SMTP_APP_PASSWORD'))


def send_email(to_email: str, subject: str, body: str):
    if os.getenv('EMAIL_PROVIDER','smtp').lower() == 'brevo':
        import requests
        if not email_configured():raise RuntimeError('Brevo API key and verified sender are required')
        response=requests.post('https://api.brevo.com/v3/smtp/email',
            headers={'api-key':os.environ['BREVO_API_KEY'],'Accept':'application/json'},
            json={'sender':{'email':os.environ['EMAIL_FROM'],'name':'CareerNova AI'},
                  'to':[{'email':to_email}],'subject':subject,'textContent':body},timeout=20)
        if not response.ok:
            # Do not include remote response bodies or keys in application logs.
            raise RuntimeError('Email provider rejected delivery')
        return True
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")
    if smtp_password and smtp_host.lower() == "smtp.gmail.com":
        smtp_password = "".join(smtp_password.split())

    if not smtp_email or not smtp_password:
        raise RuntimeError(
            "SMTP_EMAIL and SMTP_APP_PASSWORD must be set in .env"
        )

    message = EmailMessage()
    message["From"] = smtp_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()

    # Gmail supports implicit TLS on 465 and STARTTLS on 587.
    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20, context=context)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
    try:
        server.ehlo()
        if smtp_port != 465:
            server.starttls(context=context)
            server.ehlo()
        server.login(smtp_email, smtp_password)
        server.send_message(message)
    finally:
        try:
            server.quit()
        except (OSError, smtplib.SMTPException):
            server.close()

    return True


def send_verification_email(to_email: str, token: str):
    base_url = os.getenv(
        "APP_BASE_URL", "http://127.0.0.1:8000"
    ).rstrip("/")

    verification_link = (
        f"{base_url}/api/job-alerts/verify-email"
        f"?token={token}"
    )

    subject = "Verify your CareerNova AI email address"

    body = f"""Welcome to CareerNova AI!

Please verify your email address to activate
your job alert subscription.

Click the link below:

{verification_link}

This verification link expires in 30 minutes.

If you did not register for CareerNova AI,
you can ignore this email.

CareerNova AI Team
"""

    return send_email(to_email, subject, body)
