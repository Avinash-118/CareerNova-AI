import unittest
from datetime import datetime, timezone, timedelta
import pandas as pd
from advanced_job_filters import filter_frame


class AdvancedJobFilterTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        self.jobs = pd.DataFrame([
            {'title':'Junior Engineer','company':'Acme','description':'Python SQL','published_at':now.isoformat()},
            {'title':'Senior Engineer','company':'Beta','description':'Python Java','published_at':str(int((now-timedelta(days=20)).timestamp()*1000))},
            {'title':'Staff Engineer','company':'Acme','description':'Python SQL Java','published_at':''},
        ])

    def test_combined_literal_keywords(self):
        rows = filter_frame(self.jobs, company='acme', skills='Python, SQL', exclude='Java')
        self.assertEqual(list(rows.title), ['Junior Engineer'])
        self.assertTrue(filter_frame(self.jobs, skills='Python[').empty)

    def test_missing_dates_excluded_and_millis_supported(self):
        self.assertEqual(len(filter_frame(self.jobs, posted_days=7)), 1)
        self.assertEqual(len(filter_frame(self.jobs, posted_days=30)), 2)
        self.assertEqual(list(filter_frame(self.jobs, sort='newest').title), list(self.jobs.title))

    def test_seniority_and_sort(self):
        self.assertEqual(list(filter_frame(self.jobs, seniority='lead').title), ['Staff Engineer'])
        self.assertEqual(list(filter_frame(self.jobs, sort='company').company), ['Acme','Acme','Beta'])

    def test_absent_dates_and_empty_frame(self):
        self.assertTrue(filter_frame(self.jobs.drop(columns='published_at'), posted_days=1).empty)
        self.assertTrue(filter_frame(self.jobs, company='missing', posted_days=7).empty)


if __name__ == '__main__':
    unittest.main()
