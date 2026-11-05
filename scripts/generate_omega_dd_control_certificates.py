"""Reproduce fixed control certificate proposals; Lean checking remains mandatory."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,help="Write proposals to a new directory instead of comparing checked-in bytes")
    args=parser.parse_args()
    if args.output_dir:args.output_dir.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((ROOT/"research/aristotle-omega-dd-v1/source-manifest.json").read_text())
    results=[]
    for name in ["DeMorgan","Choices","DenseControl"]:
        source=ROOT/"scripts/lean"/("generate_omega_dd_"+name+".lean")
        if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest["certificate_generators"][source.relative_to(ROOT).as_posix()]:
            raise ValueError("Generator source identity changed")
        p=subprocess.run(["lake","env","lean","--run",str(source)],cwd=ROOT/"formal",capture_output=True,timeout=120)
        if p.returncode:
            sys.stderr.buffer.write(p.stdout+p.stderr);return p.returncode
        expected=ROOT/"formal/PCSReferenceCertificates"/(name+".lean")
        if args.output_dir:(args.output_dir/(name+".lean")).write_bytes(p.stdout)
        elif p.stdout!=expected.read_bytes():raise ValueError("Certificate reproduction differs: "+name)
        results.append({"name":name,"sha256":hashlib.sha256(p.stdout).hexdigest(),"kernel_verified_by_generator":False})
    print(json.dumps({"format":"pcs-omega-dd-control-reproduction-v1","certificates":results,"pcs_authority":False},indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
