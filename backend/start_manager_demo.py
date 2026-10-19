"""Start loopback-only demo servers on a new session-cleared database copy."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import backup

root=Path(__file__).resolve().parents[1]
for port in (8000,18080):
    with socket.socket() as connection:
        connection.settimeout(1)
        if connection.connect_ex(('127.0.0.1',port))==0:
            raise SystemExit(f'Port {port} is in use. Close earlier MachineCare servers before starting a fresh demo.')
if not (root/'app/build/web/index.html').is_file():raise SystemExit('Build the Flutter web app first.')
snapshot,_=backup.create(root/'backend/machinecare.db',root/'.verification/manager-demo')
environment={key.upper():value for key,value in os.environ.items()}
environment['MACHINECARE_ORIGIN']='http://localhost:18080'
processes=[]
try:
    for name,arguments in [('api',[str(root/'backend/server.py'),'run','--db',str(snapshot),'--port','8000']),
                           ('web',['-m','http.server','18080','--bind','127.0.0.1','--directory',str(root/'app/build/web')])]:
        with (snapshot.parent/f'{snapshot.stem}-{name}.log').open('w') as log:
            processes.append(subprocess.Popen([sys.executable,*arguments],cwd=root,env=environment,
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
    for attempt in range(20):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1) as response:assert response.status==200
            with urllib.request.urlopen('http://127.0.0.1:18080/',timeout=1) as response:assert response.status==200
            break
        except (OSError,AssertionError):
            if any(p.poll() is not None for p in processes):raise RuntimeError('Demo server exited; inspect logs.')
            time.sleep(.25)
    else:raise RuntimeError('Demo server health checks timed out.')
except Exception:
    for process in processes:process.terminate()
    raise
(snapshot.parent/'running-demo.json').write_text(json.dumps({'database':str(snapshot),'backendPid':processes[0].pid,'frontendPid':processes[1].pid},indent=2))
print('DEMO COPY: changes do not modify backend/machinecare.db.')
print('Open http://localhost:18080 and sign in with your current account/password.')
print('Demo database:',snapshot)
print('Server health checks passed. PIDs:',*[p.pid for p in processes])
