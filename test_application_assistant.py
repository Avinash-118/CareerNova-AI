import unittest
from unittest.mock import MagicMock
from application_field_mapping import profile_key
from application_session import ApplicationSession


class ApplicationAssistantTests(unittest.TestCase):
    def test_metadata_mapping(self):
        self.assertEqual(profile_key({'id': 'firstName'}), 'first_name')
        self.assertEqual(profile_key({'name': 'email_address'}), 'email')
        self.assertEqual(profile_key({'autocomplete': 'section-applicant given-name'}), 'first_name')
        self.assertIsNone(profile_key({'label': 'Years of Python experience'}))
        self.assertIsNone(profile_key({'label': 'Do you require sponsorship?'}))

    def session(self):
        session = ApplicationSession('https://example.com')
        self.addCleanup(session.executor.shutdown)
        session._status = lambda: {'stage': 'ready'}
        session.fields = [{'label': 'Your details', 'name': 'firstName', 'type': 'text', 'tag': 'input'}]
        control = MagicMock()
        session.field_locators = [control]
        return session, control

    def test_profile_fill_verified(self):
        session, control = self.session()
        control.input_value.side_effect = ['', '', 'Asha']
        result = session._autofill({'first_name': 'Asha'})
        control.fill.assert_called_once_with('Asha', timeout=3500)
        self.assertEqual(result['autofilled_count'], 1)
        self.assertTrue(result['next_question']['completed'])

    def test_rejected_fill_remains_question(self):
        session, control = self.session()
        control.input_value.return_value = ''
        result = session._autofill({'first_name': 'Asha'})
        self.assertEqual(result['autofilled_count'], 0)
        self.assertEqual(result['remaining_count'], 1)
        self.assertEqual(len(result['field_errors']), 1)

    def test_existing_answer_preserved(self):
        session, control = self.session()
        control.input_value.return_value = 'Existing'
        session._autofill({'first_name': 'Asha'})
        control.fill.assert_not_called()
        self.assertEqual(session.answers[0], 'Existing')

    def test_progress_revisit_and_recovery(self):
        session, control = self.session()
        session.answers[0] = 'Asha'
        session.answer_sources[0] = 'Saved candidate profile'
        self.assertEqual(session._progress()['filled'], 1)
        question = session.revisit(0)
        self.assertFalse(question['completed'])
        self.assertEqual(question['progress']['filled'], 0)
        session.page = MagicMock()
        session._detect = lambda: None
        control.input_value.return_value = 'Manually corrected'
        session._resume()
        self.assertEqual(session.answers[0], 'Manually corrected')
        self.assertEqual(session._progress()['fields'][0]['source'], 'Existing employer form value')

    def test_ashby_style_labels_fill_saved_profile(self):
        session, _ = self.session()
        labels = [('Name*','text'),('Email*','email'),('Linkedin URL*','text'),('Years of Experience*','number')]
        values = ['Asha Candidate','asha@example.com','https://linkedin.com/in/asha','3']
        session.fields = [{'label':label,'type':kind,'tag':'input'} for label,kind in labels]
        session.field_locators = []
        for value in values:
            control = MagicMock();control.input_value.side_effect = ['', '', value]
            session.field_locators.append(control)
        result = session._autofill({'first_name':'Asha','last_name':'Candidate','email':values[1],'linkedin_url':values[2],'experience_years':'3'})
        self.assertEqual(result['autofilled_count'],4)
        for control,value in zip(session.field_locators,values):
            control.fill.assert_called_once_with(value,timeout=3500)

    def test_overview_waits_and_application_is_ready(self):
        session, _ = self.session()
        session.page = MagicMock()
        session.page.locator.return_value.count.return_value = 0
        session.page.locator.return_value.inner_text.return_value = 'Overview - Search jobs'
        session.fields = [{'label':'Search','type':'search'}]
        self.assertEqual(ApplicationSession._status(session)['stage'],'waiting_for_form')
        session.page.locator.return_value.inner_text.return_value = 'Applicant Form'
        session.fields = [{'label':'Name*','type':'text'},{'label':'Email*','type':'email'}]
        self.assertEqual(ApplicationSession._status(session)['stage'],'ready')

    def test_scan_follows_employer_popup_and_rescans(self):
        session, _ = self.session()
        session.stage = 'waiting_for_form'
        session.page = MagicMock()
        popup = MagicMock();popup.is_closed.return_value = False
        session.page.context.pages = [popup]
        session._resume = MagicMock(return_value={'stage':'ready'})
        self.assertEqual(session.scan_for_form()['stage'],'ready')
        self.assertIs(session.page,popup)
        session._resume.assert_called_once()

    def test_plain_name_maps_to_full_name_but_company_name_does_not(self):
        self.assertEqual(profile_key({'label':'Name*'}),'__full_name__')
        self.assertEqual(profile_key({'label':'Name (required)'}),'__full_name__')
        self.assertIsNone(profile_key({'label':'Company name'}))


if __name__ == '__main__':
    unittest.main()
