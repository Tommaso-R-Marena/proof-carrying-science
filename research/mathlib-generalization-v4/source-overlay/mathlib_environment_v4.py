"""Research-local, receiver-controlled multi-step Mathlib proof search.

Extends the existing pinned Mathlib reader. Statements are trusted developer
inputs, not a public arbitrary-Lean API. Model actions never contain Lean source.
Each terminal is reconstructed and independently kernel-audited twice.
"""
from copy import deepcopy
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import tempfile
import time

from .environment import ROOT, LeanEnvironment, reference_expression
from .induction_ir import digest
from .mathlib_retrieval import MathlibRetriever, MATHLIB_REVISION, ALLOWED_AXIOMS, symbols, head_name
from .benchmark_mathlib_v4 import alpha_signature

IMPORTS = ('Mathlib.Data.Set.Function', 'Mathlib.Algebra.Group.Basic',
           'Mathlib.Data.Nat.Factorial.Basic', 'Mathlib.Data.List.Basic',
           'Mathlib.Data.Finset.Card', 'Mathlib.Data.Real.Basic', 'Mathlib.Tactic')
PREFIXES = ('Function.Injective', 'Function.Surjective', 'Set.preimage', 'Set.image',
            'Set.mem_', 'Set.subset_', 'List.length_', 'List.map_', 'List.append_',
            'List.reverse_', 'List.mem_', 'List.nil_', 'List.cons_',
            'Finset.card_', 'Finset.mem_', 'Finset.insert_', 'Finset.erase_',
            'Nat.factorial', 'Nat.dvd_', 'Nat.add_', 'Nat.mul_', 'Nat.succ_', 'Nat.le_')
NAMES = ('mul_assoc', 'mul_comm', 'mul_left_cancel', 'mul_right_cancel', 'mul_inv_rev',
         'inv_mul_cancel', 'mul_inv_cancel', 'inv_inv', 'one_mul', 'mul_one',
         'le_trans', 'le_antisymm', 'lt_of_lt_of_le', 'lt_of_le_of_lt', 'add_le_add',
         'add_assoc', 'add_comm', 'zero_add', 'add_zero', 'pow_succ', 'pow_zero',
         'Eq.trans', 'Eq.symm', 'congrArg', 'congrFun', 'le_of_eq')
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z')
LOCAL = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,30}(?:\.[12]){0,3}\Z')
BASE = {'assumption':'assumption', 'rfl':'rfl', 'constructor':'constructor', 'left':'left', 'right':'right'}
PORTFOLIO = ('simp_all', 'omega', 'aesop', 'grind', 'first | ring | linarith')

def same_kernel_type(first,second):
    """Ignore binder presentation/universe parameter names, preserve their scope.

    Each input is already a genuine kernel audit of the immutable source type.
    This does not decide arbitrary definitional equivalence or accept proofs.
    """
    return (first.get('format')==second.get('format')=='pcs-lean-kernel-v1'
            and set(first['axioms'])==set(second['axioms'])
            and set(first['axioms'])<=ALLOWED_AXIOMS
            and alpha_signature(first['expression'])==alpha_signature(second['expression']))

def catalog_command():
    return r'''open Lean Elab Command Meta
syntax "#pcs_mathlib_v4_catalog" : command
elab_rules : command
 | `(#pcs_mathlib_v4_catalog) => do
  liftTermElabM do
   let env ← getEnv
   let mut entries := #[]
   let prefixes : List String := ''' + json.dumps(list(PREFIXES)) + r'''
   let names : List String := ''' + json.dumps(list(NAMES)) + r'''
   for (name, info) in env.constants.toList do
    let isThm := match info with | .thmInfo _ => true | _ => false
    if isThm && (prefixes.any (fun p => p.isPrefixOf (toString name)) || names.contains (toString name)) then
     let moduleName := match env.getModuleIdxFor? name with
       | some idx => toString env.header.moduleNames[idx.toNat]!
       | none => "current"
     entries := entries.push <| Json.mkObj [
       ("name", toJson (toString name)), ("type", toJson (toString (← ppExpr info.type))),
       ("expression", PCSProofProbe.expression info.type), ("module", toJson moduleName),
       ("universes", toJson (info.levelParams.map toString))]
   IO.println s!"PCS_EXTERNAL_CATALOG:{(toJson entries).compress}"
#pcs_mathlib_v4_catalog
'''

