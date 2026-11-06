"""Source-owned obligations and independent closed checkers; no scientific authority."""
from __future__ import annotations
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import time

from research.scientific_intake_v1.checks import bound_bytes,bindings_valid
from research.scientific_intake_v1.intake import digest
from .dimensions import check_expression
from .model_checks import SBMLModel,first,tag,mathml,fraction,safe_xml,conservation,matlab_correspondence,integrate_model


def eval_ir(ir,values,depth=0):
    if depth>64:raise ValueError('IR depth bound')
    from .model_checks import bounded,power
    op=ir['op']
    if op=='number':return fraction(ir['value'])
    if op=='symbol':return values[ir['name']]
    if op=='neg':return -eval_ir(ir['arg'],values,depth+1)
    args=[eval_ir(a,values,depth+1) for a in ir.get('args',[])]
    if op=='add':
        total=0
        for x in args:total=bounded(total+x)
        return total
    if op=='mul':
        total=1
        for x in args:total=bounded(total*x)
        return total
    if op=='sub' and len(args)==2:return bounded(args[0]-args[1])
    if op=='div' and len(args)==2:return bounded(args[0]/args[1])
    if op=='pow' and len(args)==2:return power(*args)
    raise ValueError('unsupported independent scalar IR')


def symbols(ir):
    if not isinstance(ir,dict):return set()
    names={ir['name']} if ir.get('op')=='symbol' else set()
    for v in ir.values():
        if isinstance(v,dict):names|=symbols(v)
        elif isinstance(v,list):
            for a in v:names|=symbols(a)
    return names


def obligations(interpretation,inventory):
    arts=inventory['artifacts'];by_id={a['id']:a for a in arts};result=[]
    def add(checker,payload,source,ids):
        bindings=[{'artifact_id':x,'sha256':by_id[x]['sha256'],'size':by_id[x]['size']} for x in sorted(set(ids))]
        value={'checker':checker,'payload':payload,'source':source,'artifact_ids':sorted(set(ids)),
               'source_bindings':bindings,'assumptions':['Original source is data; scientific meaning requires review.'],'authority':False}
        value['id']='obligation-'+digest(value)[:24];result.append(value)
    for item in interpretation['equations']:
        src=item['source'];checker='source_equation' if item.get('origin','').startswith('sbml_') else 'meaning_review'
        add(checker,{'item':item},src,[src['artifact_id']])
        add('dimension',{'item':item},src,[src['artifact_id']])
    for item in interpretation['quantities']:
        src=item['source'];add('source_quantity',{'item':item},src,[src['artifact_id']])
    for a in arts:
        if a['path'].endswith(('.sbml','.xml')) and b'<sbml' in bound_bytes(a)[:500]:
            source={'artifact_id':a['id'],'sha256':a['sha256'],'quote':'','locator':{'whole_artifact':True}}
            peers=[b for b in arts if b['path'].endswith('.m')]
            add('model_assurance',{'artifact_id':a['id'],'export_id':peers[0]['id'] if len(peers)==1 else None},source,[a['id']]+([peers[0]['id']] if len(peers)==1 else []))
        elif a['path'].endswith('.rst'):
            add('document_reproduction',{'artifact_id':a['id']},{'artifact_id':a['id'],'sha256':a['sha256'],'quote':'','locator':{'whole_artifact':True}},[a['id']])
    return sorted(result,key=lambda o:o['id'])


def _source_quantity(item,raw):
    role=item.get('role','');actual=None
    if role.startswith('sbml_'):
        root=safe_xml(raw);name=item.get('symbol',item.get('name'));attribute=role[5:]
        if role=='sbml_local_parameter':
            reactions=[n for n in root.iter() if tag(n)=='reaction' and n.get('id')==item['scope']]
            matches=[n for r in reactions for n in r.iter() if tag(n) in {'parameter','localParameter'} and n.get('id')==name];attribute='value'
        else:matches=[n for n in root.iter() if n.get('id')==name and attribute in n.attrib]
        if len(matches)!=1:raise ValueError('quantity declaration not unique')
        actual=fraction(matches[0].get(attribute))
        return {'status':'VERIFIED_SUPPORTED' if actual==fraction(item['value']) else 'REFUTED',
                'evidence':{'actual':str(actual),'proposed':item['value'],'checked_fields':['numeric_value','source_binding'],'unchecked_fields':['physical_unit_semantics','scientific_meaning'],'scope':'Exact source-declared numeric quantity only; units, empirical measurement and scientific validity are not established.'}}
    return {'status':'UNKNOWN','evidence':{'reason':'Reported document quantity is extracted; interpreting its experimental context or reproducing it requires a supported computational example or review.'}}


def _source_equation(item,raw):
    if item.get('parse_status')!='SUPPORTED':raise ValueError('unresolved equation')
    model=SBMLModel(raw);lhs=item['lhs'];reaction=None;direct=None
    if item['origin']=='sbml_kinetic_law':
        rid=item.get('reaction') or lhs.get('reaction') or lhs.get('id')
        reaction=next(r for r in model.reactions if r['id']==rid);direct=reaction['math']
    elif item['origin']=='sbml_assignmentRule':direct=next(expr for name,expr in model.assignments if name==lhs['name'])
    else:raise ValueError('equation outside supported independent SBML subset')
    expected_symbols={(n.text or '').strip() for n in direct.iter() if tag(n)=='ci'}
    if symbols(item['rhs'])!=expected_symbols:raise ValueError('source-to-IR dependency mismatch')
    from .rational_equivalence import compare,direct_ir
    algebra=compare(direct_ir(direct),item['rhs'])
    mismatches=[]
    for j in range(12):
        y=[Fraction((i+1)*(j+1),100) for i in range(len(model.dynamic))];context=model.context(y)
        if reaction:context.update(reaction['local'])
        a=mathml(direct,context);b=eval_ir(item['rhs'],context)
        if a!=b:mismatches.append({'sample':j,'source':str(a),'interpretation':str(b)})
    return {'status':'REFUTED' if mismatches or algebra['status']=='DISTINCT_RATIONAL_FUNCTIONS' else 'VERIFIED_SUPPORTED','evidence':{'rational_equivalence':algebra,'samples':12,'dependency_symbols':sorted(expected_symbols),'mismatches':mismatches,
            'scope':'Exact rational-function comparison on the common defined domain plus finite differential observations and syntactic dependencies. Python refinement and scientific meaning remain open.'}}


