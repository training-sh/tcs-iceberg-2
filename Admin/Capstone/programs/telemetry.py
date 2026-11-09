"""Small supplied job metrics endpoint; reports also persist independently in S3."""
from http.server import BaseHTTPRequestHandler,HTTPServer
import json,os,time,urllib.request
from pathlib import Path
STATE=Path('/state/report.json')
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path!='/report': self.send_error(404); return
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if data.get('status')!='PASS': self.send_error(400); return
        STATE.write_text(json.dumps(data))
        payload={'streams':[{'stream':{'app':'seller-ops','namespace':os.environ['POD_NAMESPACE']},'values':[[str(time.time_ns()),'SELLER_OPS_PASS '+json.dumps(data)]]}]}
        try:
            req=urllib.request.Request('http://loki:3100/loki/api/v1/push',json.dumps(payload).encode(),{'Content-Type':'application/json'})
            urllib.request.urlopen(req,timeout=10).close()
        except Exception: print('LOKI_DELIVERY_FAILED: inspect Loki readiness; report is retained in S3',flush=True)
        self.send_response(200); self.end_headers(); self.wfile.write(b'accepted')
    def do_GET(self):
        data=json.loads(STATE.read_text()) if STATE.exists() else {}
        if self.path=='/metrics':
            body='olist_job_success %d\nolist_job_duration_seconds %s\nolist_input_items %s\n'%(int(data.get('status')=='PASS'),data.get('seconds',0),data.get('input_items',0))
            for table,count in data.get('outputs',{}).items(): body+='olist_output_rows{table="%s"} %d\n'%(table,count)
            self.send_response(200); self.send_header('Content-Type','text/plain; version=0.0.4'); self.end_headers(); self.wfile.write(body.encode())
        else:
            self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(data).encode())
HTTPServer(('0.0.0.0',8000),Handler).serve_forever()
