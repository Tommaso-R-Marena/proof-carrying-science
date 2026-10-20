"""Negative-only HTTP availability probe; no store or verifier acceptance exists."""
import sys,time,socket,threading,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
TARGET=Path('/workspace/pcs-independent-witness-v1')
sys.path.insert(0,str(TARGET))
from research.scientific_witness_v1.server import make_server
source=TARGET/'research/scientific_witness_v1/server.py'
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scope':'Unauthenticated HTTP parser availability only; no positive authorization/store/verifier mock.'}
server=make_server(None,port=0)
thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
first=socket.create_connection(server.server_address,timeout=1)
second=None
try:
 first.sendall(b'POST /rpc HTTP/1.0\r\n')
 time.sleep(.05)
 second=socket.create_connection(server.server_address,timeout=1);second.settimeout(.35)
 second.sendall(b'GET / HTTP/1.0\r\n\r\n')
 start=time.monotonic()
 try:answer=second.recv(2048);outcome='answered'
 except TimeoutError:answer=b'';outcome='timed_out'
 report.update(second_request=outcome,blocked_seconds=time.monotonic()-start)
 first.close();second.settimeout(2)
 if not answer:answer=second.recv(2048)
 report['after_first_disconnect_response']=answer.split(b'\r\n',1)[0].decode('ascii')
 report['observed_unauthenticated_head_of_line_blocking']=outcome=='timed_out'
 print(json.dumps(report,indent=2))
finally:
 first.close()
 if second:second.close()
 server.shutdown();server.server_close();thread.join(2)
