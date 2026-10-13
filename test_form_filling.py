
from playwright.sync_api import sync_playwright

TEST_URL = "http://127.0.0.1:8765/test_application.html"


def fill_test_application():
    print("\nCareerNova AI - Form Filling Assistant")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=500
        )

        page = browser.new_page()

        try:
            page.goto(
                TEST_URL,
                wait_until="domcontentloaded",
                timeout=30000
            )

            print("Application page opened.")

            # Sample information only
            applicant = {
                "full_name": "Test Applicant",
                "email": "test@example.com",
                "phone": "5551234567",
                "experience": "2-3 years",
                "cover_letter": (
                    "I am interested in this position "
                    "and would like to learn more."
                )
            }

            page.locator("#full_name").fill(
                applicant["full_name"]
            )
            print("Full Name filled.")

            page.locator("#email").fill(
                applicant["email"]
            )
            print("Email filled.")

            page.locator("#phone").fill(
                applicant["phone"]
            )
            print("Phone Number filled.")

            page.locator("#experience").select_option(
                label=applicant["experience"]
            )
            print("Experience selected.")

            page.locator("#cover_letter").fill(
                applicant["cover_letter"]
            )
            print("Cover Letter filled.")

            print("\nApplication fields filled successfully.")
            print("Resume upload skipped for this test.")
            print("Application has NOT been submitted.")

            input(
                "\nReview the filled form in Chromium. "
                "Press Enter to close..."
            )

        finally:
            browser.close()


if __name__ == "__main__":
    fill_test_application()
