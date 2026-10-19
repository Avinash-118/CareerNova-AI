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
        self.answer_sources = {}
        self.evidence_context = {}
        self.field_errors = {}
        self.closed = False
        self.stage = "opening"

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
            try:
                self.page.locator('input:not([type=hidden]), textarea, select').first.wait_for(state='visible', timeout=4000)
            except Exception:
                pass
            self._detect()
            return {'session_id': self.session_id, **self._status()}
        except Exception:
            self._cleanup()
            raise

    def _status(self):
        """Prefer visible application fields over incidental login text."""
        try:
            password_visible = self.page.locator('input[type="password"]:visible').count() > 0
            body = (self.page.locator('body').inner_text(timeout=4000) or '')[:5000].lower()
            verification = any(x in body for x in (
                'enter verification code', 'verify your email', 'two-factor authentication',
                'enter your otp', 'enter the one-time code'))
            fillable = [f for f in self.fields if f['type'] not in (
                'password', 'hidden', 'checkbox', 'radio', 'file')]
            labels = ' '.join(f['label'].lower() for f in fillable)
            application_signals = any(x in labels for x in (
                'full name', 'first name', 'last name', 'email', 'resume',
                'phone', 'linkedin', 'preferred first name', 'name*')) or any(x in body for x in ('applicant form', 'application form'))
            registration_words = ('join ', 'sign up', 'create account', 'register', 'registration')
            registration = (any(x in body for x in registration_words)
                            and application_signals and not password_visible)
            auth_page = password_visible or verification
        except Exception:
            fillable, application_signals, registration, auth_page = [], False, False, False

        if auth_page:
            self.stage = 'waiting_for_login'
            message = 'Complete login or verification manually, then continue your application.'
        elif application_signals and fillable:
            self.stage = 'registration' if registration else 'ready'
            message = f'I found {len(self.fields)} visible fields. Nova can fill supported profile details.'
        elif not self.fields or not application_signals:
            self.stage = 'waiting_for_form'
            message = 'Open the Application tab or Apply form in the employer browser. Nova will check for the form automatically; you can also use Rescan current form.'
        else:
            self.stage = 'ready'
            message = f'I found {len(self.fields)} fields. Ready to inspect and fill supported details.'
        return {'stage': self.stage, 'message': message,
                'total_questions': len(self.fields), 'current_index': self.index,
                'completed': False, 'submitted': False}

    def resume(self):
        return self.run(self._resume)

    def _resume(self):
        # Recover only observable values from the same employer browser, never replay stale answers.
        try:
            self.page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception:
            pass
        self._detect()
        self.answers = {}
        self.answer_sources = {}
        self.evidence_context = {}
        self.field_errors = {}
        self.index = 0
        for i, info in enumerate(self.fields):
            if info['type'] in ('text', 'email', 'tel', 'url', 'number', 'date', 'search') or info['tag'] == 'textarea':
                try:
                    value = self.field_locators[i].input_value(timeout=2000)
                    if value.strip():
                        self.answers[i] = value
                        self.answer_sources[i] = 'Existing employer form value'
                except Exception:
                    self.field_errors[i] = 'Field changed. Rescan the employer form.'
        return self._status()

    def scan_for_form(self):
        def scan():
            if self.stage not in ('waiting_for_form', 'waiting_for_login', 'opening'):
                return self._status()
            # Employer Apply buttons may open another tab in the same assisted context.
            pages = [p for p in self.page.context.pages if not p.is_closed()]
            if pages:
                self.page = pages[-1]
            return self._resume()
        return self.run(scan)

    def _progress(self):
        rows = []
        for i, field in enumerate(self.fields):
            value = self.answers.get(i)
            state = ('skipped' if value == '(skipped)' else 'filled' if value is not None
                     else 'failed' if i in self.field_errors else 'manual' if field['type'] in ('file','password')
                     else 'unanswered')
            rows.append({'index':i, 'question':field['label'], 'state':state,
                         'source':self.answer_sources.get(i, ''), 'error':self.field_errors.get(i, '')})
        return {'fields':rows, 'filled':sum(r['state']=='filled' for r in rows), 'total':len(rows)}

    def revisit(self, index):
        def select():
            if index < 0 or index >= len(self.fields):
                raise ValueError('Field no longer available. Rescan the form.')
            self.answers.pop(index, None)
            self.answer_sources.pop(index, None)
            self.index = index
            return self._question()
        return self.run(select)

    def _detect(self):
        self.fields = []
        self.field_locators = []
        for frame in self.page.frames:
            controls = frame.locator('input:not([type=hidden]), textarea, select')
            for i in range(controls.count()):
                field = controls.nth(i)
                if not field.is_visible() or not field.is_enabled():
                    continue
                kind = (field.get_attribute('type') or 'text').lower()
                if kind in ('submit', 'button', 'reset', 'image'):
                    continue
                # Bind to the element, rather than a shifting position in the form.
                token = uuid.uuid4().hex
                field.evaluate('(el, token) => el.setAttribute("data-careernova-field", token)', token)
                stable = frame.locator(f'[data-careernova-field="{token}"]')
                metadata = field.evaluate("""el => ({
                    label: [...(el.labels || [])].map(x => x.innerText.trim()).join(' ') ||
                      (el.getAttribute('aria-labelledby') || '').split(/\s+/).map(id => el.ownerDocument.getElementById(id)?.textContent || '').join(' ').trim() ||
                      el.getAttribute('aria-label') ||
                      el.parentElement?.querySelector('label')?.innerText?.trim() ||
                      el.getAttribute('placeholder') || el.name || 'Application question',
                    name: el.name || '', id: el.id || '', autocomplete: el.autocomplete || '',
                    tag: el.tagName.toLowerCase(), required: el.required === true || el.getAttribute('aria-required') === 'true'
                })""")
                metadata.update(type=kind, options=field.locator('option').all_text_contents() if metadata['tag'] == 'select' else [])
                self.fields.append(metadata)
                self.field_locators.append(stable)


    def prepare_evidence(self, profile, memories, resume):
        from application_memory import evidence_for
        self.evidence_context = {i: evidence_for(field, profile, memories, resume)
                                 for i, field in enumerate(self.fields)}
        for i, e in self.evidence_context.items():
            if e['conflict']:
                self.answers.pop(i, None)
                self.answer_sources.pop(i, None)
        return [{'question': self.fields[i]['label'], **e} for i, e in self.evidence_context.items() if e['conflict']]

    def autofill(self, profile):
        return self.run(self._autofill, profile)

    def _autofill(self, profile):
        """Fill only unambiguous saved fields; never submit or guess eligibility."""
        status = self._status()
        if status['stage'] not in ('ready', 'registration'):
            return {'autofilled_count': 0, 'remaining_count': 0,
                    'next_question': None, **status}
        import re
        names = {
            'first name': 'first_name', 'given name': 'first_name',
            'last name': 'last_name', 'family name': 'last_name', 'surname': 'last_name',
            'preferred first name': 'first_name',
            'email': 'email', 'email address': 'email', 'e mail': 'email',
            'full name': '__full_name__', 'legal name': '__full_name__',
            'phone': 'phone', 'phone number': 'phone', 'mobile number': 'phone',
            'current location': 'location',
            'linkedin': 'linkedin_url', 'linkedin url': 'linkedin_url', 'linkedin profile': 'linkedin_url',
            'github': 'github_url', 'github url': 'github_url',
            'portfolio': 'portfolio_url', 'portfolio url': 'portfolio_url',
            'university': 'university', 'university college': 'university',
            'degree': 'degree', 'years of experience': 'experience_years',
            'skills': 'skills', 'education details': 'education',
            'first': 'first_name', 'last': 'last_name',
            'email address required': 'email', 'linkedin profile linkedin com in': 'linkedin_url',
        }
        filled = []
        failures = []
        for i, info in enumerate(self.fields):
            if i in self.answers or self.evidence_context.get(i, {}).get('conflict'):
                continue
            label = re.sub(r'[^a-z0-9]+', ' ', info['label'].lower()).strip()
            label = re.sub(r'\s+required$', '', label).strip()
            key = names.get(label)
            if not key:
                from application_field_mapping import profile_key
                key = profile_key(info)
            if not key:
                if label.startswith(('linkedin profile', 'linkedin url')):
                    key = 'linkedin_url'
                elif label.startswith('first name'):
                    key = 'first_name'
                elif label.startswith('last name'):
                    key = 'last_name'
                elif label.startswith('phone number'):
                    key = 'phone'
            if not key or info['type'] in ('file', 'password', 'radio', 'checkbox'):
                continue
            value = (' '.join(str(profile.get(k) or '').strip() for k in ('first_name', 'last_name')).strip()
                     if key == '__full_name__' else str(profile.get(key) or '').strip())
            if not value:
                continue
            field = self.field_locators[i]
            try:
                existing = field.input_value(timeout=3500)
                if existing.strip():
                    self.answers[i] = existing
                    self.answer_sources[i] = 'Existing employer form value'
                    continue
                if info['tag'] == 'select':
                    choices = info.get('options', [])
                    match = next((x for x in choices if x.strip().casefold() == value.casefold()), None)
                    if match is None:
                        continue
                    field.select_option(label=match, timeout=3500)
                    value = match
                elif info['type'] in ('text', 'email', 'tel', 'url', 'search', 'number') or info['tag'] == 'textarea':
                    # Preserve any values that the employer form already contains.
                    existing = field.input_value(timeout=3500)
                    if existing.strip():
                        self.answers[i] = existing
                        continue
                    field.fill(value, timeout=3500)
                else:
                    continue
                field.press('Tab', timeout=3500)
                actual = field.input_value(timeout=3500)
                if info['tag'] != 'select' and actual != value:
                    raise ValueError('The employer form did not retain the entered value')
                self.field_errors.pop(i, None)
                self.answers[i] = value
                self.answer_sources[i] = 'Saved candidate profile'
                filled.append({'question': info['label'], 'value': value})
            except Exception as exc:
                self.field_errors[i] = 'Could not verify this field. Retry or enter it manually.'
                failures.append({'question': info['label'], 'message': 'Could not verify this field. Answer it below or enter it in the employer browser.'})
        self.index = 0
        self._advance_index()
        return {
            'autofilled_count': len(filled),
            'autofilled': filled,
            'field_errors': failures,
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
            return {'progress':self._progress(), 'completed': bool(self.fields), 'message': 'All detected questions processed. Review the browser form; nothing has been submitted.'}
        return {'progress':self._progress(), 'completed': False, 'question': {**self.fields[self.index], **self.evidence_context.get(self.index, {})}, 'question_number': self.index + 1, 'total_questions': len(self.fields)}

    def question(self):
        return self.run(self._question)

    def _field(self):
        return self.field_locators[self.index]

    def answer(self, value):
        return self.run(self._answer, value)

    def _answer(self, value):
        if self.index >= len(self.fields):
            raise ValueError('No remaining questions')
        info = self.fields[self.index]
        field = self._field()
        if info['type'] == 'password':
            raise ValueError('Enter passwords manually in the employer browser')
        if info['type'] == 'file':
            raise ValueError('Use the resume upload control or skip this field')
        if info['tag'] == 'select':
            match = next((x for x in info['options'] if x.strip().casefold() == value.strip().casefold()), None)
            if match is None:
                raise ValueError('Choose one of the displayed options')
            field.select_option(label=match)
        elif info['type'] in ('checkbox', 'radio'):
            if value.lower() in ('yes', 'true', 'checked', 'on'):
                field.check()
            elif value.lower() in ('no', 'false', 'unchecked', 'off'):
                if info['type'] == 'radio':
                    raise ValueError('Select the radio option you want in the employer browser')
                field.uncheck()
            else:
                raise ValueError('Please answer Yes or No')
        elif info['type'] in ('text', 'email', 'tel', 'url', 'number', 'date', 'search') or info['tag'] == 'textarea':
            field.fill(value)
            field.press('Tab')
            if field.input_value() != value:
                raise ValueError('The form did not retain the answer. Please retry or enter it manually.')
        else:
            raise ValueError('This field requires manual entry in the browser')
        self.field_errors.pop(self.index, None)
        self.answers[self.index] = value
        self.answer_sources[self.index] = 'Confirmed answer'
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
        return {'session_id': self.session_id, 'answers': [{'question': field['label'], 'answer': self.answers.get(i, '(not answered)'), 'source': self.answer_sources.get(i, 'Manual / not entered'), 'evidence': self.evidence_context.get(i, {}).get('evidence', [])} for i, field in enumerate(self.fields)], 'submitted': False}

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
