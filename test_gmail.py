
import os
import ssl
import smtplib
from dotenv import load_dotenv

load_dotenv(override=True)

email = os.getenv("SMTP_EMAIL", "").strip()
password = os.getenv("SMTP_APP_PASSWORD", "").replace(" ", "").strip()

try:
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=30,
        context=context
    ) as server:

        server.ehlo()

        print("SSL connection successful")
        print("Attempting Gmail authentication...")

        server.login(
            email,
            password,
            initial_response_ok=False
        )

        print("GMAIL LOGIN SUCCESSFUL!")

except smtplib.SMTPAuthenticationError as exc:
    print("Gmail rejected authentication.")
    print("SMTP status:", exc.smtp_code)

except smtplib.SMTPServerDisconnected:
    print("Gmail disconnected during authentication.")

except Exception as exc:
    print("Error type:", type(exc).__name__)
    print("Error:", exc)
