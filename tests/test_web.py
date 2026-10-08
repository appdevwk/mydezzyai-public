import base64
import http.client
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from api import index
import core

ENV={'DEZZY_USERNAME':'larry','DEZZY_PASSWORD':'test-password','DEZZY_SIGNING_SECRET':'test-signing-secret','OPENAI_API_KEY':'fake-test-key'}

def fake(instructions,prompt,search=False,schema=None):
    if schema==core.PLAN_SCHEMA: text=json.dumps({'questions':['Implementation','Alternatives','Limitations']})
    elif schema==core.PRODUCT_SCHEMA: text=json.dumps({'report':'Verified mock report','python_code':"raise RuntimeError('never execute')"})
    else: text='Mock research or review'
    return {'text':text,'sources':{'https://example.com':'Evidence'} if search else {},'usage':{}}

class WebTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,ENV);self.env.start()
    def tearDown(self): self.env.stop()
    def test_seven_separate_invocations(self):
        for mode in ('research','draft','code'):
            body={'task':'Build my project','mode':mode}
            for step in range(7):
                data=index.advance(body,fake)
                self.assertEqual(data['job']['calls'],step+1)
                body={'state':data['state']}
            self.assertEqual(data['job']['status'],'completed')
            self.assertEqual(sum(bool(s['sources']) for s in data['job']['steps']),3)
            if mode=='code':self.assertIn('syntax passed',data['job']['result']['validation'])
            else:self.assertEqual(data['job']['result']['python_code'],'')
            with self.assertRaises(ValueError):index.advance(body,fake)
    def test_tampered_and_expired_state(self):
        data=index.advance({'task':'Task','mode':'draft'},fake)
        with self.assertRaises(ValueError):index.unseal(data['state']+'bad')
        job=data['job'];job['created']=0
        with self.assertRaises(ValueError):index.unseal(index.seal(job))

    def test_livekit_token_requires_config_and_is_short_lived(self):
        with patch.dict(os.environ, {'LIVEKIT_URL':'', 'LIVEKIT_API_KEY':'', 'LIVEKIT_API_SECRET':''}):
            with self.assertRaises(RuntimeError): index.livekit_token()
        with patch.dict(os.environ, {'LIVEKIT_URL':'wss://example.livekit.cloud', 'LIVEKIT_API_KEY':'key', 'LIVEKIT_API_SECRET':'secret', 'LIVEKIT_ROOM':'dezzy'}):
            token=index.livekit_token()
            self.assertEqual(token['url'],'wss://example.livekit.cloud')
            self.assertEqual(len(token['token'].split('.')),3)
            claims=json.loads(base64.urlsafe_b64decode(token['token'].split('.')[1]+'=='))
            self.assertEqual(claims['iss'],'key')
            self.assertEqual(claims['video']['room'],'dezzy')
    def test_failed_provider_never_retries(self):
        count=[]
        def fail(*a,**k):count.append(1);raise RuntimeError('Provider failed')
        result=index.advance({'task':'Task','mode':'research'},fail)
        self.assertEqual(result['job']['status'],'failed');self.assertEqual(len(count),1)
        with self.assertRaises(ValueError):index.advance({'state':result['state']},fail)
    def test_invalid_input(self):
        for body in ({},{'task':'','mode':'code'},{'task':'a'*8001,'mode':'code'},{'task':'Valid','mode':'bad'}):
            with self.assertRaises(ValueError):index.advance(body,fake)
    def test_seo_configuration(self):
        with patch.dict(os.environ,{'DEZZY_PUBLIC_URL':'https://dezzy.example.com'}):
            self.assertEqual(index.public_url(),'https://dezzy.example.com')
            html=index.about()
            self.assertIn('rel="canonical" href="https://dezzy.example.com/about"',html)
            self.assertIn('application/ld+json',html)
            self.assertIn('og:description',html)
        for url in ('http://example.com','https://user:password@example.com','https://example.com/path','https://example.com?query=1'):
            with patch.dict(os.environ,{'DEZZY_PUBLIC_URL':url}):self.assertEqual(index.public_url(),'')
        self.assertIn('content="noindex, nofollow"',index.page())
    def test_http_auth_routes_and_csrf(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),index.handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
        auth={'Authorization':'Basic '+base64.b64encode(b'larry:test-password').decode()}
        def request(method,path,body=None,headers=None):
            conn.request(method,path,body=body,headers=headers or {})
            response=conn.getresponse();return response.status,response.read(),dict(response.getheaders())
        try:
            self.assertEqual(request('GET','/about')[0],200)
            status,body,_=request('GET','/robots.txt')
            self.assertEqual(status,200);self.assertIn(b'Disallow: /',body);self.assertIn(b'Allow: /about$',body)
            with patch.dict(os.environ,{'DEZZY_PUBLIC_URL':'https://dezzy.example.com'}):
                status,body,_=request('GET','/sitemap.xml')
                self.assertEqual(status,200);self.assertIn(b'https://dezzy.example.com/about',body)
            self.assertEqual(request('GET','/')[0],401)
            status,body,headers=request('GET','/',headers=auth)
            self.assertEqual(status,200);self.assertIn(b'myDEZZYAI',body)
            self.assertNotIn(b'__TOKEN__',body);self.assertNotIn(b'fake-test-key',body)
            self.assertEqual(headers['Cache-Control'],'no-store')
            self.assertEqual(headers['X-Frame-Options'],'DENY')
            self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
            self.assertEqual(headers['X-Robots-Tag'],'noindex, nofollow')
            self.assertEqual(request('GET','/api/health',headers=auth)[0],200)
            conn.request('GET','/api/health',headers={**auth,'X-Forwarded-Proto':'https'})
            secure_health=conn.getresponse();secure_health.read()
            self.assertIn('max-age=31536000',dict(secure_health.getheaders())['Strict-Transport-Security'])
            self.assertEqual(request('POST','/api/step','{}',auth)[0],403)
            h={**auth,'Content-Type':'application/json','X-Dezzy-Request':'1'}
            self.assertEqual(request('POST','/api/step','[]',h)[0],400)
            original=index.advance
            with patch.object(index,'advance',side_effect=lambda body:original(body,fake)):
                status,body,_=request('POST','/api/step',json.dumps({'task':'Test task','mode':'code'}),h)
                self.assertEqual(status,200)
                result=json.loads(body)
                self.assertEqual(result['job']['calls'],1)
                self.assertEqual(index.unseal(result['state'])['id'],result['job']['id'])
            self.assertEqual(request('GET','/not-found',headers=auth)[0],404)
            with patch.dict(os.environ,{'DEZZY_PASSWORD':''}):self.assertEqual(request('GET','/',headers=auth)[0],503)
        finally:conn.close();server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
