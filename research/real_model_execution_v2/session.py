"""Owned inference process with checked framing, correlation and shutdown."""
from contextlib import AbstractContextManager
import subprocess
import sys

from research.real_model_safety_v1.audit import same
from .channel import Channel
from .protocol import environment,request,check_ready,check_output,closed,sources


class Session(AbstractContextManager):
    def __init__(self,snapshot,dependencies,log,oracle):
        self.process=subprocess.Popen([sys.executable,"-m","research.real_model_execution_v2.worker",str(snapshot)],
                                      stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,bufsize=0,
                                      env=environment(dependencies))
        self.oracle,self.sequence,self.closed=oracle,0,False
        try:
            self.reader=Channel(self.process.stdout.fileno())
            self.writer=Channel(self.process.stdin.fileno(),limit=16384)
            self.ready=self.reader.read();self.session=check_ready(self.ready)
            self.sources=self.ready["sources"]
        except BaseException:
            self.__exit__(None,None,None);raise

    def generate(self,messages):
        if self.closed or sources()!=self.sources:raise ValueError("closed/changed inference session")
        req=request(self.session,self.sequence,messages)
        self.writer.write(req);value=self.reader.read()
        raw=check_output(value,req,self.oracle)
        self.sequence+=1
        return req,value,raw

    def close(self):
        if self.closed:raise ValueError("inference session already closed")
        if sources()!=self.sources:raise ValueError("inference sources changed")
        req=request(self.session,self.sequence)
        self.writer.write(req);value=self.reader.read()
        same(value,closed(req));same(value["sources"],self.sources)
        self.process.stdin.close();self.reader.eof();self.process.wait(timeout=30)
        if self.process.returncode:raise ValueError("inference worker failed")
        self.closed=True
        return value

    def __exit__(self,*args):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        for stream in (self.process.stdin,self.process.stdout):
            if stream and not stream.closed:stream.close()
