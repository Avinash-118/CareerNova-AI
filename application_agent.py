
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def detect_application_fields(page):
    print("\n" + "=" * 60)
    print("CareerNova AI - Application Form Detection")
    print("=" * 60)

    fields = page.locator(
        "input, textarea, select"
    )

    total_fields = fields.count()
    detected_fields = []

    print(f"\nTotal form controls found: {total_fields}\n")

    for index in range(total_fields):
        field = fields.nth(index)

        try:
            if not field.is_visible():
                continue

            tag = field.evaluate(
                "(element) => element.tagName.toLowerCase()"
            )

            field_type = (
                field.get_attribute("type") or "text"
            ).lower()

            field_name = field.get_attribute("name") or ""
            field_id = field.get_attribute("id") or ""
            placeholder = (
                field.get_attribute("placeholder") or ""
            )
            aria_label = (
                field.get_attribute("aria-label") or ""
            )

            label = ""

            try:
                label = field.evaluate("""
                    element => {
                        const labels = element.labels;
                        if (labels && labels.length > 0) {
                            return Array.from(labels)
                                .map(label => label.innerText.trim())
                                .join(" ");
                        }
                        return "";
                    }
                """)
            except Exception:
                pass

            field_info = {
                "index": index + 1,
                "tag": tag,
                "type": field_type,
                "name": field_name,
                "id": field_id,
                "label": label,
                "placeholder": placeholder,
                "aria_label": aria_label,
                "required": field.get_attribute("required")
                is not None,
            }

            if tag == "select":
                try:
                    field_info["options"] = field.locator(
                        "option"
                    ).all_text_contents()
                except Exception:
                    field_info["options"] = []

            detected_fields.append(field_info)

            print(f"Field {index + 1}")
            print(f"  Tag: {tag}")
            print(f"  Type: {field_type}")
            print(f"  Name: {field_name}")
            print(f"  Label: {label}")
            print(f"  Placeholder: {placeholder}")
            print(f"  Required: {field_info['required']}")

            if tag == "select":
                print(
                    f"  Options: {field_info.get('options', [])}"
                )

            print("-" * 45)

        except Exception as error:
            print(
                f"Could not inspect field {index + 1}: "
                f"{error}"
            )

    print(
        f"\nSuccessfully detected "
        f"{len(detected_fields)} visible controls."
    )

    return detected_fields


def open_job_application(job_url):
    parsed = urlparse(job_url)

    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
    ):
        raise ValueError("Invalid application URL")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        try:
            page.goto(
                job_url,
                wait_until="domcontentloaded",
                timeout=45000
            )

            print("\nCareerNova AI Application Assistant")
            print("Job portal:", page.url)
            print("Page title:", page.title())

            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=10000
                )
            except PlaywrightTimeoutError:
                print(
                    "Page is still loading some resources."
                )

            print(
                "\nApplication portal opened successfully."
            )

            print(
                "Detecting application form fields..."
            )

            detected_fields = detect_application_fields(
                page
            )

            if not detected_fields:
                print(
                    "\nNo visible application fields found."
                )
                print(
                    "The portal may require clicking Apply, "
                    "logging in, or opening another page."
                )

            print(
                "\nNo information has been entered "
                "or submitted."
            )

            input(
                "\nPress Enter to close the browser..."
            )

            return detected_fields

        finally:
            browser.close()


if __name__ == "__main__":
    job_url = input(
        "Enter a job application URL: "
    ).strip()

    open_job_application(job_url)
