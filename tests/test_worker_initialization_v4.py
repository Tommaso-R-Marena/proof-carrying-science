"""Initialization deadlines and fail-closed separation from user proof actions."""
import json
import queue
import pytest
from pcs.experimental.prover.environment import LeanEnvironment
from pcs.experimental.prover.mathlib_environment_v4 import MathlibEnvironmentV4

TRUE_STATE={'format':'pcs-lean-state-v1','status':'open','states':[{'goals':[{'expression':{'kind':'constant','value':'True:[]','children':[]},'locals':[]}]}],'error':''}

class Stream:
    def __init__(self):self.lines=queue.Queue()
    def __iter__(self):
        while True:
            line=self.lines.get()
            if line is None:return
            yield line

class Process:
    def __init__(self,env,ready):
        self.env,self.ready=env,ready;self.stdout=Stream();self.stdin=self;self.requests=[];self.timeouts=[];self.terminated=False
    def write(self,line):
        self.requests.append(json.loads(line));self.timeouts.append(self.env.timeout)
        result=self.ready if len(self.requests)==1 else {'format':'pcs-lean-state-v1','status':'invalid','states':[],'error':'unproved user goal'}
        self.stdout.lines.put('PCS_STATE:'+json.dumps(result)+'\n')
        self.stdout.lines.put('PCS_END:{"errors":[]}\n')
    def flush(self):pass
    def terminate(self):self.terminated=True;self.stdout.lines.put(None)
    def wait(self,timeout=None):return 0

def receiver(monkeypatch,tmp_path,ready,cls=LeanEnvironment):
    env=cls.__new__(cls);env.paths=[tmp_path];env.worker=None;env.lean='lean';env.cache=tmp_path;env.timeout=2;env.invocations=0;env.seconds=0
    process=Process(env,ready)
    monkeypatch.setattr('pcs.experimental.prover.environment.subprocess.Popen',lambda *args,**kwargs:process)
    return env,process

@pytest.mark.parametrize("cls",[LeanEnvironment,MathlibEnvironmentV4])
def test_receiver_probe_is_separate_and_cannot_certify_user_goal(monkeypatch,tmp_path,cls):
    env,process=receiver(monkeypatch,tmp_path,TRUE_STATE,cls)
    try:
        result=LeanEnvironment._worker_source(env,'#pcs_probe (False) => []\n')
        assert process.requests==['#pcs_probe (True) => []\n','#pcs_probe (False) => []\n']
        assert process.timeouts==[60,2] and env.timeout==2
        assert env.worker_initialization_requests==1 and env.worker_wire_requests==2
        assert result['status']=='invalid' and result['error']=='unproved user goal'
        LeanEnvironment._worker_source(env,'#pcs_probe (False) => []\n')
        assert env.worker_initialization_requests==1 and env.worker_wire_requests==3
    finally:env.close()

@pytest.mark.parametrize('ready',[
    {**TRUE_STATE,'status':'closed'},
    {**TRUE_STATE,'format':'forged'},
    {**TRUE_STATE,'states':[]},
    {**TRUE_STATE,'states':[{'goals':[]}]},
    {**TRUE_STATE,'states':[{'goals':[{'expression':{'kind':'constant','value':'False:[]','children':[]},'locals':[]}]}]},
    {**TRUE_STATE,'states':[{'goals':[{'expression':{'kind':'constant','value':'True:[]','children':[]},'locals':[{'name':'hidden_assumption'}]}]}]},
])
def test_forged_initialization_rejects_before_user_input(monkeypatch,tmp_path,ready):
    env,process=receiver(monkeypatch,tmp_path,ready)
    with pytest.raises(RuntimeError,match='initialization failed'):env._worker_source('#pcs_probe (False) => []\n')
    assert env.timeout==2 and env.worker is None and process.terminated
    assert process.requests==['#pcs_probe (True) => []\n']
    assert env.worker_wire_requests==1
