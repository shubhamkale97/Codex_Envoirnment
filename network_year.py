"""Copyright year from HTTPS internet time, never the host wall clock."""
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import threading
import time
import urllib.request

CACHE = Path(os.environ.get('YEAR_CACHE_FILE', '/var/lib/leadgen/year.json'))
INDIA = timezone(timedelta(hours=5, minutes=30))
_lock = threading.Lock()
_checked = None
_last = {'year': 2026, 'source': 'initial', 'verified': False, 'timezone': 'Asia/Kolkata'}
try:
    saved = json.loads(CACHE.read_text())
    if isinstance(saved.get('year'), int) and 2026 <= saved['year'] <= 2200:
        _last.update(year=saved['year'], source='last-verified')
except (OSError, ValueError, TypeError):
    pass

def fetch_year():
    # No visitor or application data is sent to the time providers.
    sources = [
        ('timeapi.io', 'https://timeapi.io/api/time/current/zone?timeZone=Asia%2FKolkata'),
        ('cloudflare.com', 'https://www.cloudflare.com/cdn-cgi/trace'),
    ]
    for source, url in sources:
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Syncaxis-Leadgen/1.0', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(request, timeout=5) as response:
                text = response.read(65536).decode()
            if source == 'timeapi.io':
                year = json.loads(text)['year']
            else:
                trace = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
                year = datetime.fromtimestamp(float(trace['ts']), tz=INDIA).year
            if isinstance(year, int) and 2026 <= year <= 2200:
                return year, source
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            continue
    raise RuntimeError('Internet time providers unavailable')

def current_year():
    global _checked, _last
    with _lock:
        elapsed = None if _checked is None else time.monotonic() - _checked
        refresh_after = 3600 if _last['verified'] else 60
        if elapsed is not None and elapsed < refresh_after:
            return dict(_last)
        _checked = time.monotonic()
        try:
            year, source = fetch_year()
            # Keep the last verified year if a provider supplies an older cached value.
            if year < _last['year']:
                raise RuntimeError('Internet year regressed')
            _last = {'year': year, 'source': source, 'verified': True, 'timezone': 'Asia/Kolkata'}
            try:
                CACHE.parent.mkdir(parents=True, exist_ok=True)
                temporary = CACHE.with_suffix('.tmp')
                temporary.write_text(json.dumps({'year': year}))
                temporary.replace(CACHE)
            except OSError:
                pass
        except RuntimeError:
            _last = {**_last, 'verified': False, 'source': 'last-verified' if _last['source'] != 'initial' else 'initial'}
        return dict(_last)