def execute(obligation,artifacts,*,kernel=True):
    started=time.monotonic();result={'id':obligation['id'],'obligation_id':obligation['id'],'checker':obligation['checker'],'status':'UNKNOWN',
        'source_bindings':obligation['source_bindings'],'evidence':{},'authority':False,'scientific_meaning':'OPEN'}
    try:
        bindings_valid(obligation,artifacts);checker=obligation['checker'];p=obligation['payload']
        if checker=='source_quantity':result.update(_source_quantity(p['item'],bound_bytes(artifacts[obligation['source']['artifact_id']])))
        elif checker=='source_equation':result.update(_source_equation(p['item'],bound_bytes(artifacts[obligation['source']['artifact_id']])))
        elif checker=='dimension':
            item=p['item'];r=check_expression(item['rhs'],item.get('symbol_units',{})) if item.get('rhs') else {'status':'UNKNOWN','reason':'unresolved meaning'}
            result.update(status={'VERIFIED':'VERIFIED_SUPPORTED','REFUTED':'REFUTED'}.get(r['status'],'UNKNOWN'),evidence=r)
        elif checker=='model_assurance':
            model=SBMLModel(bound_bytes(artifacts[p['artifact_id']]));c=conservation(model)
            certificates=[]
            if kernel:
                from .concrete_lean import verify_certificate
                for vector in c['certificates'][:4]:
                    try:certificates.append(verify_certificate({'matrix':c['matrix'],'weights':vector['amount_weights']}))
                    except (ValueError,RuntimeError) as exc:certificates.append({'status':'UNKNOWN','reason':str(exc)[:1000]})
            if kernel and len(c['certificates'])>4:certificates.append({'status':'UNKNOWN','reason':'Kernel certificate budget: at most four vectors per model'})
            numeric=integrate_model(model)
            correspondence=matlab_correspondence(model,bound_bytes(artifacts[p['export_id']])) if p.get('export_id') else {'status':'UNSUPPORTED'}
            success=numeric['max_solver_difference']<1e-4 and correspondence['status']=='MATCHED_FINITE_RATIONAL_SAMPLES' and all(x['status'].startswith('KERNEL_CHECKED') for x in certificates)
            result.update(status='VERIFIED_SUPPORTED' if success else 'REFUTED' if correspondence['status']=='CONTRADICTED' else 'UNKNOWN',evidence={'conservation':c,'kernel_certificates':certificates,'numerical':numeric,'author_export':correspondence,
                          'scope':'Compound finite model-assurance observations; no scientific meaning promoted.'})
        elif checker=='document_reproduction':
            from .document_checks import check_document
            a=artifacts[p['artifact_id']];r=check_document(bound_bytes(a),a['path']);result.update(status='VERIFIED_SUPPORTED' if r['status']=='REPRODUCED' else 'REFUTED' if r['status']=='REFUTED' else 'UNKNOWN',evidence=r)
        else:result['evidence']={'reason':'Human scientific interpretation required'}
        bindings_valid(obligation,artifacts)
    except (OSError,ValueError,KeyError,TypeError,SyntaxError,IndexError,RuntimeError,ArithmeticError,StopIteration,ImportError) as exc:
        result.update(status='UNKNOWN',evidence={'reason':str(exc)[:1500],'error_type':type(exc).__name__})
    result['seconds']=time.monotonic()-started
    return result


def execute_bounded(obligation,artifacts):
    if obligation['checker'] not in {'model_assurance','document_reproduction'}:return execute(obligation,artifacts)
    import importlib.util,os,subprocess,sys
    from research.scientific_intake_v1.intake import canonical
    from pcs.jsonio import strict_json_loads
    root=Path(__file__).resolve().parents[2];paths=[str(root)]
    scipy=importlib.util.find_spec('scipy')
    if scipy and scipy.origin:paths.append(str(Path(scipy.origin).parent.parent))
    env={'PATH':os.environ.get('PATH',''),'PYTHONPATH':os.pathsep.join(paths),'LANG':'C.UTF-8',
         'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    import tempfile,shutil
    scratch=tempfile.mkdtemp(prefix='pcs-scientific-worker-');env['TMPDIR']=scratch
    try:
        process=subprocess.Popen([sys.executable,'-m','research.scientific_understanding_v2.worker'],cwd=root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:stdout,stderr=process.communicate(canonical({'obligation':obligation,'artifacts':artifacts}),timeout=35)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(process.pid,signal.SIGKILL);process.communicate()
            raise ValueError('bounded computation deadline exceeded')
        if process.returncode or len(stdout)>16*1024**2:raise ValueError('bounded computation failed: '+stderr.decode(errors='replace')[-500:])
        return strict_json_loads(stdout.decode())
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        return {'id':obligation['id'],'obligation_id':obligation['id'],'checker':obligation['checker'],'status':'UNKNOWN','source_bindings':obligation['source_bindings'],
                'evidence':{'reason':str(exc)[:1000],'resource_failure':True},'authority':False,'scientific_meaning':'OPEN','seconds':0.}
    finally:shutil.rmtree(scratch)
