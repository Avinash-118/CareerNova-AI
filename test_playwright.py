
from playwright.sync_api import sync_playwright

def test_browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        page.goto(
            "https://example.com",
            wait_until="domcontentloaded"
        )

        print("Browser opened successfully!")
        print("Page title:", page.title())

        page.wait_for_timeout(3000)

        browser.close()

if __name__ == "__main__":
    test_browser()
