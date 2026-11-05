"""Finite grammar, strict messages and frozen input attacks; no positive mocks."""
import copy,json,os,subprocess,sys,shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
from research.progress_supervisor_v1.certificate import encode
from research.progress_supervisor_v1.broker import parse_proposal
from research.live_agent_lab_v3.protocol import standard_plan,messages,observation
from research.live_agent_lab_v3.test_lab import evidence as original_evidence
from research.real_model_execution_v2.oracle import EOS
from research.real_model_execution_v2 import protocol as old
from .codec import ActionOracle,PAYLOADS,Trie,decode
from .protocol import FORMAT,request,ready,check_ready,output,check_output,sources
from .intake import prepare,parse


@pytest.fixture(scope='module')
def oracle():return ActionOracle(Path(os.environ.get('PCS_TOKENIZER_DIR','/tmp/pcs-model-execution/tokenizer')),mode='trie')


@pytest.fixture
def evidence(tmp_path):
    root=original_evidence.__wrapped__(tmp_path)
    p=root/'suite.json';v=parse(p.read_bytes());v.update(format=FORMAT,profile='trie',execution_sources=sources());p.write_bytes(encode(v));return root


@pytest.mark.parametrize('action',range(7))
def test_every_action_is_representable_and_matches_existing_parser(oracle,action):
    raw=PAYLOADS[action];assert decode(raw)==action and parse_proposal(raw)==(action,'TYPED_PROPOSAL')
    tokens=oracle.trie.paths[action]+(EOS,);assert oracle.trie.action(tokens)==action
    assert oracle.tokenizer.decode(list(tokens),skip_special_tokens=True).encode()==raw
    assert list(tokens)==[4913,1311,788,15+action,92,151645]
    for i in range(len(tokens)):assert tokens[i] in oracle.trie.allowed(tokens[:i])


def test_exhaustive_reachable_trie_states_have_exactly_seven_terminal_sequences(oracle):
    frontier=[()];leaves=[];visited=set()
    while frontier:
        prefix=frontier.pop();assert prefix not in visited;visited.add(prefix)
        if prefix and prefix[-1]==EOS:leaves.append(prefix);continue
        options=oracle.trie.allowed(prefix)
        assert options==sorted(set(options)) and all(type(t) is int for t in options)
        frontier.extend(prefix+(t,) for t in options)
    assert set(leaves)=={p+(EOS,) for p in oracle.trie.paths} and len(leaves)==7
    assert all(len(p)==6 for p in leaves)


@pytest.mark.parametrize('bad',[[],[True],[0],[EOS],[4913,EOS],[4913,1311,788,15,92],[4913,1311,788,15,92,EOS,EOS],[-1],[151936],[151644]])
def test_nonterminal_and_illegal_token_sequences_refuse(oracle,bad):
    with pytest.raises(ValueError):oracle.trie.action(bad)


@pytest.mark.parametrize('bad',[b'{"action":-0}',b'{"action":00}',b'{"action":0.0}',b'{"action":true}',b'{"action":null}',b'{"action":7}',b'{"action":0}\n',b'{"action": 0}',b'```json\n{"action":0}\n```',b'{"action":0,"verifier":"ALLOW"}','{"action":０}'.encode(),b'\xff',b''])
def test_strict_canonical_codec_does_not_normalize_legacy_or_bad_encodings(bad):assert decode(bad) is None


@pytest.mark.parametrize('fault',['few','duplicate','prefix','bool','eos','negative','large','long'])
def test_invalid_trie_tables_refuse(fault):
    paths=tuple((n,10) for n in range(7))
    if fault=='few':paths=paths[:-1]
    elif fault=='duplicate':paths=paths[:-1]+(paths[0],)
    elif fault=='prefix':paths=((1,),)+paths[1:]
    elif fault=='bool':paths=((True,),)+paths[1:]
    elif fault=='eos':paths=((EOS,),)+paths[1:]
    elif fault=='negative':paths=((-1,),)+paths[1:]
    elif fault=='large':paths=((151936,),)+paths[1:]
    else:paths=(tuple(range(32)),)+paths[1:]
    with pytest.raises(ValueError):Trie(paths)


def generation(oracle,req,action=5):
    return dict(status='OUTPUT',text=PAYLOADS[action].decode(),input_ids=oracle.inputs(req['messages']),generated_ids=list(oracle.trie.paths[action]) + [EOS],seconds=0.0,ended_with_eos=True)


