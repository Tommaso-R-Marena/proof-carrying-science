"""Read-only technical inventory: declarations are not legal clearance."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(root):
    root=Path(root).resolve()
    tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0'))-{''}
    names=set(subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root).decode().split('\0'))-{''}
    rights=[]; dependencies=[]; actions=[]; experiments=[]
    for name in sorted(filter(None,names)):
        path=root/name
        if not path.is_file() or path.is_symlink(): continue
        base=path.name.lower()
        if any(token in base for token in ('license','notice','rights','data_card','datacard')):
            rights.append({'path':name,'sha256':digest(path),'scope':'File name indicates rights/provenance material; content requires review.'})
        if base in ('pyproject.toml','cargo.toml','cargo.lock','package.json','package-lock.json','lake-manifest.json','lean-toolchain') or (base.startswith('requirements') and base.endswith(('.lock','.txt'))):
            dependencies.append({'path':name,'sha256':digest(path)})
        if name.startswith('.github/workflows/') and path.suffix in ('.yml','.yaml'):
            for number,line in enumerate(path.read_text().splitlines(),1):
                match=re.search(r'\buses:\s*([^\s#]+)',line)
                if match:
                    ref=match.group(1); suffix=ref.rsplit('@',1)[-1]
                    actions.append({'path':name,'line':number,'reference':ref,'immutable_commit_pin':bool(re.fullmatch('[0-9a-fA-F]{40}',suffix)),'local_action':ref.startswith('./')})
        if name.startswith('research/') and base in ('evidence_sha256.json','artifact_sha256.json','data-manifest.json','protocol.json','registry.json','source-manifest.json'):
            experiments.append({'path':name,'sha256':digest(path),'rights_status':'not_inferred_from_presence'})
    return {'format':'pcs-technical-rights-and-provenance-inventory-v1','source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'source_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip(),
            'dirty_status':subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip(),
            'inventory_scope':'Tracked and nonignored untracked regular files; development overlay is not the HEAD commit alone.',
            'tracked_path_count':len(tracked),'nonignored_untracked_path_count':len(names-tracked),
            'first_party_license_file_sha256':digest(root/'LICENSE') if (root/'LICENSE').is_file() and not (root/'LICENSE').is_symlink() else None,
            'rights_files':rights,'dependency_manifests':dependencies,'workflow_actions':actions,'experiment_manifests':experiments,
            'legal_clearance':False,'automatic_distribution_authority':False,
            'unresolved':['Transitive package license review is not complete.','Generated assets and contributors require source-specific review.','Academic or institutional rights cannot be established by a repository scan.','Tagged actions are mutable unless separately source-bound.'],
            'preservation':'Existing first-party license files are unchanged; owner publication authorization is separate from third-party rights.'}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(inventory(args.root),indent=2)+'\n')
