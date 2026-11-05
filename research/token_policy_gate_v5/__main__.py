import argparse,json,sys,subprocess
from pathlib import Path
from .receiver import receive

def main():
    p=argparse.ArgumentParser(description='Kernel-check model token/byte/policy pairs before SQL receiving replay')
    p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--tokenizer',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(receive(a.input,a.tokenizer,a.output)));return 0
    except (OSError,ValueError,RuntimeError,EOFError,subprocess.SubprocessError) as e:
        print(json.dumps(dict(status='REFUSED_OR_UNAVAILABLE',error=type(e).__name__,complete=False,pcs_authority=False)),file=sys.stderr);return 20

if __name__=='__main__':raise SystemExit(main())
