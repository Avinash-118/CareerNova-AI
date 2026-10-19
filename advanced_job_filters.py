"""Apply discovery filters before pagination; missing facts never count as matches."""
import re
import pandas as pd


def filter_frame(frame, company='', skills='', exclude='', seniority='', posted_days=0, sort='relevance'):
    frame = frame.copy()
    def column(name):
        return frame[name].fillna('').astype(str) if name in frame else pd.Series('', index=frame.index)
    if company.strip():
        frame = frame[column('company').str.contains(company.strip(), case=False, regex=False)]
    searchable = column('title') + ' ' + column('description') + ' ' + column('search_text')
    for skill in [x.strip() for x in skills.split(',') if x.strip()]:
        frame = frame[searchable.loc[frame.index].str.contains(skill, case=False, regex=False)]
    for word in [x.strip() for x in exclude.split(',') if x.strip()]:
        frame = frame[~searchable.loc[frame.index].str.contains(word, case=False, regex=False)]
    levels = {
        'entry': r'\b(?:junior|jr|entry[ -]level|graduate|intern|trainee)\b',
        'senior': r'\b(?:senior|sr)\b',
        'lead': r'\b(?:lead|principal|staff|manager|director|head|vp)\b',
    }
    if seniority in levels:
        frame = frame[column('title').str.contains(levels[seniority], case=False, regex=True)]
    if posted_days or sort == 'newest':
        dates = column('published_at')
        numeric = pd.to_numeric(dates, errors='coerce')
        parsed = pd.to_datetime(dates.where(numeric.isna()), errors='coerce', utc=True)
        millis = numeric > 100000000000
        parsed.loc[millis] = pd.to_datetime(numeric.loc[millis], unit='ms', errors='coerce', utc=True)
        seconds = numeric.notna() & ~millis
        parsed.loc[seconds] = pd.to_datetime(numeric.loc[seconds], unit='s', errors='coerce', utc=True)
        frame['_posted'] = parsed
        if posted_days:
            frame = frame[(frame['_posted'] >= pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=posted_days)) & (frame['_posted'] <= pd.Timestamp.now(tz='UTC'))]
        if sort == 'newest':
            frame = frame.sort_values('_posted', ascending=False, na_position='last', kind='stable')
        frame = frame.drop(columns='_posted')
    elif sort in ('title', 'company'):
        frame = frame.sort_values(sort, key=lambda s: s.astype(str).str.lower(), kind='stable')
    return frame