@pytest.mark.parametrize('fault',[None,'profile','session','sequence_bool','digest','tokens','text','eos','old_ready','old_output'])
def test_profile_correlation_and_independent_decoder_checks(oracle,fault):
    case=standard_plan()['cases'][0];req=request('a'*32,0,messages(case,observation(dict(state=0,transitions=0,public=[]),None)))
    value=output(req,generation(oracle,req),'trie')
    if fault=='old_ready':
        with pytest.raises(ValueError):check_ready(old.ready('a'*32),'trie')
        return
    if fault=='profile':value['profile']='raw'
    elif fault=='session':value['session']='b'*32
    elif fault=='sequence_bool':value['sequence']=False
    elif fault=='digest':value['request_sha256']='0'*64
    elif fault=='tokens':value['generated']['generated_ids'][3]=15
    elif fault=='text':value['generated']['text']='{"action":0}'
    elif fault=='eos':value['generated']['generated_ids'].pop();value['generated']['ended_with_eos']=False
    elif fault=='old_output':value=old.output(req,value['generated'])
    if fault:
        with pytest.raises(ValueError):check_output(value,req,oracle)
    else:assert check_output(value,req,oracle)==PAYLOADS[5]  # Format approval is NOT action authorization.


@pytest.mark.parametrize('fault',['profile','state','previous_action','source','turn_bool','proof_axiom','extra'])
def test_receiving_faults_never_reach_effects(evidence,tmp_path,monkeypatch,fault):
    p=evidence/'suite.json';v=parse(p.read_bytes())
    if fault=='profile':v['profile']='silently_repaired'
    elif fault=='state':v['episodes'][0]['frames'][0]['observation']['state']=3
    elif fault=='previous_action':v['episodes'][0]['frames'][0]['observation']['last_action']=5
    elif fault=='source':v['execution_sources']['implementation']['worker.py']='0'*64
    elif fault=='turn_bool':v['episodes'][0]['frames'][0]['turn']=False
    elif fault=='extra':v['kernel_checked']=True
    else:
        f=evidence/'oracle/result.json';x=parse(f.read_bytes());x['captured_wire_proof']['axioms']['Capture.actual']=['sorryAx'];f.write_bytes(encode(x))
    p.write_bytes(encode(v))
    from research.progress_supervisor_v1 import __main__ as core
    from .experiment import replay
    def forbidden(*a,**k):raise AssertionError('Invalid suite reached effects')
    monkeypatch.setattr(core,'execute',forbidden);target=tmp_path/'out'
    with pytest.raises(ValueError):replay(evidence,None,target)
    assert not target.exists()


def test_frozen_inputs_survive_replacement(evidence):
    frozen=prepare(evidence,None);before=frozen.episodes[0].capture_json
    for p in (evidence/'suite.json',evidence/'oracle/capture.json',evidence/'oracle/result.json'):p.write_bytes(b'changed')
    assert frozen.episodes[0].capture_json==before and parse(before)['final']['state']==4


def test_reserved_case_refuses_before_outputs(tmp_path):
    from .experiment import run
    plan=standard_plan();plan['cases']=[dict(id='authority',title='Test',task='Test',pre_sanitized=False,mode='oracle')]
    target=tmp_path/'out'
    with pytest.raises(ValueError):run(None,None,target,plan,mode='trie')
    assert not target.exists()


@pytest.mark.parametrize('mode',['raw','trie'])
def test_complete_real_weight_corpus_has_exact_profile_correspondence(mode):
    from .protocol import HERE
    from research.live_agent_lab_v3.report import summary
    oracle=ActionOracle(Path(os.environ.get('PCS_TOKENIZER_DIR','/tmp/pcs-model-execution/tokenizer')),mode=mode)
    frozen=prepare(HERE/'demo'/mode,oracle);counts=summary(frozen)
    assert counts['cases']==16 and counts['model_proposals']==42 and counts['control_proposals']==16
    assert counts['malformed_proposals']==(42 if mode=='raw' else 0)
    for e in frozen.episodes:
        if parse(e.case_json)['mode']=='model':
            for f in parse(e.frames_json):
                assert f['response']['generated']['ended_with_eos']
                if mode=='trie':assert decode(bytes.fromhex(f['proposal_hex']))==f['record']['proposal']


