"""Start the local research lab; gameplay needs only Python's standard library."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import webbrowser
from .server import create_server


def main():
    parser=argparse.ArgumentParser(__doc__);sub=parser.add_subparsers(dest='action',required=True)
    serve=sub.add_parser('serve',help='Read-only loopback lab; no Lean or Python packages needed')
    serve.add_argument('--port',type=int,default=8080);serve.add_argument('--open',action='store_true');serve.add_argument('--json',action='store_true')
    sub.add_parser('doctor',help='Report available tools; never issues a proof verdict')
    args=parser.parse_args()
    if args.action=='doctor':
        lean=shutil.which('lean');version=None
        if lean:
            try:version=subprocess.check_output([lean,'--version'],text=True,timeout=5).strip()
            except (OSError,subprocess.SubprocessError):pass
        print(json.dumps(dict(play_command='python -m research.trace_lab_v1 serve --open',
          gameplay_requires_lean=False,python_packages={name:importlib.util.find_spec(name) is not None for name in ('cryptography','jsonschema')},
          lean_path=lean,lean_version=version,kernel_checked=False,pcs_authority=False),indent=2));return
    try:server=create_server(args.port)
    except (OSError,ValueError) as error:parser.exit(2,f'Could not start lab: {error}\n')
    url=f'http://127.0.0.1:{server.server_port}/#seed=20261021'
    print(json.dumps(dict(url=url,kernel_checked=False,pcs_authority=False)) if args.json else f'PCS Trace Lab: {url}\nRead-only local lab. Lean checks run separately. Press Ctrl-C to stop.',flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
