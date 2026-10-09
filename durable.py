"""Durable owner-scoped task ledger. Reserve before provider calls; never replay them."""
import contextlib
import datetime
import hashlib
import json
import os
import sqlite3
import time
import uuid

class StorageUnavailable(RuntimeError): pass
class RequestConflict(ValueError): pass
class QuotaExceeded(RuntimeError): pass

@contextlib.contextmanager
def connection():
    url = os.environ.get('DATABASE_URL', '')
    if url:
        if not url.startswith(('postgresql://', 'postgres://')):
            raise StorageUnavailable('DATABASE_URL must be a PostgreSQL connection string.')
        try:
            import psycopg
            conn = psycopg.connect(url, connect_timeout=5, sslmode="require")
        except Exception:
            raise StorageUnavailable('Persistent PostgreSQL storage is unavailable.') from None
        postgres = True
    else:
        path = os.environ.get('DEZZY_DATABASE_PATH', '')
        if os.environ.get('VERCEL') or not path or not os.path.isabs(path) or path.startswith('/tmp/'):
            raise StorageUnavailable('Configure persistent PostgreSQL storage before starting tasks on Vercel.')
        conn = sqlite3.connect(path, timeout=5)
        postgres = False
    def execute(sql, params=()):
        return conn.execute(sql.replace('?', '%s') if postgres else sql, params)
    try:
        if not postgres: conn.execute('BEGIN IMMEDIATE')
        execute('CREATE TABLE IF NOT EXISTS dezzy_jobs (owner TEXT NOT NULL, id TEXT NOT NULL, state TEXT NOT NULL, updated TEXT NOT NULL, PRIMARY KEY(owner,id))')
        execute('CREATE TABLE IF NOT EXISTS dezzy_requests (owner TEXT NOT NULL, id TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL, response TEXT, day TEXT NOT NULL, PRIMARY KEY(owner,id))')
        yield execute, postgres
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally: conn.close()

def lock(execute, postgres, owner):
    if postgres: execute('SELECT pg_advisory_xact_lock(hashtext(?))', (owner,))

def history(owner):
    with connection() as (execute, postgres):
        rows = execute('SELECT state FROM dezzy_jobs WHERE owner=? ORDER BY updated DESC LIMIT 30', (owner,)).fetchall()
        return [json.loads(row[0]) for row in rows]

def step(owner, data, advance):
    request_id = data.get('request_id')
    try:
        if not isinstance(request_id, str): raise ValueError()
        uuid.UUID(request_id)
    except (ValueError, AttributeError):
        raise ValueError('A valid request_id is required.') from None
    if data.get('state'):
        raise ValueError('Signed-state continuation is disabled; use an owned job_id.')
    job_id = data.get('job_id')
    if job_id is not None and not isinstance(job_id, str): raise ValueError('Invalid job_id.')
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    with connection() as (execute, postgres):
        lock(execute, postgres, owner)
        existing = execute('SELECT fingerprint,status,response FROM dezzy_requests WHERE owner=? AND id=?', (owner, request_id)).fetchone()
        if existing:
            if existing[0] != fingerprint: raise RequestConflict('Request ID was reused with different input.')
            if existing[1] != 'completed': raise RequestConflict('Prior request outcome is uncertain. It will not be repeated automatically.')
            return json.loads(existing[2])
        if os.environ.get('DEZZY_ALLOW_PAID_AI') != 'true':
            raise QuotaExceeded('Paid AI is disabled. Offline games and saved reports remain available.')
        try:
            daily = int(os.environ.get('DEZZY_DAILY_REQUEST_LIMIT', '0'))
            lifetime = int(os.environ.get('DEZZY_TOTAL_REQUEST_LIMIT', '0'))
        except ValueError: raise QuotaExceeded('Invalid request quota configuration.') from None
        if daily <= 0 or lifetime <= 0: raise QuotaExceeded('Explicit daily and total request limits are required.')
        used = execute('SELECT COUNT(*) FROM dezzy_requests WHERE owner=? AND day=?', (owner,today)).fetchone()[0]
        total = execute('SELECT COUNT(*) FROM dezzy_requests WHERE owner=?', (owner,)).fetchone()[0]
        if used >= daily or total >= lifetime: raise QuotaExceeded('Request allowance exhausted. No provider call was made.')
        if execute("SELECT id FROM dezzy_requests WHERE owner=? AND status='processing'", (owner,)).fetchone():
            raise RequestConflict('A prior request is running or uncertain. Resolve it before more paid work.')
        if job_id:
            row = execute('SELECT state FROM dezzy_jobs WHERE owner=? AND id=?', (owner,job_id)).fetchone()
            if not row: raise ValueError('Owned task not found.')
            saved = json.loads(row[0])
            if time.time() - saved['job']['created'] > 86400: raise ValueError('Task expired. Start a new task.')
            if saved['job']['status'] != 'running': raise ValueError('This task has stopped. Start a new task.')
            body = {'state': saved['state']}
        else:
            body = {'task':data.get('task'), 'mode':data.get('mode')}
            if not isinstance(body['task'],str) or not 1 <= len(body['task'].strip()) <= 8000 or body['mode'] not in ('research','draft','code'):
                raise ValueError('Enter a task and select a valid deliverable.')
        execute("INSERT INTO dezzy_requests(owner,id,fingerprint,status,day) VALUES(?,?,?,'processing',?)", (owner,request_id,fingerprint,today))
    # Reservation is committed before I/O. A crash leaves an uncertain entry,
    # preventing an automatic retry/new call; it is never refunded blindly.
    import core
    reservation = core.paid_request_reservation.set(True)
    try: result = advance(body)
    finally: core.paid_request_reservation.reset(reservation)
    with connection() as (execute, postgres):
        lock(execute, postgres, owner)
        execute('INSERT INTO dezzy_jobs(owner,id,state,updated) VALUES(?,?,?,?) ON CONFLICT(owner,id) DO UPDATE SET state=excluded.state,updated=excluded.updated', (owner,result['job']['id'],json.dumps(result),datetime.datetime.now(datetime.timezone.utc).isoformat()))
        execute("UPDATE dezzy_requests SET status='completed',response=? WHERE owner=? AND id=?", (json.dumps(result),owner,request_id))
    return result
