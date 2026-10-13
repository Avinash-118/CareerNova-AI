
import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_email(to_email: str, subject: str, body: str):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")

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

    with smtplib.SMTP(
        smtp_host, smtp_port, timeout=20
    ) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(smtp_email, smtp_password)
        server.send_message(message)

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
