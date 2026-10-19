"""Transactional history helpers. Call on the same connection as the mutation."""
from sqlalchemy import text

def record_event(conn,user_id,tracker_id,kind,title,body='',occurred_at=None,event_key=None):
    return conn.execute(text('''INSERT INTO public.application_events
        (user_id,tracker_id,kind,title,body,occurred_at,event_key)
        VALUES(:u,:t,:k,:title,:b,COALESCE(:at,NOW()),:key)
        ON CONFLICT(tracker_id,event_key) DO NOTHING RETURNING id'''),
        {'u':user_id,'t':tracker_id,'k':kind,'title':title,'b':body,'at':occurred_at,'key':event_key}).scalar_one_or_none()
