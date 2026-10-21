import unittest
from unittest.mock import patch
from fastapi import HTTPException
import resume_job_matching as matching


class ResumeMatchingTests(unittest.TestCase):
    @patch.object(matching.INDEX_PATH.__class__, 'is_file', return_value=False)
    @patch.object(matching, 'fetch_live_jobs')
    def test_live_ranking_and_no_resume_sent_to_feed(self, feed, exists):
        feed.return_value = [
            {'id':'weak','title':'Engineer','description':'Python SQL Docker'},
            {'id':'strong','title':'Data Analyst','description':'Python SQL'},
            {'id':'unrelated','title':'Chef','description':'Kitchen catering cooking'}]
        jobs = matching.match_resume_jobs('Data Analyst Python SQL', 1)
        self.assertEqual([j['id'] for j in jobs], ['strong'])
        self.assertEqual(jobs[0]['matching_method'], 'live_keywords')
        self.assertIsNone(jobs[0]['faiss_score'])
        feed.assert_called_once_with()
        self.assertNotIn('matching_method', feed.return_value[1])

    @patch.object(matching.INDEX_PATH.__class__, 'is_file', return_value=True)
    @patch.object(matching, 'semantic_search', return_value=[{'description':'Python','faiss_score':0.8}])
    @patch.object(matching, 'fetch_live_jobs')
    def test_existing_semantic_path_is_preserved(self, feed, search, exists):
        jobs = matching.match_resume_jobs('Python', 3)
        search.assert_called_once_with('Python', 3)
        feed.assert_not_called()
        self.assertEqual(jobs[0]['faiss_score'], 0.8)

    @patch.object(matching.INDEX_PATH.__class__, 'is_file', return_value=False)
    @patch.object(matching, 'fetch_live_jobs', return_value=[])
    def test_feed_outage_is_reported(self, feed, exists):
        with self.assertRaises(HTTPException) as error:
            matching.match_resume_jobs('Python')
        self.assertEqual(error.exception.status_code, 503)


if __name__ == '__main__':
    unittest.main()
