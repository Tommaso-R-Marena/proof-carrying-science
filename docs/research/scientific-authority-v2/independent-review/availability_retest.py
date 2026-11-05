"""Negative-only HTTP/TLS acquisition deadlines; no scientific authorization."""
import sys,time,socket,threading,json,hashlib,tempfile,ssl,datetime,ipaddress
from pathlib import Path
sys.dont_write_bytecode=True
TARGET=Path('/workspace/pcs-independent-witness-v1');sys.path.insert(0,str(TARGET))
from research.scientific_witness_v1 import server as module
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.x509.oid import NameOID
source=TARGET/'research/scientific_witness_v1/server.py';before=hashlib.sha256(source.read_bytes()).hexdigest()
observations=[]
def run_plain():
 server=module.make_server(None,port=0);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
 first=socket.create_connection(server.server_address,timeout=2);first.sendall(b'POST /rpc HTTP/1.0\r\nX-Slow: ')
 stop=threading.Event();sent=[0]
 def trickle():
  while not stop.wait(.1):
   try:first.sendall(b'x');sent[0]+=1
   except OSError:return
 trickler=threading.Thread(target=trickle,daemon=True);trickler.start();time.sleep(.05)
 second=socket.create_connection(server.server_address,timeout=2);second.settimeout(module.ACQUISITION_SECONDS+3);second.sendall(b'GET / HTTP/1.0\r\n\r\n');start=time.monotonic()
 try:
  response=second.recv(2048);elapsed=time.monotonic()-start
  return {'id':'continuous_header_trickle_absolute_deadline','wall_seconds':elapsed,'trickle_bytes':sent[0],'http_status':response.split(b'\r\n',1)[0].decode(),'passed':response.startswith(b'HTTP/1.0 501') and elapsed<module.ACQUISITION_SECONDS+2 and sent[0]>5}
 finally:
  stop.set();first.close();second.close();server.shutdown();server.server_close();thread.join(2);trickler.join(2)
def run_tls(directory):
 key=ec.generate_private_key(ec.SECP256R1());name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'127.0.0.1')]);now=datetime.datetime.now(datetime.timezone.utc)
 cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(minutes=10)).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False).sign(key,hashes.SHA256())
 certpath=Path(directory)/'certificate.pem';keypath=Path(directory)/'tls-key.pem';certpath.write_bytes(cert.public_bytes(serialization.Encoding.PEM));keypath.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
 server=module.make_server(None,port=0,cert=str(certpath),tls_key=str(keypath));thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
 first=socket.create_connection(server.server_address,timeout=2);time.sleep(.05)
 context=ssl.create_default_context(cafile=str(certpath));plain=socket.create_connection(server.server_address,timeout=2);plain.settimeout(module.ACQUISITION_SECONDS+3);start=time.monotonic();second=None
 try:
  second=context.wrap_socket(plain,server_hostname='127.0.0.1');second.sendall(b'GET / HTTP/1.0\r\n\r\n');response=second.recv(2048);elapsed=time.monotonic()-start
  return {'id':'stalled_tls_handshake_absolute_deadline','wall_seconds':elapsed,'tls_certificate_verified':True,'http_status':response.split(b'\r\n',1)[0].decode(),'passed':response.startswith(b'HTTP/1.0 501') and elapsed<module.ACQUISITION_SECONDS+2}
 finally:
  first.close()
  if second:second.close()
  else:plain.close()
  server.shutdown();server.server_close();thread.join(2)
observations.append(run_plain())
with tempfile.TemporaryDirectory() as directory:observations.append(run_tls(directory))
report={'source_sha256':before,'source_after_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'configured_acquisition_seconds':module.ACQUISITION_SECONDS,'scope':'Real unauthenticated parser/TLS negative controls only. No positive scientific verifier or store is substituted. TLS certificate is local ephemeral test material.','observations':observations}
report['passed']=before==report['source_after_sha256'] and all(x['passed'] for x in observations)
print(json.dumps(report,indent=2))
if not report['passed']:raise SystemExit(1)
