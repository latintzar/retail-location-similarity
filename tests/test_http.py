"""Exercise the shipped scorer over loopback with its authored synthetic matrix."""
from pathlib import Path
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class QuietHandler(server.Handler):
    def log_message(self,*args):pass

class ScorerHTTPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start();cls.origin='http://127.0.0.1:'+str(cls.http.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join(timeout=5)

    def post(self,body):
        request=urllib.request.Request(self.origin+'/api/search',data=body,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=20) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as error:return error.code,json.load(error)

    def test_preset_runs_the_original_scorer(self):
        status,result=self.post(json.dumps({'lat':51.5117,'lng':-.124,'top_k':5}).encode())
        self.assertEqual(status,200)
        self.assertEqual(len(result['similar_hexes']),5)
        self.assertEqual(result['stats']['total_hexes'],90)
        self.assertEqual(result['stats']['feature_dimensions'],5)
        scores=[row['similarity'] for row in result['similar_hexes']]
        self.assertEqual(scores,sorted(scores,reverse=True))

    def test_invalid_requests_are_rejected_before_search(self):
        for body in [b'{',b'x'*2049,json.dumps({'lat':0,'lng':0}).encode(),json.dumps({'lat':float('inf'),'lng':0}).encode()]:
            with self.subTest(body_bytes=len(body)):self.assertEqual(self.post(body)[0],400)

    def test_dataset_source_is_explicit_and_files_are_not_browsable(self):
        with urllib.request.urlopen(self.origin+'/api/source',timeout=5) as response:source=json.load(response)
        self.assertIn('Synthetic',source['dataset'])
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.origin+'/server.py',timeout=5)
        self.assertEqual(error.exception.code,404)

if __name__=='__main__':unittest.main()
