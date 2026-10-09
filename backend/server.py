"""Loopback-only pilot HTTP adapter. Do not expose this server to a company network."""
import argparse, getpass, json, os, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import defaultdict, deque
from core import Store, Error

def serve(store,port=8000):
    attempts=defaultdict(deque); lock=threading.Lock()
    origin=os.environ.get('MACHINECARE_ORIGIN','http://localhost:8080')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass # Never log credentials or request bodies.
        def respond(self,status,payload):
            body=json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            if self.headers.get('Origin')==origin: self.send_header('Access-Control-Allow-Origin',origin)
            self.end_headers(); self.wfile.write(body)
        def do_OPTIONS(self):
            if self.headers.get('Origin')!=origin: return self.respond(403,{'error':'Origin is not allowed.'})
            self.send_response(204); self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Access-Control-Allow-Headers','Authorization,Content-Type')
            self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS'); self.end_headers()
        def token(self):
            value=self.headers.get('Authorization','')
            if not value.startswith('Bearer '): raise Error('Sign in first.',401)
            return value[7:]
        def handle_request(self,post):
            try:
                if self.headers.get('Origin') not in (None,origin): raise Error('Origin is not allowed.',403)
                path=self.path.split('?')[0]
                if post:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=32768: raise Error('Invalid request size.')
                    d=json.loads(self.rfile.read(size))
                    if not isinstance(d,dict): raise Error('Expected a JSON object.')
                    if path=='/login':
                        key=self.client_address[0]
                        with lock:
                            q=attempts[key]
                            while q and q[0]<time.time()-300: q.popleft()
                            if len(q)>=15: raise Error('Too many login attempts. Wait five minutes.',429)
                            q.append(time.time())
                        result=store.login(str(d.get('username','')),str(d.get('password','')))
                    elif path.startswith('/actions/'): result=store.execute(self.token(),path.rsplit('/',1)[1],d)
                    else: raise Error('Route not found.',404)
                elif path=='/health': result={'status':'ok','mode':'local-pilot'}
                elif path=='/state': result=store.state(self.token())
                else: raise Error('Route not found.',404)
                self.respond(200,result)
            except Error as e: self.respond(e.status,{'error':e.message})
            except (ValueError,TypeError,KeyError): self.respond(400,{'error':'Invalid input. Check required fields and data types.'})
            except Exception: self.respond(500,{'error':'Server error. No partial transaction was committed.'})
        def do_GET(self): self.handle_request(False)
        def do_POST(self): self.handle_request(True)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'MachineCare pilot API: http://127.0.0.1:{server.server_port}',flush=True)
    return server

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['init','seed','run']); parser.add_argument('--db',default='machinecare.db'); parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args(); store=Store(args.db)
    if args.command=='init':
        username=input('First administrator username: ').strip()
        if not username: raise SystemExit('Username is required.')
        password=getpass.getpass('Administrator password (12+ characters): ')
        if password!=getpass.getpass('Confirm password: '): raise SystemExit('Passwords do not match.')
        store.bootstrap(username,password); print('Administrator created. No default credentials.')
    elif args.command=='seed': store.seed(); print('Sample equipment added. No sample accounts or passwords created.')
    else:
        server=serve(store,args.port)
        try: server.serve_forever()
        except KeyboardInterrupt: server.server_close()