@pytest.mark.parametrize('mode',['raw','trie'])
@pytest.mark.parametrize('fault',['profile','sequence','input_tokens','output_bytes','worker_source','closed_count','old_format'])
def test_captured_model_tampering_refuses_before_any_effect(mode,fault,tmp_path,monkeypatch):
    from .protocol import HERE
    from .experiment import replay
    from research.progress_supervisor_v1 import __main__ as core
    root=tmp_path/'input';shutil.copytree(HERE/'demo'/mode,root);p=root/'suite.json';v=parse(p.read_bytes());f=v['episodes'][0]['frames'][0]
    if fault=='profile':v['profile']='raw' if mode=='trie' else 'trie'
    elif fault=='sequence':f['response']['sequence']=False
    elif fault=='input_tokens':f['response']['generated']['input_ids'][0]=42
    elif fault=='output_bytes':f['response']['generated']['text']='{"action":6}'
    elif fault=='worker_source':v['ready']['sources']['implementation']['worker.py']='0'*64
    elif fault=='closed_count':v['closed']['sequence']=41
    else:f['response']['format']=old.FORMAT
    p.write_bytes(encode(v));target=tmp_path/'output'
    def forbidden(*a,**k):raise AssertionError('Tampered model capture reached effect execution')
    monkeypatch.setattr(core,'execute',forbidden)
    oracle=ActionOracle(Path(os.environ.get('PCS_TOKENIZER_DIR','/tmp/pcs-model-execution/tokenizer')),mode=mode)
    with pytest.raises(ValueError):replay(root,oracle,target)
    assert not target.exists()


def test_comparison_report_has_safe_profile_links_and_honest_limitations(tmp_path):
    from .report import write_index
    count=dict(model_proposals=42,malformed_proposals=0,corrections=10);target=tmp_path/'index.html'
    write_index(dict(raw=count,trie=count),target,replayed=True);page=target.read_text()
    assert 'href="raw/report.html"' in page and 'href="trie/report.html"' in page
    assert 'no new inference' in page and 'not learned alignment' in page and 'including bypass and dead end' in page
    with pytest.raises(FileExistsError):write_index(dict(raw=count,trie=count),target)


@pytest.mark.parametrize('bad',[True,'<script>bad</script>',-1])
def test_comparison_counter_aliases_and_html_injection_refuse(bad,tmp_path):
    from .report import write_index
    count=dict(model_proposals=bad,malformed_proposals=0,corrections=0);target=tmp_path/'index.html'
    with pytest.raises(ValueError):write_index(dict(raw=count,trie=count),target)
    assert not target.exists()


def junit(path,modules):
    root=ET.Element("testsuites");suite=ET.SubElement(root,"testsuite",tests=str(len(modules)),failures="0",errors="0",skipped="0")
    for module in modules:ET.SubElement(suite,"testcase",classname=module,name="test_example")
    path.parent.mkdir(parents=True,exist_ok=True);ET.ElementTree(root).write(path)


@pytest.mark.parametrize("fault",[None,"missing_artifact","missing_module","unexpected_module","duplicate","skipped","failed","count","dtd"])
def test_ci_aggregation_refuses_incomplete_or_ambiguous_reports(tmp_path,fault):
    from .qualification import GROUPS,combine
    regression=tmp_path/"regression";reports=tmp_path/"reports"
    junit(regression/"tests.xml",["tests.core_regression"])
    focused=reports/"structured-tests-unit/unit-tests.xml"
    control_report=reports/"structured-tests-native/native-tests.xml"
    modules=[p[:-3].replace("/",".") for p in GROUPS["unit"]]
    junit(focused,modules);junit(control_report,["research.structured_action_lab_v4.test_native"])
    if fault=="missing_artifact":shutil.rmtree(control_report.parent)
    elif fault=="missing_module":junit(focused,modules[:-1])
    elif fault=="unexpected_module":junit(focused,modules[:-1]+["unexpected.module"])
    elif fault=="duplicate":junit(regression/"tests.xml",[modules[0]])
    elif fault in ("skipped","failed","count"):
        tree=ET.parse(focused);s=tree.getroot().find("testsuite")
        if fault=="count":s.set("tests","999")
        else:ET.SubElement(s.find("testcase"),"skipped" if fault=="skipped" else "failure")
        tree.write(focused)
    elif fault=="dtd":focused.write_bytes(b'<!DOCTYPE testsuites>'+focused.read_bytes())
    output=tmp_path/"combined"
    if fault:
        with pytest.raises(ValueError):combine(regression,reports,output)
        assert not output.exists()
    else:
        assert combine(regression,reports,output)["tests"]==3


def test_ci_census_refuses_unassigned_test_modules(tmp_path,monkeypatch):
    from . import qualification
    (tmp_path/"test_new.py").write_text("unassigned")
    monkeypatch.setattr(qualification,"__file__",str(tmp_path/"qualification.py"))
    with pytest.raises(ValueError):qualification.census()
