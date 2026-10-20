"""Real local principal/namespace probes; never claims independent administration."""
import os,sys,subprocess,json,tempfile,shutil
from pathlib import Path
report={'uid':os.getuid(),'euid':os.geteuid(),'gid':os.getgid(),'sudo_available':shutil.which('sudo') is not None,'newuidmap_available':shutil.which('newuidmap') is not None,'newgidmap_available':shutil.which('newgidmap') is not None,'uid_map':Path('/proc/self/uid_map').read_text(),'capability_status':[line for line in Path('/proc/self/status').read_text().splitlines() if line.startswith(('CapEff:','CapBnd:','NoNewPrivs:','Seccomp:'))]}
namespace=subprocess.run(['unshare','-Ur',sys.executable,'-c','import os,json;from pathlib import Path; x={"namespace_uid":os.getuid(),"outer_uid_map":Path("/proc/self/uid_map").read_text()};\ntry: os.setuid(65534);x["distinct_uid_switch"]="succeeded"\nexcept OSError as e: x["distinct_uid_switch"]={"errno":e.errno,"error":str(e)}\nprint(json.dumps(x))'],capture_output=True,text=True)
report['user_namespace']={'returncode':namespace.returncode,'stdout':namespace.stdout.strip(),'stderr':namespace.stderr.strip()}
with tempfile.TemporaryDirectory() as temp:
 path=Path(temp)/'fixture-key';path.write_bytes(os.urandom(32));os.chmod(temp,0o700);os.chmod(path,0o600)
 child=subprocess.run([sys.executable,'-c','import pathlib,sys;print(len(pathlib.Path(sys.argv[1]).read_bytes()))',str(path)],capture_output=True,text=True)
 report['same_uid_separate_process_can_read_fixture_0600_key']={'returncode':child.returncode,'observed_bytes':child.stdout.strip(),'key_material_printed':False}
report['profiles']={'A':'EXECUTABLE_LOCAL_MULTI_PROCESS_ONE_ADMINISTRATOR','B':'BLOCKED_TECHNICAL: no supported distinct outer-UID mapping/helper or privilege in this environment','C':'BLOCKED_EXTERNAL: no independent administrator/host or independently protected key/bootstrap supplied'}
print(json.dumps(report,indent=2))
