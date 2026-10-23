import unittest
from unittest.mock import patch
import time
import live_jobs as feeds


class FreeFeedsTests(unittest.TestCase):
    def setUp(self):
        feeds._source_cache.clear()

    @patch.object(feeds,'get_json')
    def test_himalayas_pagination_expiry_and_original_application_link(self,get):
        item={'guid':'one','title':'Analyst','companyName':'Example','applicationLink':'https://example.com/apply?ref=himalayas','locationRestrictions':['United States'],'pubDate':1700000000,'expiryDate':time.time()+500,'description':'SQL'}
        expired={**item,'guid':'closed','expiryDate':1}
        get.side_effect=[{'jobs':[item,expired],'nextCursor':'second'},{'jobs':[],'nextCursor':None}]
        jobs=feeds.fetch_himalayas()
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['url'],item['applicationLink'])
        self.assertEqual(jobs[0]['work_mode'],'Remote')
        self.assertEqual(jobs[0]['source_url'],'https://himalayas.app')
        self.assertEqual(get.call_args.args[1]['cursor'],'second')

    @patch.object(feeds,'get_json',return_value={'data':[{'slug':'one','title':'Engineer','company_name':'Example','remote':True,'job_types':['Full-time'],'created_at':1700000000,'url':'https://www.arbeitnow.com/jobs/one'}]})
    def test_arbeitnow_normalization(self,get):
        job=feeds.fetch_arbeitnow()[0]
        self.assertEqual(job['company'],'Example')
        self.assertEqual(job['work_mode'],'Remote')
        self.assertIn('T',job['published_at'])

    def test_daily_cache_and_expiry_on_cached_reads(self):
        calls=[]
        def fetch():calls.append(1);return [{'id':'one','expires_at':feeds.iso_date(time.time()+50)}]
        self.assertEqual(len(feeds.daily_feed('Test',fetch)),1)
        self.assertEqual(len(feeds.daily_feed('Test',fetch)),1)
        self.assertEqual(len(calls),1)
        with patch.object(feeds.time,'time',return_value=time.time()+100):
            self.assertEqual(feeds.daily_feed('Test',fetch),[])


if __name__=='__main__':unittest.main()
