"""Local development only: one worker thread owns each Playwright session."""
import ipaddress
import socket
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Invalid application URL')
    # Public portals must not reach private addresses. Local test page is the only exception.
    if parsed.hostname in ('localhost', '127.0.0.1'):
        if parsed.port != 8765 or parsed.path != '/test_application.html':
            raise ValueError('Only the local sample application is allowed on localhost')
        return
    for item in socket.getaddrinfo(parsed.hostname, None):
        ip = ipaddress.ip_address(item[4][0])
        if not ip.is_global:
            raise ValueError('Private or reserved destinations are not allowed')


class ApplicationSession:
    def __init__(self, url):
        self.session_id = str(uuid.uuid4())
        self.url = url
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.playwright = self.browser = self.page = None
        self.fields = []
        self.index = 0
        self.answers = {}
        self.closed = False

    def run(self, method, *args):
        if self.closed:
            raise ValueError('Session is closed')
        return self.executor.submit(method, *args).result(timeout=90)

    def start(self):
        return self.run(self._start)

    def _start(self):
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.launch(headless=False)
            self.page = self.browser.new_page(accept_downloads=False)
            self.page.goto(self.url, wait_until='domcontentloaded', timeout=45000)
            self._detect()
            return {'session_id': self.session_id, 'total_questions': len(self.fields), 'current_index': self.index, 'completed': not self.fields}
        except Exception:
            self._cleanup()
            raise

    def _detect(self):
        self.fields = []
        controls = self.page.locator('input:not([type=hidden]), textarea, select')
        for i in range(controls.count()):
            field = controls.nth(i)
            if not field.is_visible() or not field.is_enabled():
                continue
            kind = (field.get_attribute('type') or 'text').lower()
            if kind in ('submit', 'button', 'reset', 'image'):
                continue
            tag = field.evaluate('(el) => el.tagName.toLowerCase()')
            label = field.evaluate('''el => [...(el.labels || [])].map(x => x.innerText.trim()).join(' ') || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('name') || 'Application question' ''')
            options = field.locator('option').all_text_contents() if tag == 'select' else []
            self.fields.append({'locator_index': i, 'label': label, 'type': kind, 'tag': tag, 'options': options, 'required': field.evaluate('(el) => el.required === true')})


    def autofill(self, profile):
        return self.run(self._autofill, profile)

    def _autofill(self, profile):
        """Fill only unambiguous saved fields; never submit or guess eligibility."""
        import re
        names = {
            'first name': 'first_name', 'given name': 'first_name',
            'last name': 'last_name', 'family name': 'last_name', 'surname': 'last_name',
            'email': 'email', 'email address': 'email', 'e mail': 'email',
            'phone': 'phone', 'phone number': 'phone', 'mobile number': 'phone',
            'current location': 'location',
            'linkedin': 'linkedin_url', 'linkedin url': 'linkedin_url', 'linkedin profile': 'linkedin_url',
            'github': 'github_url', 'github url': 'github_url',
            'portfolio': 'portfolio_url', 'portfolio url': 'portfolio_url',
            'university': 'university', 'university college': 'university',
            'degree': 'degree', 'years of experience': 'experience_years',
            'skills': 'skills', 'education details': 'education',
        }
        controls = self.page.locator('input:not([type=hidden]), textarea, select')
        filled = []
        for i, info in enumerate(self.fields):
            if i in self.answers:
                continue
            label = re.sub(r'[^a-z0-9]+', ' ', info['label'].lower()).strip()
            label = re.sub(r'\s+required$', '', label).strip()
            key = names.get(label)
            if not key or info['type'] in ('file', 'password', 'radio', 'checkbox'):
                continue
            value = str(profile.get(key) or '').strip()
            if not value:
                continue
            field = controls.nth(info['locator_index'])
            try:
                if info['tag'] == 'select':
                    choices = info.get('options', [])
                    match = next((x for x in choices if x.strip().casefold() == value.casefold()), None)
                    if match is None:
                        continue
                    field.select_option(label=match, timeout=3500)
                    value = match
                elif info['type'] in ('text', 'email', 'tel', 'url', 'search') or info['tag'] == 'textarea':
                    # Preserve any values that the employer form already contains.
                    existing = field.input_value(timeout=3500)
                    if existing.strip():
                        self.answers[i] = existing
                        continue
                    field.fill(value, timeout=3500)
                else:
                    continue
                self.answers[i] = value
                filled.append({'question': info['label'], 'value': value})
            except Exception as exc:
                print('Autofill field skipped:', info['label'], str(exc)[:180])
        self.index = 0
        self._advance_index()
        return {
            'autofilled_count': len(filled),
            'autofilled': filled,
            'remaining_count': len(self.fields) - len(self.answers),
            'next_question': self._question(),
            'submitted': False,
        }

    def _advance_index(self):
        while self.index < len(self.fields) and self.index in self.answers:
            self.index += 1

    def _question(self):
        self._advance_index()
        if self.index >= len(self.fields):
            return {'completed': True, 'message': 'All questions processed. Review the browser form; nothing has been submitted.'}
        return {'completed': False, 'question': self.fields[self.index], 'question_number': self.index + 1, 'total_questions': len(self.fields)}

    def question(self):
        return self.run(self._question)

    def _field(self):
        return self.page.locator('input:not([type=hidden]), textarea, select').nth(self.fields[self.index]['locator_index'])

    def answer(self, value):
        return self.run(self._answer, value)

    def _answer(self, value):
        if self.index >= len(self.fields):
            raise ValueError('No remaining questions')
        info = self.fields[self.index]
        field = self._field()
        if info['type'] == 'file':
            raise ValueError('Use the resume upload control or skip this field')
        if info['tag'] == 'select':
            field.select_option(label=value)
        elif info['type'] in ('checkbox', 'radio'):
            if value.lower() in ('yes', 'true', 'checked', 'on'):
                field.check()
            elif value.lower() in ('no', 'false', 'unchecked', 'off'):
                field.uncheck()
            else:
                raise ValueError('Please answer Yes or No')
        elif info['type'] in ('text', 'email', 'tel', 'url', 'number', 'date', 'search', 'password') or info['tag'] == 'textarea':
            field.fill(value)
        else:
            raise ValueError('This field requires manual entry in the browser')
        self.answers[self.index] = value
        self.index += 1
        self._advance_index()
        return {'message': 'Answer entered successfully', 'next_question': self._question()}

    def skip(self):
        return self.run(self._skip)

    def _skip(self):
        if self.index >= len(self.fields):
            raise ValueError('No remaining questions')
        if self.fields[self.index]['required']:
            raise ValueError('This field is required; enter an answer or handle it manually')
        self.answers[self.index] = '(skipped)'
        self.index += 1
        self._advance_index()
        return {'next_question': self._question()}

    def upload(self, filename, content):
        return self.run(self._upload, filename, content)

    def _upload(self, filename, content):
        if self.index >= len(self.fields) or self.fields[self.index]['type'] != 'file':
            raise ValueError('Current question is not a file upload')
        self._field().set_input_files({'name': filename, 'mimeType': 'application/pdf' if filename.lower().endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'buffer': content})
        self.answers[self.index] = f'Uploaded: {filename}'
        self.index += 1
        self._advance_index()
        return {'next_question': self._question()}

    def review(self):
        return {'session_id': self.session_id, 'answers': [{'question': field['label'], 'answer': self.answers.get(i, '(not answered)')} for i, field in enumerate(self.fields)], 'submitted': False}

    def _cleanup(self):
        try:
            if self.browser:
                self.browser.close()
        finally:
            if self.playwright:
                self.playwright.stop()

    def close(self):
        if not self.closed:
            try:
                self.executor.submit(self._cleanup).result(timeout=30)
            finally:
                self.closed = True
                self.executor.shutdown(wait=False)


sessions = {}
lock = threading.Lock()


def create_session(url):
    validate_url(url)
    session = ApplicationSession(url)
    try:
        result = session.start()
    except Exception:
        session.close()
        raise
    with lock:
        sessions[session.session_id] = session
    return result


def get_session(session_id):
    with lock:
        session = sessions.get(session_id)
    if session is None:
        raise KeyError('Session not found')
    return session


def close_session(session_id):
    with lock:
        session = sessions.pop(session_id, None)
    if session:
        session.close()
    return {'message': 'Session closed'}
