"""Fixed worker launch, correlated responses and fail-closed shutdown."""
import subprocess,sys
from research.real_model_execution_v2.session import Session as BaseSession
from research.real_model_execution_v2.channel import Channel
from research.real_model_safety_v1.audit import same
from .protocol import environment,request,check_ready,check_output,closed,sources


class Session(BaseSession):
    def __init__(self,snapshot,dependencies,log,oracle):
        self.mode=oracle.mode
        self.process=subprocess.Popen([sys.executable,"-m","research.structured_action_lab_v4.worker",str(snapshot),self.mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,bufsize=0,env=environment(dependencies))
        self.oracle,self.sequence,self.closed=oracle,0,False
        try:
            self.reader=Channel(self.process.stdout.fileno());self.writer=Channel(self.process.stdin.fileno(),limit=16384)
            self.ready=self.reader.read();self.session=check_ready(self.ready,self.mode);self.sources=self.ready["sources"]
        except BaseException:self.__exit__(None,None,None);raise

    def generate(self,messages):
        if self.closed or sources()!=self.sources:raise ValueError("Closed/changed inference session")
        req=request(self.session,self.sequence,messages);self.writer.write(req);value=self.reader.read()
        raw=check_output(value,req,self.oracle);self.sequence+=1;return req,value,raw

    def close(self):
        if self.closed or sources()!=self.sources:raise ValueError("Closed/changed inference session")
        req=request(self.session,self.sequence);self.writer.write(req);value=self.reader.read();same(value,closed(req,self.mode))
        self.process.stdin.close();self.reader.eof();self.process.wait(timeout=30)
        if self.process.returncode:raise ValueError("Inference worker failed")
        self.closed=True;return value
