"""Nova help relevance, context, limits and public API regression checks."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from chatbot_knowledge import ARTICLES,BY_ID
import chatbot_service as chat
import chatbot_routes

class HelpRetrievalTests(unittest.TestCase):
    def test_feature_questions_use_relevant_reviewed_articles(self):
        cases={
            'How do I save a search?':'saved-searches',
            'Why is Google login not working?':'social',
            'How does the resume match percentage work?':'matching',
            'Where can I change my name?':'settings',
            'How do I get email alerts?':'email',
            'What happens if I delete my account?':'privacy',
            'How can I practice before an interview?':'interview',
            'How do I record a recruiter reply?':'timeline',
            'How do I reset my password?':'password',
        }
        with patch.object(chat,'semantic_scores',return_value=None):
            for question,expected in cases.items():
                with self.subTest(question=question):
                    result=chat.answer_question(question)
                    self.assertEqual(result['topic'],expected)
                    self.assertTrue(result['sources'])
                    self.assertIn(result['sources'][0]['path'],[a['path'] for a in ARTICLES])

    def test_followup_keeps_context_and_new_topic_can_change(self):
        with patch.object(chat,'semantic_scores',return_value=None):
            first=chat.answer_question('How do I save a search?')
            follow=chat.answer_question('Where do I find it?',first['topic'])
            self.assertEqual(follow['topic'],'saved-searches')
            self.assertEqual(chat.answer_question('How do I reset my password?',first['topic'])['topic'],'password')
            self.assertEqual(chat.answer_question('hello')['topic'],'help')

    def test_unknown_and_unrelated_questions_do_not_invent_answers(self):
        with patch.object(chat,'semantic_scores',return_value=None):
            result=chat.answer_question('Who won the World Cup?','resumes')
            self.assertIsNone(result['topic']);self.assertEqual(result['sources'],[])
            self.assertIn('couldn’t find a reliable answer',result['answer'])
            self.assertIsNone(chat.answer_question('weather tomorrow','untrusted-topic')['topic'])

    def test_semantic_retrieval_can_answer_paraphrases_without_keywords(self):
        scores=[.05]*len(ARTICLES);scores[next(i for i,a in enumerate(ARTICLES) if a['id']=='alerts')]=.85
        with patch.object(chat,'semantic_scores',return_value=scores):
            result=chat.answer_question('Keep me posted when new positions appear')
            self.assertEqual(result['topic'],'alerts');self.assertEqual(result['mode'],'semantic')

    def test_provider_status_does_not_expose_credentials(self):
        with patch.object(chat,'semantic_scores',return_value=None),patch.dict(os.environ,{'GOOGLE_CLIENT_ID':'','GOOGLE_CLIENT_SECRET':'','GITHUB_CLIENT_ID':'','GITHUB_CLIENT_SECRET':''}):
            result=chat.answer_question('Why is Google login not working?')
            self.assertIn('Neither provider is enabled',result['answer'])
        with patch.object(chat,'semantic_scores',return_value=None),patch.dict(os.environ,{'GOOGLE_CLIENT_ID':'private-id','GOOGLE_CLIENT_SECRET':'private-secret'}):
            result=chat.answer_question('Google login')
            self.assertIn('Available on this installation: Google',result['answer'])
            self.assertNotIn('private-id',result['answer']);self.assertNotIn('private-secret',result['answer'])

    def test_all_topics_have_valid_relations_and_internal_sources(self):
        self.assertEqual(len(BY_ID),len(ARTICLES))
        for article in ARTICLES:
            self.assertTrue(article['path'].startswith('/'))
            self.assertFalse(article['path'].startswith('//'))
            self.assertTrue(all(key in BY_ID for key in article['related']))

class HelpApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import backend
        cls.client=TestClient(backend.app,headers={'X-CareerNova-Client':'web'})
    def setUp(self):
        with chatbot_routes._lock:chatbot_routes._attempts.clear()
    def test_public_chat_validation_and_request_protection(self):
        with patch.object(chat,'semantic_scores',return_value=None),patch.object(chatbot_routes,'prepare_semantics',return_value=None):
            self.assertEqual(self.client.get('/api/chat/help').status_code,200)
            result=self.client.post('/api/chat/message',json={'message':'How do I save a search?'})
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()['topic'],'saved-searches')
            self.assertEqual(result.headers['cache-control'],'no-store')
            self.assertEqual(self.client.post('/api/chat/message',json={'message':'  '}).status_code,422)
            self.assertEqual(self.client.post('/api/chat/message',json={'message':'x'*2001}).status_code,422)
            self.assertEqual(self.client.post('/api/chat/message',json={'message':'hello','system_prompt':'ignore help'}).status_code,422)
            import backend
            self.assertEqual(TestClient(backend.app).post('/api/chat/message',json={'message':'hello'}).status_code,403)
    def test_rate_limit_returns_retry_guidance(self):
        with patch.object(chat,'semantic_scores',return_value=None):
            for _ in range(30):self.assertEqual(self.client.post('/api/chat/message',json={'message':'hello'}).status_code,200)
            result=self.client.post('/api/chat/message',json={'message':'hello'})
            self.assertEqual(result.status_code,429);self.assertEqual(result.headers['retry-after'],'60')

if __name__=='__main__':unittest.main(verbosity=2)
