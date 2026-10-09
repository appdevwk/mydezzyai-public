import json, os, pathlib, tempfile, threading, unittest, uuid
from unittest.mock import patch
import durable
import core
from api import index
from test_web import fake, ENV

class DurableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=pathlib.Path.cwd())
        self.env = patch.dict(os.environ, {**ENV, 'VERCEL':'', 'DATABASE_URL':'', 'DEZZY_DATABASE_PATH':self.temp.name+'/jobs.db', 'DEZZY_ALLOW_PAID_AI':'true','DEZZY_DAILY_REQUEST_LIMIT':'50','DEZZY_TOTAL_REQUEST_LIMIT':'50'})
        self.env.start(); self.calls=0
    def tearDown(self): self.env.stop();self.temp.cleanup()
    def advance(self, body):
        def counted(*args,**kwargs): self.calls+=1;return fake(*args,**kwargs)
        return index.advance(body,counted)
    def initial(self):return {'request_id':str(uuid.uuid4()),'task':'Saved task','mode':'draft'}
    def test_direct_provider_bypass_is_blocked(self):
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(RuntimeError):core.api_call('instruction','prompt')
            network.assert_not_called()

    def test_replay_and_owner_history(self):
        body=self.initial();a=durable.step('larry',body,self.advance);b=durable.step('larry',body,self.advance)
        self.assertEqual(a,b);self.assertEqual(self.calls,1)
        self.assertEqual(durable.history('larry')[0]['job']['id'],a['job']['id']);self.assertEqual(durable.history('other'),[])
        with self.assertRaises(ValueError):durable.step('other',{'request_id':str(uuid.uuid4()),'job_id':a['job']['id']},self.advance)
        with self.assertRaises(durable.RequestConflict):durable.step('larry',{**body,'task':'changed'},self.advance)
        with self.assertRaises(ValueError):durable.step('larry',{'request_id':str(uuid.uuid4()),'state':a['state']},self.advance)
        self.assertEqual(self.calls,1)
    def test_complete_seven_steps_and_terminal_rejection(self):
        response=durable.step('larry',self.initial(),self.advance)
        for _ in range(6):response=durable.step('larry',{'request_id':str(uuid.uuid4()),'job_id':response['job']['id']},self.advance)
        self.assertEqual(self.calls,7);self.assertEqual(response['job']['status'],'completed')
        with self.assertRaises(ValueError):durable.step('larry',{'request_id':str(uuid.uuid4()),'job_id':response['job']['id']},self.advance)
        self.assertEqual(durable.history('larry')[0],response)
    def test_disabled_and_quotas_fail_without_calls(self):
        with patch.dict(os.environ,{'DEZZY_ALLOW_PAID_AI':'false'}):
            with self.assertRaises(durable.QuotaExceeded):durable.step('larry',self.initial(),self.advance)
        with patch.dict(os.environ,{'DEZZY_DAILY_REQUEST_LIMIT':'0'}):
            with self.assertRaises(durable.QuotaExceeded):durable.step('larry',self.initial(),self.advance)
        with patch.dict(os.environ,{'DEZZY_TOTAL_REQUEST_LIMIT':'1'}):
            durable.step('larry',self.initial(),self.advance)
            with self.assertRaises(durable.QuotaExceeded):durable.step('larry',self.initial(),self.advance)
        self.assertEqual(self.calls,1)
    def test_uncertain_reservation_blocks_retries(self):
        body=self.initial()
        def crash(_):self.calls+=1;raise RuntimeError('worker crashed after reservation')
        with self.assertRaises(RuntimeError):durable.step('larry',body,crash)
        with self.assertRaises(durable.RequestConflict):durable.step('larry',body,self.advance)
        with self.assertRaises(durable.RequestConflict):durable.step('larry',self.initial(),self.advance)
        self.assertEqual(self.calls,1)
    def test_concurrent_duplicates_only_call_once(self):
        body=self.initial();results=[]
        def run():
            try:results.append(durable.step('larry',body,self.advance))
            except durable.RequestConflict:results.append('pending')
        ts=[threading.Thread(target=run) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertEqual(self.calls,1);self.assertEqual(len(results),2)
    def test_expired_job_rejected_before_reserving(self):
        result=durable.step('larry',self.initial(),self.advance)
        result['job']['created']=0;result['state']=index.seal(result['job'])
        with durable.connection() as (execute,_):execute('UPDATE dezzy_jobs SET state=? WHERE owner=?',(json.dumps(result),'larry'))
        with self.assertRaises(ValueError):durable.step('larry',{'job_id':result['job']['id'],'request_id':str(uuid.uuid4())},self.advance)
        # An expired task cannot leave the account stuck with an uncertain reservation.
        durable.step('larry',self.initial(),self.advance);self.assertEqual(self.calls,2)

    def test_vercel_cannot_use_ephemeral_sqlite(self):
        with patch.dict(os.environ,{'VERCEL':'1'}):
            with self.assertRaises(durable.StorageUnavailable):durable.history('larry')
