"""Focused checks for conservative identity, saved filters and transactional history."""
import os
import secrets
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import text
from job_identity import canonical_url,deduplicate_jobs
import backend
import live_jobs_routes

class JobIdentityTests(unittest.TestCase):
    def test_tracking_removed_but_requisition_ids_and_fragments_retained(self):
        self.assertEqual(canonical_url('https://WWW.example.com/jobs?id=12&utm_source=feed#apply'),'https://example.com/jobs?id=12')
        self.assertNotEqual(canonical_url('https://example.com/jobs?id=12'),canonical_url('https://example.com/jobs?id=13'))
        self.assertNotEqual(canonical_url('https://example.com/#job/12'),canonical_url('https://example.com/#job/13'))
        self.assertEqual(canonical_url('https://example.com/'),'')
        self.assertEqual(canonical_url('javascript:alert(1)'),'')
    def test_clear_duplicates_combine_while_similar_requisitions_remain(self):
        base={'title':'Python Engineer','company':'Northstar','location':'Chicago'}
        jobs=[{**base,'id':'a','url':'https://example.com/jobs?id=12&utm_source=a','source':'A'},
              {**base,'id':'b','url':'https://example.com/jobs?utm_source=b&id=12','source':'B'},
              {**base,'id':'c','url':'https://example.com/jobs?id=13','source':'B'},
              {**base,'id':'d','url':'https://example.com/jobs?id=14','location':'Austin','source':'B'}]
        result=deduplicate_jobs(jobs)
        self.assertEqual(len(result),3)
        self.assertEqual(result[0]['duplicate_count'],2)
        self.assertEqual(result[0]['possible_duplicate_count'],1)
        self.assertEqual(result[2]['possible_duplicate_count'],0)
        self.assertEqual(len(deduplicate_jobs(result)),3)
        self.assertNotIn('listings',jobs[0])

class SearchHistoryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context=TestClient(backend.app);cls.context.__enter__();cls.users=[]
    @classmethod
    def tearDownClass(cls):
        with backend.engine.begin() as conn:
            for uid in cls.users:
                conn.execute(text('DELETE FROM public.career_job_tracker WHERE user_id=:u'),{'u':str(uid)})
                conn.execute(text('DELETE FROM public.users WHERE id=:u'),{'u':uid})
        cls.context.__exit__(None,None,None)
    def account(self):
        client=TestClient(backend.app,headers={'X-CareerNova-Client':'web'})
        email=f'cn-history-{secrets.token_hex(8)}@example.com'
        result=client.post('/api/auth/register',json={'full_name':'History Tester','email':email,'password':'History-Test-Only-2026!'})
        self.assertEqual(result.status_code,201,result.text)
        uid=client.get('/api/auth/me').json()['id'];self.users.append(uid)
        return client,uid
    def test_saved_search_crud_isolation_validation_and_export(self):
        a,_=self.account();b,_=self.account()
        filters={'source':'live','term':'Python','type':'full-time','mode':'remote','city':'Chicago','field':'Software Engineer'}
        result=a.post('/api/saved-searches',json={'name':'Remote engineering','filters':filters})
        self.assertEqual(result.status_code,201,result.text);sid=result.json()['id']
        self.assertEqual(a.get(f'/api/saved-searches/{sid}').json()['filters'],filters)
        self.assertEqual(b.get('/api/saved-searches').json()['searches'],[])
        self.assertEqual(b.get(f'/api/saved-searches/{sid}').status_code,404)
        self.assertEqual(b.patch(f'/api/saved-searches/{sid}',json={'name':'Steal','filters':filters}).status_code,404)
        self.assertEqual(b.delete(f'/api/saved-searches/{sid}').status_code,404)
        self.assertEqual(a.post('/api/saved-searches',json={'name':'   ','filters':filters}).status_code,422)
        self.assertEqual(a.post('/api/saved-searches',json={'name':'Wrong source','filters':{'source':'private'}}).status_code,422)
        self.assertEqual(a.patch(f'/api/saved-searches/{sid}',json={'name':'New name','filters':{**filters,'source':'historical'}}).status_code,200)
        self.assertEqual(a.get('/api/privacy/export').json()['saved_searches'][0]['name'],'New name')
        extended={**filters,'company':'Acme','skills':'Python, SQL','exclude':'Java','seniority':'entry','posted_days':7,'sort':'newest'}
        changed=a.patch(f'/api/saved-searches/{sid}',json={'name':'Advanced filters','filters':extended})
        self.assertEqual(changed.status_code,200,changed.text)
        self.assertEqual(a.get(f'/api/saved-searches/{sid}').json()['filters'],extended)
        self.assertEqual(a.post('/api/saved-searches',json={'name':'Bad sort','filters':{'sort':'unsafe'}}).status_code,422)
        self.assertEqual(a.delete(f'/api/saved-searches/{sid}').status_code,200)
        self.assertEqual(a.get('/api/saved-searches').json()['searches'],[])
    def test_duplicate_saves_personal_flags_and_history(self):
        a,uid=self.account();b,_=self.account()
        job={'job_id':'feed-a:12','job_title':'Python Engineer','company':'Northstar','location':'Chicago','apply_url':'https://example.com/jobs?id=12&utm_source=a'}
        first=a.post('/api/dashboard/save',json=job);self.assertEqual(first.status_code,201,first.text);tid=first.json()['id']
        duplicate=a.post('/api/dashboard/save',json={**job,'job_id':'feed-b:12','apply_url':'https://example.com/jobs?utm_source=b&id=12'})
        self.assertEqual(duplicate.json()['id'],tid);self.assertTrue(duplicate.json()['already_tracked'])
        spaced=a.post('/api/dashboard/save',json={**job,'job_id':'  '+job['job_id']+'  '})
        self.assertEqual(spaced.json()['id'],tid)
        second=a.post('/api/dashboard/save',json={**job,'job_id':'feed-b:13','apply_url':'https://example.com/jobs?id=13'})
        self.assertNotEqual(second.json()['id'],tid)
        a.patch(f'/api/dashboard/jobs/{tid}',json={'status':'Applied','notes':'Submitted on employer website.'})
        a.patch(f'/api/dashboard/jobs/{tid}',json={'status':'Applied','notes':'Submitted on employer website.'})
        history=a.get('/api/timeline',params={'tracker_id':tid});self.assertEqual(history.status_code,200,history.text)
        events=history.json()['events'];self.assertEqual(len(events),3)
        self.assertEqual({e['kind'] for e in events},{'saved','status','notes'})
        self.assertEqual(b.get('/api/timeline',params={'tracker_id':tid}).status_code,404)
        self.assertEqual(b.get('/api/timeline').json()['events'],[])
        stamp=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        manual={'tracker_id':tid,'kind':'Recruiter reply','title':'First interview invitation','body':'Recruiter requested availability.','occurred_at':stamp}
        result=a.post('/api/timeline',json=manual);self.assertEqual(result.status_code,201,result.text);eid=result.json()['id']
        self.assertEqual(b.post('/api/timeline',json=manual).status_code,404)
        self.assertEqual(b.delete(f'/api/timeline/{eid}').status_code,404)
        self.assertEqual(a.delete(f"/api/timeline/{events[0]['id']}").status_code,400)
        first_page=a.get('/api/timeline',params={'tracker_id':tid,'limit':2}).json()
        second_page=a.get('/api/timeline',params={'tracker_id':tid,'limit':2,'before':first_page['next_cursor']}).json()
        self.assertEqual(len(first_page['events'])+len(second_page['events']),4)
        self.assertFalse({e['id'] for e in first_page['events']}&{e['id'] for e in second_page['events']})
        feed=[{'id':'other-feed:12','title':'Python Engineer','company':'Northstar','location':'Chicago','employment_type':'full-time','description':'Python','url':'https://example.com/jobs?id=12&utm_source=other'}]
        with patch.object(live_jobs_routes,'fetch_live_jobs',return_value=feed):
            mine=a.get('/api/jobs/discover').json()['jobs'][0]
            theirs=b.get('/api/jobs/discover').json()['jobs'][0]
            self.assertEqual(mine['tracked_status'],'Applied');self.assertEqual(mine['tracker_id'],tid)
            self.assertNotIn('tracked_status',theirs);self.assertNotIn('tracked_status',feed[0])
        exported=a.get('/api/privacy/export').json();self.assertIn('application_events',exported)
        self.assertEqual(a.delete(f'/api/timeline/{eid}').status_code,200)
        self.assertEqual(a.delete(f'/api/dashboard/jobs/{tid}').status_code,200)
        with backend.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM public.application_events WHERE tracker_id=:id'),{'id':tid}).scalar_one(),0)

if __name__=='__main__':unittest.main(verbosity=2)
