"""Run one durable alert/digest cycle or a long-running worker, separate from API workers."""
import json
import argparse
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from database import engine
from platform_routes import configure_platform, check_alerts
from live_jobs import get_source_status
from feature_schema import configure_features
from email_service import send_email, email_configured

log=logging.getLogger(__name__)

def enqueue(conn, uid, subject, body, key):
    conn.execute(text('INSERT INTO public.mail_outbox(user_id,subject,body,dedupe_key) VALUES(:u,:s,:b,:k) ON CONFLICT(dedupe_key) DO NOTHING'),{'u':uid,'s':subject,'b':body,'k':key})


def run_cycle(user_ids=None):
    # Session advisory lock prevents two workers from delivering the same cycle concurrently.
    with engine.connect() as lock:
        if not lock.execute(text('SELECT pg_try_advisory_lock(717938241)')).scalar_one():
            return {'status':'Already running'}
        run_id=None
        try:
            with engine.begin() as conn:
                run_id=conn.execute(text('INSERT INTO public.worker_runs DEFAULT VALUES RETURNING id')).scalar_one()
                users=conn.execute(text('SELECT DISTINCT user_id AS id FROM public.job_alert_rules WHERE enabled=TRUE')).mappings().all()
            if user_ids is not None:
                users=[u for u in users if u["id"] in user_ids]
            added=0
            for user in users:
                result=check_alerts(dict(user))
                added+=int(result['message'].split()[0])
            today=datetime.now(timezone.utc).date().isoformat()
            with engine.begin() as conn:
                opted=conn.execute(text('''SELECT u.id FROM public.users u JOIN public.notification_preferences p ON p.user_id=u.id
                    WHERE p.email_digest=TRUE AND u.email_verified=TRUE''')).scalars().all()
                if user_ids is not None:
                    opted=[uid for uid in opted if uid in user_ids]
                for uid in opted:
                    matches=conn.execute(text('''SELECT title,company FROM public.job_notifications
                        WHERE user_id=:u AND created_at>NOW()-INTERVAL '24 hours' ORDER BY id DESC LIMIT 20'''),{'u':uid}).mappings().all()
                    if matches:
                        body='New opportunities on CareerNova:\n\n'+'\n'.join(f"- {r['title']} — {r['company']}" for r in matches)
                        body+='\n\nOpen your CareerNova alert inbox. Turn off digests in notification preferences.'
                        enqueue(conn,uid,'Your daily CareerNova job digest',body,f'digest:{uid}:{today}')
                    reminders=conn.execute(text('''SELECT id,title,due_at FROM public.career_reminders
                        WHERE user_id=:u AND completed=FALSE AND due_at<=NOW()+INTERVAL '24 hours' AND due_at>NOW()-INTERVAL '7 days' '''),{'u':uid}).mappings().all()
                    for reminder in reminders:
                        enqueue(conn,uid,'CareerNova reminder: '+reminder['title'],f"{reminder['title']}\nDue: {reminder['due_at'].isoformat()}\nReview your CareerNova reminders.",f"reminder:{reminder['id']}")
            delivered=0
            if email_configured():
                with engine.connect() as conn:
                    ids=conn.execute(text("SELECT id,user_id FROM public.mail_outbox WHERE status IN ('Pending','Retry') AND next_attempt<=NOW() AND attempts<5 ORDER BY id LIMIT 50")).mappings().all()
                ids=[r["id"] for r in ids if user_ids is None or r["user_id"] in user_ids]
                for mail_id in ids:
                    # Row remains locked during SMTP. On crash delivery is at-least-once.
                    with engine.begin() as conn:
                        mail=conn.execute(text('''SELECT m.*,u.email,u.email_verified,COALESCE(p.email_digest,FALSE) AS opted
                            FROM public.mail_outbox m JOIN public.users u ON u.id=m.user_id
                            LEFT JOIN public.notification_preferences p ON p.user_id=u.id WHERE m.id=:id FOR UPDATE OF m'''),{'id':mail_id}).mappings().first()
                        if not mail or mail['status'] not in ('Pending','Retry'):continue
                        if mail['dedupe_key'].startswith('verify:') and mail['created_at']<datetime.now(timezone.utc)-timedelta(minutes=30):
                            conn.execute(text("UPDATE public.mail_outbox SET status='Expired' WHERE id=:id"),{'id':mail_id});continue
                        if not mail['dedupe_key'].startswith('verify:') and not (mail['email_verified'] and mail['opted']):
                            conn.execute(text("UPDATE public.mail_outbox SET status='Cancelled' WHERE id=:id"),{'id':mail_id});continue
                        try:
                            send_email(mail['email'],mail['subject'],mail['body'])
                            conn.execute(text("UPDATE public.mail_outbox SET status='Sent',sent_at=NOW(),attempts=attempts+1,last_error=NULL WHERE id=:id"),{'id':mail_id})
                            delivered+=1
                        except Exception:
                            conn.execute(text("""UPDATE public.mail_outbox SET attempts=attempts+1,
                                status=CASE WHEN attempts+1>=5 THEN 'Failed' ELSE 'Retry' END,
                                next_attempt=NOW()+INTERVAL '15 minutes',last_error='SMTP delivery failed' WHERE id=:id"""),{'id':mail_id})
            with engine.begin() as conn:
                conn.execute(text("UPDATE public.worker_runs SET status='Completed',finished_at=NOW(),detail=:d,sources=CAST(:sources AS JSONB) WHERE id=:id"),{'id':run_id,'d':f'{added} matches; {delivered} emails delivered','sources':json.dumps(get_source_status())})
                conn.execute(text('DELETE FROM public.auth_sessions WHERE expires_at<NOW()'))
                conn.execute(text('DELETE FROM public.password_resets WHERE expires_at<NOW()'))
                conn.execute(text('DELETE FROM public.oauth_flows WHERE expires_at<NOW()'))
            return {'status':'Completed','matches':added,'delivered':delivered,'run_id':run_id}
        except Exception:
            if run_id:
                with engine.begin() as conn:
                    conn.execute(text("UPDATE public.worker_runs SET status='Failed',finished_at=NOW(),detail='Cycle failed; inspect worker logs' WHERE id=:id"),{'id':run_id})
            log.error('CareerNova worker cycle failed')
            return {'status':'Failed'}
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(717938241)'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    configure_platform(engine);configure_features(engine)
    while True:
        print(run_cycle(),flush=True)
        if args.once:break
        time.sleep(max(60,int(os.getenv('ALERT_CHECK_SECONDS','900'))))
