"""Explicit import-order successor to the preserved, historically uncompiled v0.7 exports.

No inequalities, hypotheses or proof tactics change. Generated source still has
no kernel verdict until the qualified checker actually succeeds.
"""
from .lean_export_v07 import export_relational as legacy_relational, export_update as legacy_update

def import_first(source):
    needle='import Mathlib\n'
    if source.count(needle)!=1 or not source.startswith('/-!'):
        raise ValueError('Exact legacy export framing required')
    return needle+'\n'+source.replace(needle,'',1)

def export_relational(*args,**kwargs):return import_first(legacy_relational(*args,**kwargs))
def export_update(*args,**kwargs):return import_first(legacy_update(*args,**kwargs))

def main():
    import argparse,hashlib,json
    from pathlib import Path
    from .verify_relational import strict_load
    from .lean_status_v07 import check_proof
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
    for mode in ['relation','update']:
        p=sub.add_parser(mode);p.add_argument('model')
        if mode=='update':p.add_argument('new_model')
        p.add_argument('certificate');p.add_argument('reviewer_policy');p.add_argument('output');p.add_argument('--check',action='store_true');p.add_argument('--project-dir')
    a=parser.parse_args();args=[Path(a.model).read_bytes()]
    if a.mode=='update':args.append(Path(a.new_model).read_bytes())
    args.extend([strict_load(a.certificate),strict_load(a.reviewer_policy)])
    source=(export_relational if a.mode=='relation' else export_update)(*args)
    path=Path(a.output)
    with path.open('x',encoding='utf-8') as f:f.write(source)
    result={'status':'SOURCE_EXPORTED_NOT_KERNEL_CHECKED','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pcs_authority':False}
    if a.check:result=check_proof(path,a.project_dir)
    print(json.dumps(result,indent=2));return 0 if not a.check or result['kernel_checked'] else 2
if __name__=='__main__':raise SystemExit(main())
