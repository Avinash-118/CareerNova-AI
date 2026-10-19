"""Conservative job identity: remove tracking parameters, retain requisition IDs."""
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING_KEYS={'fbclid','gclid','dclid','msclkid','mc_cid','mc_eid','referrer'}

def normalize(value):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',str(value or '')).casefold()))


def canonical_url(value):
    try:
        url=urlsplit(str(value or '').strip())
        if url.scheme.lower() not in ('http','https') or not url.hostname or url.username or url.password:return ''
        host=url.hostname.lower().removeprefix('www.')
        port=url.port
        if port and port not in (80,443):host+=f':{port}'
        query=sorted((key,val) for key,val in parse_qsl(url.query,keep_blank_values=True) if not key.lower().startswith('utm_') and key.lower() not in TRACKING_KEYS)
        path=url.path.rstrip('/') or '/'
        # A company homepage is not a job identifier.
        fragment=url.fragment if url.fragment.lower() not in {'top','apply','description','job-description'} else ''
        if path=='/' and not query and not fragment:return ''
        return urlunsplit(('https',host,path,urlencode(query),fragment))
    except ValueError:return ''


def exact_key(job):
    url=canonical_url(job.get('apply_url') or job.get('url'))
    title=normalize(job.get('title') or job.get('job_title'))
    company=normalize(job.get('company'))
    return (url,title,company) if url and title and company and company not in {'unknown','unknown company','company not listed'} else None


def similar_key(job):
    title=normalize(job.get('title') or job.get('job_title'))
    company=normalize(job.get('company'))
    location=normalize(job.get('location'))
    return (title,company,location) if title and company and location and company not in {'unknown','unknown company','company not listed'} else None


def deduplicate_jobs(jobs):
    groups={};result=[]
    for original in jobs:
        job=dict(original)
        key=exact_key(job)
        provenance={'id':str(job.get('id','')),'source':job.get('source_slug') or job.get('source') or 'Job feed','url':job.get('apply_url') or job.get('url') or ''}
        if key and key in groups:
            kept=groups[key]
            for listing in job.get('listings') or [provenance]:
                if listing not in kept['listings']:kept['listings'].append(listing)
            kept['duplicate_count']=len(kept['listings'])
            for field in ('description','employment_type','work_mode'):
                if not kept.get(field) and job.get(field):kept[field]=job[field]
        else:
            job['listings']=list(job.get('listings') or [provenance])
            job['duplicate_count']=len(job['listings'])
            result.append(job)
            if key:groups[key]=job
    similar={}
    for job in result:
        key=similar_key(job)
        if key:similar.setdefault(key,[]).append(job)
    for group in similar.values():
        for job in group:job['possible_duplicate_count']=len(group)-1
    return result


def tracked_match(job,tracked):
    ids={str(job.get('id') or job.get('job_id') or '')}|{str(p.get('id','')) for p in job.get('listings',[])}
    key=exact_key(job)
    for item in tracked:
        if str(item['job_id']) in ids or (key and key==exact_key(item)):
            return item
    return None


def annotate_tracking(jobs,user_id,connection):
    from sqlalchemy import text
    tracked=[dict(row) for row in connection.execute(text('SELECT id,job_id,job_title,company,location,apply_url,status FROM public.career_job_tracker WHERE user_id=:u'),{'u':str(user_id)}).mappings().all()]
    for job in jobs:
        item=tracked_match(job,tracked)
        if item:
            job['tracker_id']=item['id'];job['tracked_status']=item['status']
        else:
            job.pop('tracker_id',None);job.pop('tracked_status',None)
    return jobs