class MathlibEnvironmentV4(MathlibRetriever):
    def __init__(self, *, timeout=12, excluded_names=(), excluded_modules=(), cache=None):
        self.cpu_seconds=0.; self.max_child_rss_kib=0; self.cache_hits=0; self.invalid=0
        self.worker=None;self.invocations=0;self.worker_requests=0;self.worker_cpu_seconds=0.
        self._states={};self.library=[];self.library_source='';self.library_sha256=digest([])
        self.excluded_names=frozenset(excluded_names); self.excluded_modules=frozenset(excluded_modules)
        self.mathlib=ROOT/'.lake/packages/mathlib'
        if subprocess.check_output(['git','-C',str(self.mathlib),'rev-parse','HEAD'],text=True).strip()!=MATHLIB_REVISION:raise RuntimeError('exact approved Mathlib revision required')
        self.lean=subprocess.check_output(['lean','--print-prefix'],text=True).strip()+'/bin/lean'
        self.version=subprocess.check_output([self.lean,'--version'],text=True).strip()
        if 'version 4.28.0,' not in self.version:raise RuntimeError('Lean4.28 required')
        self.cache=Path(cache or ROOT/'.lake/pcs-prover');self.cache.mkdir(parents=True,exist_ok=True)
        if not (self.cache/'PCSProofProbe.olean').exists():
            from .memory_cost import MeasuredInductionEnvironment
            env=MeasuredInductionEnvironment(cache=self.cache);env.close()
        self.paths=[self.cache,self.mathlib/'.lake/build/lib/lean']+sorted((ROOT/'.lake/packages').glob('*/.lake/build/lib/lean'))
        configured_timeout=timeout
        self.timeout=max(60,timeout);self.calls=0;self.seconds=0.
        self.import_digests={module:hashlib.sha256((self.mathlib/'.lake/build/lib/lean'/Path(module.replace('.','/')+'.olean')).read_bytes()).hexdigest() for module in IMPORTS}
        index=self.cache/'mathlib-v4-catalog.json'
        binding={'lean':self.version,'mathlib':MATHLIB_REVISION,'imports':self.import_digests,
                 'probe_sha256':hashlib.sha256((ROOT/'formal/PCSProofProbe.lean').read_bytes()).hexdigest(),
                 'catalog_command_sha256':hashlib.sha256(catalog_command().encode()).hexdigest()}
        cached=None
        if index.exists() and index.stat().st_size<=32_000_000:
            try:
                candidate=json.loads(index.read_text())
                if candidate['binding']==binding and digest(candidate['catalog'])==candidate['catalog_sha256']:cached=candidate['catalog']
            except (ValueError,KeyError,TypeError):pass
        self.catalog_from_cache=cached is not None
        self.catalog=cached if cached is not None else self._record(catalog_command(),'PCS_EXTERNAL_CATALOG:')
        if len(self.catalog)>4096:raise RuntimeError('Mathlib catalog bound exceeded')
        self.catalog=sorted((e for e in self.catalog if NAME.fullmatch(e['name'])),key=lambda e:e['name'])
        self.catalog_sha256=digest(self.catalog); self.by_name={e['name']:e for e in self.catalog}
        if cached is None:index.write_text(json.dumps({'binding':binding,'catalog':self.catalog,'catalog_sha256':self.catalog_sha256},separators=(',',':')))
        self.source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self._entry_symbols={e['name']:symbols(e['expression']) for e in self.catalog}
        # Import initialization is measured construction, not a tactic timeout.
        self.timeout=max(40,configured_timeout)
        try:self.observe('True')
        finally:self.timeout=configured_timeout

    def _lean_path(self):return os.pathsep.join(map(str,self.paths))
    def _worker_file(self):return ROOT/'formal/PCSMathlibWorkerV4.lean'
    def close(self):LeanEnvironment.close(self)

    def _worker_cpu(self):
        if self.worker is None:return 0.
        try:
            fields=Path('/proc/'+str(self.worker.pid)+'/stat').read_text().split()
            return (int(fields[13])+int(fields[14]))/os.sysconf('SC_CLK_TCK')
        except (OSError,ValueError):return 0.

    def rank(self,state,*,mode='structural',limit=12):
        if mode not in {'structural','lexical'} or type(limit) is not int or not 1<=limit<=32:raise ValueError('retrieval settings')
        if not state['goals']:return []
        goal=state['goals'][0];target=goal['expression'];gs=symbols(target)
        ls=set().union(*(symbols(l['expression']) for l in goal['locals'])) if goal['locals'] else set()
        words=set(re.findall(r'[A-Za-z][A-Za-z0-9_]*',goal['target']));head=head_name(target)
        rows=[]
        for e in self.catalog:
            if not self.allowed(e['name']):continue
            if mode=='lexical':score=len(words&set(re.findall(r'[A-Za-z][A-Za-z0-9_]*',e['name']+' '+e['type'])))
            else:
                constants=self._entry_symbols[e['name']]
                score=3*len(gs&constants)+len(ls&constants)-len(constants-gs-ls)/4+2*(head==head_name(e['expression']))
            rows.append({'score':score,**e})
        return sorted(rows,key=lambda e:(-e['score'],e['name']))[:limit]

    def _record(self,text,prefix,*,minimal=False):
        imported=IMPORTS[:-1] if minimal else IMPORTS
        header='import PCSProofProbe\n'+''.join('import '+m+'\n' for m in imported)
        header+='universe u v w u_1 u_2 u_3 u_4 u_5\nset_option maxHeartbeats 200000\nset_option maxRecDepth 512\n'
        before=resource.getrusage(resource.RUSAGE_CHILDREN); tick=time.monotonic();self.calls+=1
        try:
            with tempfile.TemporaryDirectory(prefix='mathlib-v4-',dir=self.cache) as directory:
                file=Path(directory)/'Request.lean';file.write_text(header+self.library_source+text)
                command=[self.lean,str(file)]
                if shutil.which('prlimit'):command=['prlimit','--as=8589934592','--cpu=30','--',*command]
                result=subprocess.run(command,cwd=ROOT,env={'PATH':os.environ.get('PATH',''),'LEAN_PATH':os.pathsep.join(map(str,self.paths))},capture_output=True,text=True,timeout=self.timeout)
                output_bound=32_000_000 if prefix=='PCS_EXTERNAL_CATALOG:' else 2_000_000
                if len(result.stdout)+len(result.stderr)>output_bound:raise RuntimeError('structured output bound')
                if result.returncode:raise RuntimeError('\n'.join(l for l in (result.stdout+result.stderr).splitlines() if not l.startswith(('PCS_STATE:','PCS_KERNEL:')))[-1800:])
                records=[json.loads(l[len(prefix):]) for l in result.stdout.splitlines() if l.startswith(prefix)]
                if len(records)!=1:raise RuntimeError('missing unique structured record')
                return records[0]
        except subprocess.TimeoutExpired:raise RuntimeError('Mathlib resource exhaustion') from None
        finally:
            after=resource.getrusage(resource.RUSAGE_CHILDREN)
            self.cpu_seconds+=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime
            self.max_child_rss_kib=max(self.max_child_rss_kib,after.ru_maxrss)
            self.seconds+=time.monotonic()-tick

    def allowed(self,name):
        return name in self.by_name and name not in self.excluded_names and self.by_name[name]['module'] not in self.excluded_modules

    def render(self,action):
        if type(action) is not dict or set(action)!={'kind','argument'}:raise ValueError('typed action shape')
        kind,arg=action['kind'],action['argument']
        if kind in BASE and arg is None:return BASE[kind]
        if kind=='intro' and type(arg) is str and re.fullmatch(r'h[0-9]{1,2}',arg):return 'intro '+arg
        if kind in {'apply_lemma','exact_lemma','simp_lemma'} and type(arg) is str and self.allowed(arg):
            return ('simp only ['+arg+']') if kind=='simp_lemma' else ('apply ' if kind=='apply_lemma' else 'exact ')+arg
        if kind in {'exact_local','apply_local'} and type(arg) is str and LOCAL.fullmatch(arg) and arg.split('.')[0] not in {'sorry','admit','axiom','unsafe','native_decide'}:return ('exact ' if kind=='exact_local' else 'apply ')+arg
        if kind in {'rewrite_lemma','rewrite_local'} and type(arg) is dict and set(arg)=={'name','direction','occurrence'}:
            n,d,o=arg['name'],arg['direction'],arg['occurrence']
            if type(n) is str and ((kind=='rewrite_lemma' and self.allowed(n)) or (kind=='rewrite_local' and LOCAL.fullmatch(n) and n.split('.')[0] not in {'sorry','admit','axiom','unsafe','native_decide'})) and d in {'forward','backward'} and type(o) is int and 1<=o<=4:
                return f'conv => lhs; rw (occs := .pos [{o}]) [{"← " if d=="backward" else ""}{n}]'
        if kind in {'induction_nat','induction_list'} and type(arg) is str and re.fullmatch(r'h[0-9]{1,2}',arg):return 'induction '+arg
        raise ValueError('action outside receiver grammar/catalog')

    def observe(self,statement,actions=()):
        self._statement(statement)
        if len(actions)>24:raise ValueError('proof depth bound')
        commands=[self.render(a) for a in actions]
        key=digest({'statement':statement,'actions':actions,'catalog':self.catalog_sha256,'library':self.library_sha256,'imports':self.import_digests,'excluded_names':sorted(self.excluded_names),'excluded_modules':sorted(self.excluded_modules)})
        if key in self._states:self.cache_hits+=1;return deepcopy(self._states[key])
        text=f'#pcs_probe ({statement}) => [{", ".join("("+c+")" for c in commands)}]\n'
        cpu=self._worker_cpu()
        result=LeanEnvironment._worker_source(self,'universe u v w u_1 u_2 u_3 u_4 u_5\n'+self.library_source+text)
        self.worker_requests+=1
        delta=max(0.,self._worker_cpu()-cpu);self.worker_cpu_seconds+=delta;self.cpu_seconds+=delta
        if len(self._states)<4096:self._states[key]=deepcopy(result)
        return result

    def start(self,statement):return self.observe(statement)['states'][0]

    def step(self,statement,actions,action):
        # Syntax is checked before any compiler invocation. No proposer reward.
        self.render(action)
        result=self.observe(statement,[*actions,action]);valid=result['status']!='invalid'
        if not valid:self.invalid+=1
        return {'valid':valid,'state':result['states'][-1],'error':result['error'],'closed':result['status']=='closed'}

    def options(self,state,limit=6,mode='structural'):
        if type(limit) is not int or not 1<=limit<=16:raise ValueError('premise limit')
        if not state['goals']:return []
        g=state['goals'][0];head=head_name(g['expression']);locals_=g['locals'];used={l['name'] for l in locals_}
        action=lambda k,a=None:{'kind':k,'argument':a}
        options=[action('assumption')]
        if g['expression']['kind']=='forall':
            fresh=next((f'h{i}' for i in range(100) if f'h{i}' not in used),None)
            if fresh:options.insert(0,action('intro',fresh))
        if head in {'And','Iff'}:options.append(action('constructor'))
        if head in {'Eq','Iff'}:options.append(action('rfl'))
        if head=='Eq' and self.allowed('Eq.trans'):options.append(action('apply_lemma','Eq.trans'))
        if head=='Or':options.extend([action('left'),action('right')])
        # Independently admitted local abstractions are a bounded memory tier,
        # not lost behind broad lexical/catalog top-k ties.
        options.extend(action('apply_lemma',e['name']) for e in self.library if self.allowed(e['name']))
        for local in locals_:
            n=local['name']
            if not LOCAL.fullmatch(n):continue
            for suffix in ['','.1','.2','.1.1','.1.2','.2.1','.2.2']:
                if reference_expression(state,n+suffix) is not None:options.extend([action('exact_local',n+suffix),action('apply_local',n+suffix)])
            if head_name(local['expression'])=='Eq':options.append(action('rewrite_local',{'name':n,'direction':'forward','occurrence':1}))
            if re.fullmatch(r'h[0-9]{1,2}',n) and local['type'] in {'Nat','List Nat'}:options.append(action('induction_nat' if local['type']=='Nat' else 'induction_list',n))
        # No theorem values/proof bodies are given to the ranker.
        ranked=self.rank(state,mode=mode,limit=32)
        for entry in [e for e in ranked if self.allowed(e['name'])][:limit]:
            n=entry['name'];options.extend([action('apply_lemma',n),action('exact_lemma',n)])
            if head_name(entry['expression']) in {'Eq','Iff'}:
                options.append(action('simp_lemma',n))
                if head=='Eq':options.extend(action('rewrite_lemma',{'name':n,'direction':d,'occurrence':o}) for d in ['forward','backward'] for o in [1,2])
        for a in options:self.render(a)
        return options

    def verify(self,statement,actions):
        self._statement(statement); commands=[self.render(a) for a in actions]
        if not 1<=len(actions)<=24:raise ValueError('bounded nonempty proof')
        proof='\n'.join('  '+c for c in commands)
        # Primitive actions need no broad tactic module. Fewer imports reduce
        # cold replay cost; imported-premise failures retry the exact same proof
        # in the full approved environment. Both are ordinary kernel processes.
        minimal=True
        try:
            first=self._record(f'theorem pcs_mathlib_final : {statement} := by\n{proof}\n#pcs_audit pcs_mathlib_final\n','PCS_KERNEL:',minimal=True)
            second=self._record(f'theorem pcs_mathlib_independent : {statement} := by\n{proof}\n#pcs_audit pcs_mathlib_independent\n','PCS_KERNEL:',minimal=True)
        except RuntimeError:
            minimal=False
            first=self._record(f'theorem pcs_mathlib_final : {statement} := by\n{proof}\n#pcs_audit pcs_mathlib_final\n','PCS_KERNEL:')
            second=self._record(f'theorem pcs_mathlib_independent : {statement} := by\n{proof}\n#pcs_audit pcs_mathlib_independent\n','PCS_KERNEL:')
        if not set(first['axioms'])<=ALLOWED_AXIOMS:raise RuntimeError('unapproved theorem axioms')
        if not same_kernel_type(first,second):raise RuntimeError('independent theorem mismatch')
        return {'format':'pcs-mathlib-multistep-proof-v4','statement':statement,'goal_sha256':digest(statement),'actions':actions,'proof':proof,'kernel':first,'independent_kernel':second,'lean':self.version,'mathlib_revision':MATHLIB_REVISION,'imports':list(IMPORTS),'kernel_imports':list(IMPORTS[:-1] if minimal else IMPORTS),'import_artifact_sha256':self.import_digests,'catalog_sha256':self.catalog_sha256,'source_sha256':self.source_sha256,'library_sha256':self.library_sha256,'library':deepcopy(self.library),'excluded_names':sorted(self.excluded_names),'excluded_modules':sorted(self.excluded_modules),'pcs_authority':False}

    def admit(self,name,statement,actions,*,source,license):
        """Only a twice-checked proof enters the bounded immutable local library."""
        if len(self.library)>=6 or not re.fullmatch(r'PCSAbstractL[0-5]',name) or name in self.by_name or not source or license not in {'CC0-1.0','Apache-2.0'}:raise ValueError('bounded source-cleared lemma admission')
        receipt=self.verify(statement,actions)
        proof=receipt['proof'];declaration=f'theorem {name} : {statement} := by\n{proof}\n'
        # Extract the ACTUAL resulting signature, not a proposer supplied Expr.
        command=declaration+f'''open Lean Elab Command Meta
syntax "#pcs_admitted_signature" : command
elab_rules : command
 | `(#pcs_admitted_signature) => do
  liftTermElabM do
   let info ← getConstInfo `{name}
   IO.println s!"PCS_ADMITTED_SIGNATURE:{{(Json.mkObj [("name", toJson "{name}"), ("type", toJson (toString (← ppExpr info.type))), ("expression", PCSProofProbe.expression info.type), ("module", toJson "PCSVerifiedLibrary"), ("universes", toJson (info.levelParams.map toString))]).compress}}"
#pcs_admitted_signature
'''
        signature=self._record(command,'PCS_ADMITTED_SIGNATURE:')
        entry={'name':name,'statement':statement,'actions':deepcopy(actions),'receipt':receipt,'source':source,'license':license,'signature':signature}
        self.library.append(entry);self.library_source+=declaration;self.library_sha256=digest(self.library)
        self.catalog.append(signature);self.catalog.sort(key=lambda e:e['name']);self.by_name[name]=signature
        self._entry_symbols[name]=symbols(signature['expression']);self.catalog_sha256=digest(self.catalog)
        self._states.clear()
        return deepcopy(entry)

    def solve(self,statement,*,ranker=None,budget=48,depth=12,beam=4,premises=6,wall=60,mode='structural'):
        if any(type(x) is not int or x<1 for x in [budget,depth,beam]) or budget>128 or depth>24 or beam>8 or not 0<wall<=300:raise ValueError('bounded search settings')
        tick=time.monotonic();before=self.calls;requests=self.worker_requests;hits=self.cache_hits;cpu=self.cpu_seconds;initial=self.start(statement)
        queue=[(0,0,[],initial)];serial=0;expansions=0;transitions=[];seen=set();receipt=None
        while queue and expansions<budget and time.monotonic()-tick<wall:
            _,_,actions,state=heapq.heappop(queue)
            key=digest(state)
            if key in seen or len(actions)>=depth:continue
            seen.add(key);options=self.options(state,premises,mode)
            forced_intro=next((i for i,a in enumerate(options) if a['kind']=='intro'),None) if state['goals'][0]['expression']['kind']=='forall' else None
            if forced_intro is not None:
                # Universal/implication introduction is invertible. Asking for
                # beam alternative successes here only wastes verifier budget.
                scores=[0.]*len(options);scores[forced_intro]=1.
            elif ranker is None:
                priorities={'intro':20,'assumption':18,'rfl':17,'constructor':16,'exact_local':14,'apply_local':12,'apply_lemma':10,'exact_lemma':9,'simp_lemma':8,'rewrite_lemma':7,'rewrite_local':7,'induction_nat':4,'induction_list':4}
                scores=[priorities.get(a['kind'],0)-i*.01 for i,a in enumerate(options)]
            else:scores=ranker.rank(state,options)
            if len(scores)!=len(options) or any(type(s) not in {int,float} or not math.isfinite(s) for s in scores):raise ValueError('ranker supplied invalid scores')
            order=[forced_intro] if forced_intro is not None else sorted(range(len(options)),key=lambda i:(-scores[i],i));successors=[]
            # Budget includes invalid tactics, not only successful edges.
            for chosen in order:
                if expansions>=budget or time.monotonic()-tick>=wall:break
                expansions+=1;action=options[chosen]
                try:next_=self.step(statement,actions,action)
                except RuntimeError as error:next_={'valid':False,'state':state,'error':str(error),'closed':False}
                transitions.append({'state':state,'options':options,'chosen':chosen,'action':action,'next_state':next_['state'],'valid':next_['valid'],'error':next_['error'],'closed':next_['closed'],'prefix':actions,'goal_sha256':digest(statement)})
                if not next_['valid']:continue
                path=[*actions,action]
                if next_['closed']:
                    receipt=self.verify(statement,path);queue=[];break
                if digest(next_['state'])!=key:successors.append((len(path)-float(scores[chosen])*.001,path,next_['state']))
                if len(successors)>=beam:break
            if receipt:break
            for priority,path,nextstate in successors:
                serial+=1;heapq.heappush(queue,(priority,serial,path,nextstate))
        return {'status':'verified' if receipt else 'unknown','receipt':receipt,'transitions':transitions,'expansions':expansions,'compiler_invocations':self.calls-before,'structured_worker_requests':self.worker_requests-requests,'cache_hits':self.cache_hits-hits,'physical_lean_calls':self.calls-before+self.worker_requests-requests,'cpu_seconds':self.cpu_seconds-cpu,'wall_seconds':time.monotonic()-tick,'max_child_rss_kib':self.max_child_rss_kib,'budget':{'actions':budget,'depth':depth,'beam':beam,'seconds':wall},'pcs_authority':False}

    def portfolio(self,statement):
        self._statement(statement);before=self.calls;tick=time.monotonic();attempts=[];receipt=None
        for tactic in PORTFOLIO:
            proof='  repeat intro\n  '+tactic
            try:
                first=self._record(f'theorem pcs_tactic_baseline : {statement} := by\n{proof}\n#pcs_audit pcs_tactic_baseline\n','PCS_KERNEL:')
                if not set(first['axioms'])<=ALLOWED_AXIOMS:raise RuntimeError('unapproved axioms')
                second=self._record(f'theorem pcs_tactic_replay : {statement} := by\n{proof}\n#pcs_audit pcs_tactic_replay\n','PCS_KERNEL:')
                if not same_kernel_type(first,second):raise RuntimeError('baseline replay mismatch')
                receipt={'statement':statement,'proof':proof,'kernel':first,'independent_kernel':second,'winning_tactic':tactic};attempts.append({'tactic':tactic,'status':'verified'});break
            except RuntimeError as error:attempts.append({'tactic':tactic,'status':'unknown','error':str(error)})
        return {'status':'verified' if receipt else 'unknown','receipt':receipt,'attempts':attempts,'physical_lean_calls':self.calls-before,'wall_seconds':time.monotonic()-tick,'whole_goal_tactics_not_primitive_actions':True,'pcs_authority':False}
